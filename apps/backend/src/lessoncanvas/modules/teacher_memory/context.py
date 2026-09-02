"""F013 subordinate application of confirmed memory (ADR-0005; Spec D2/D5/D8).

Memory context is untrusted data: it travels only as a labeled list inside
JSON user payloads (the corpus_excerpt pattern), is bounded by the injection
budget, and never enters system prompts or gains instruction framing.
"""

import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from lessoncanvas.models import MemoryProjectOverride, MemoryRecord, TraceEvent
from lessoncanvas.settings import get_settings

CATEGORIES = ("language_mode", "exercise_format", "pacing_structure", "assessment_style")

# U6 injection priority: language first (field-mapped), then the free-text
# preference categories; most-recently-confirmed first within a category.
CATEGORY_PRIORITY = {
    "language_mode": 0,
    "exercise_format": 1,
    "pacing_structure": 2,
    "assessment_style": 3,
}

LANGUAGE_VALUES = ("chinese", "english", "bilingual")

_LANGUAGE_PATTERNS = (
    ("bilingual", re.compile(r"双语|两种语言|bilingual", re.IGNORECASE)),
    ("english", re.compile(r"英语|全英|english", re.IGNORECASE)),
    ("chinese", re.compile(r"中文|汉语|chinese|zh", re.IGNORECASE)),
)


def canonical_language(raw: str | None) -> str | None:
    """Deterministically map a free-text language intent onto the canonical
    enum used for conflict detection (Spec D5); None means unmappable, in
    which case no conflict can be claimed and the record simply applies as
    subordinate context."""

    if not raw:
        return None
    text = str(raw).strip()
    for value, pattern in _LANGUAGE_PATTERNS:
        if pattern.search(text):
            return value
    return None


def normalize_content(content: str) -> str:
    return re.sub(r"\s+", " ", str(content)).strip().casefold()


def content_hash(content: str) -> str:
    import hashlib

    return hashlib.sha256(normalize_content(content).encode("utf-8")).hexdigest()


def _records_in_priority_order(session: Session, workspace_id: uuid.UUID) -> list[MemoryRecord]:
    records = session.scalars(
        select(MemoryRecord).where(MemoryRecord.workspace_id == workspace_id)
    ).all()
    return sorted(
        records,
        key=lambda record: (
            CATEGORY_PRIORITY.get(record.category, 99),
            -(record.created_at.timestamp() if record.created_at else 0),
        ),
    )


def effective_memory(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    brief_language_raw: str | None = None,
) -> dict:
    """Assemble the effective subordinate context for one run/pass start.

    Deterministic and whole-record: U6 priority order, per-project overrides
    excluded, language_mode conflicts skipped with the confirmed version
    winning, budget overflow disclosed as skipped records — never silent
    truncation of a record's text."""

    settings = get_settings()
    overrides = {
        row.record_id: row.enabled
        for row in session.scalars(
            select(MemoryProjectOverride).where(
                MemoryProjectOverride.project_id == project_id
            )
        )
    }
    brief_language = canonical_language(brief_language_raw)

    applied: list[dict] = []
    conflicts: list[dict] = []
    budget_skipped: list[dict] = []
    project_disabled: list[dict] = []
    used = 0
    for record in _records_in_priority_order(session, workspace_id):
        entry = {"id": str(record.id), "category": record.category, "content": record.content}
        if overrides.get(record.id) is False:
            project_disabled.append(entry)
            continue
        if (
            record.category == "language_mode"
            and brief_language is not None
            and record.value
            and record.value != brief_language
        ):
            conflicts.append({**entry, "value": record.value, "brief_value": brief_language})
            continue
        if used + len(record.content) > settings.memory_injection_budget_chars:
            budget_skipped.append({"id": str(record.id), "category": record.category})
            continue
        applied.append(entry)
        used += len(record.content)
    return {
        "applied": applied,
        "conflicts": conflicts,
        "budget_skipped": budget_skipped,
        "project_disabled": project_disabled,
        "injected_chars": used,
    }


def attach_generation_run_memory(session, run) -> list[dict]:
    """Snapshot-once memory attach for a generation-family run: the bound
    brief's language field drives the deterministic conflict check (Spec D5)."""

    from lessoncanvas.models import BriefVersion

    language_raw = None
    brief = session.get(BriefVersion, run.brief_version_id)
    if brief is not None:
        fields = json.loads(brief.fields_json)
        entry = fields.get("output_language_mode") or {}
        value = entry.get("value") if isinstance(entry, dict) else entry
        language_raw = str(value) if value else None
    return attach_run_memory(session, run.workspace_id, run.project_id, run.id, language_raw)


def attach_run_memory(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    brief_language_raw: str | None = None,
) -> list[dict]:
    """Snapshot the effective set for one run and record the `memory.applied`
    trace event; returns the payload list for the run's model calls.

    Snapshot-once: a run re-dispatched after failure keeps its original
    applied set, so later memory changes never mutate an in-flight or
    completed run's context (Spec consistency rules)."""

    existing = session.scalar(
        select(TraceEvent)
        .where(TraceEvent.run_id == run_id, TraceEvent.event_type == "memory.applied")
        .order_by(TraceEvent.created_at.desc())
    )
    if existing is not None:
        return json.loads(existing.payload_json).get("applied", [])

    result = effective_memory(session, workspace_id, project_id, brief_language_raw)
    session.add(
        TraceEvent(
            run_id=run_id,
            event_type="memory.applied",
            payload_json=json.dumps(
                {
                    "applied": result["applied"],
                    "conflicts": result["conflicts"],
                    "budget_skipped": result["budget_skipped"],
                    "project_disabled": result["project_disabled"],
                    "injected_chars": result["injected_chars"],
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return result["applied"]
