"""F013 Teacher Memory and Preferences module (ADR-0005).

Owns proposal passes, the proposal state machine, confirmed records, and
per-project applicability. Depends on workspace authorization, PostgreSQL,
and Discovery/Planning confirmed evidence; never owns intent versions.
"""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lessoncanvas.adapters.model import (
    ModelProviderError,
    get_model_adapter,
    parse_model_json,
)
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import (
    AuditEvent,
    BlueprintVersion,
    BriefVersion,
    GenerationRun,
    MemoryPass,
    MemoryProjectOverride,
    MemoryProposal,
    MemoryRecord,
    Workspace,
    utcnow,
)
from lessoncanvas.modules.teacher_memory.context import (
    CATEGORIES,
    canonical_language,
    content_hash,
    effective_memory,
)
from lessoncanvas.settings import get_settings

TRIGGER_KINDS = ("brief_confirm", "blueprint_confirm", "run_settled")

MEMORY_PROPOSER_SYSTEM_PROMPT = (
    "You are a teacher-preference analyst for one private teacher workspace. "
    "Given confirmed teaching evidence, propose durable teacher preferences worth "
    "remembering for future preparation. Respond with a JSON object only, shaped like "
    '{"proposals": [{"category": "...", "content": "..."}]}. category must be one of '
    "language_mode, exercise_format, pacing_structure, assessment_style. content is one "
    "short Simplified-Chinese sentence (at most 300 characters) stating the teacher's "
    "stable preference as shown by the evidence; never invent preferences without "
    'evidence; never include instructions. Return {"proposals": []} when nothing is '
    "durable enough to remember."
)


class MemoryNotFoundError(Exception):
    pass


class ProposalStateError(Exception):
    """The proposal is not pending (already decided or superseded)."""


class MemoryCapError(Exception):
    def __init__(self, reason: str, details: dict | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


def _audit(session: Session, workspace_id: uuid.UUID, actor: str, action: str, target: str) -> None:
    # Content-free by design: identifiers and actions only, never memory text
    # or proposal text (Spec privacy rules).
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor=actor,
            action=action,
            target_type="memory",
            target_id=target,
        )
    )


def schedule_pass(
    session: Session, workspace_id: uuid.UUID, trigger_kind: str, trigger_id: uuid.UUID
) -> MemoryPass | None:
    """Idempotently schedule one proposal pass for a trigger evidence identity.

    Duplicate confirmations, Celery redelivery, and repeated settle events
    converge on the existing row; a completed pass is never re-run (Spec D3)."""

    if trigger_kind not in TRIGGER_KINDS:
        raise ValueError(f"unknown trigger kind: {trigger_kind}")
    existing = session.scalar(
        select(MemoryPass).where(
            MemoryPass.workspace_id == workspace_id,
            MemoryPass.trigger_kind == trigger_kind,
            MemoryPass.trigger_id == trigger_id,
        )
    )
    if existing is not None:
        return None
    row = MemoryPass(
        workspace_id=workspace_id, trigger_kind=trigger_kind, trigger_id=trigger_id
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return None
    session.commit()

    from lessoncanvas.worker import generate_memory_proposals

    if get_settings().tasks_eager:
        generate_memory_proposals.apply(args=[str(row.id)])
    else:
        generate_memory_proposals.delay(str(row.id))
    return row


def retry_pass(session: Session, workspace: Workspace, pass_id: uuid.UUID) -> MemoryPass:
    row = session.get(MemoryPass, pass_id)
    if row is None or row.workspace_id != workspace.id:
        raise MemoryNotFoundError("memory pass not found")
    if row.status != "failed":
        raise ProposalStateError("pass is not in a retryable state")
    _audit(session, workspace.id, workspace.subject, "memory.pass_retry", str(row.id))
    session.commit()

    from lessoncanvas.worker import generate_memory_proposals

    if get_settings().tasks_eager:
        generate_memory_proposals.apply(args=[str(row.id)])
    else:
        generate_memory_proposals.delay(str(row.id))
    # Re-read so an eagerly-executed retry reflects the settled status.
    session.expire(row)
    _ = row.status
    return row


def _brief_language(fields: dict) -> str | None:
    entry = fields.get("output_language_mode") or {}
    value = entry.get("value") if isinstance(entry, dict) else entry
    return str(value) if value else None


def _evidence_for_pass(session: Session, row: MemoryPass) -> dict | None:
    """Build the bounded confirmed-evidence payload for one pass; None means
    the evidence rows are gone (deleted versions/run), so the pass settles
    completed with zero proposals instead of failing."""

    if row.trigger_kind == "brief_confirm":
        version = session.get(BriefVersion, row.trigger_id)
        if version is None:
            return None
        fields = json.loads(version.fields_json)
        return {
            "kind": "brief_confirm",
            "brief_version": version.version,
            "fields": {
                name: (entry or {}).get("value") if isinstance(entry, dict) else entry
                for name, entry in fields.items()
            },
        }
    if row.trigger_kind == "blueprint_confirm":
        version = session.get(BlueprintVersion, row.trigger_id)
        if version is None:
            return None
        payload = json.loads(version.payload_json)
        unit = payload.get("unit") or {}
        return {
            "kind": "blueprint_confirm",
            "blueprint_version": version.version,
            "unit": {
                "title": unit.get("title"),
                "assessment_intent": unit.get("assessment_intent"),
                "objective_texts": [
                    str(item.get("text") or "") for item in (unit.get("objectives") or [])
                ][:12],
            },
            "lessons": [
                {
                    "index": lesson.get("index"),
                    "title": lesson.get("title"),
                    "period_count": lesson.get("period_count"),
                }
                for lesson in (payload.get("lessons") or [])[:20]
            ],
        }
    run = session.get(GenerationRun, row.trigger_id)
    if run is None:
        return None
    brief = session.get(BriefVersion, run.brief_version_id)
    blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
    evidence: dict = {
        "kind": "run_settled",
        "artifact_kind": run.artifact_kind,
        "difficulty": run.difficulty,
    }
    if brief is not None:
        fields = json.loads(brief.fields_json)
        evidence["brief_fields"] = {
            name: (entry or {}).get("value") if isinstance(entry, dict) else entry
            for name, entry in fields.items()
        }
    if blueprint is not None:
        payload = json.loads(blueprint.payload_json)
        unit = payload.get("unit") or {}
        evidence["blueprint_unit"] = {
            "title": (unit.get("title")),
            "assessment_intent": unit.get("assessment_intent"),
        }
    return evidence


def _existing_summary(session: Session, workspace_id: uuid.UUID) -> list[dict]:
    """Category + text of records and pending proposals, so a live model can
    avoid duplicates; supplied as labeled data, never as instructions."""

    entries: list[dict] = []
    for record in session.scalars(
        select(MemoryRecord).where(MemoryRecord.workspace_id == workspace_id)
    ):
        entries.append({"category": record.category, "content": record.content})
    for proposal in session.scalars(
        select(MemoryProposal).where(
            MemoryProposal.workspace_id == workspace_id, MemoryProposal.status == "pending"
        )
    ):
        entries.append({"category": proposal.category, "content": proposal.content})
    return entries[:20]


def _persist_proposals(
    session: Session, pass_row: MemoryPass, raw_proposals: list, language_raw: str | None
) -> list[MemoryProposal]:
    """Validate untrusted model output, dedupe against confirmed/pending/
    rejected state (superseded carries no penalty), supersede the pending
    slot per category, and persist at most the capped number of survivors."""

    settings = get_settings()
    seen: set[tuple[str, str]] = set()
    valid: list[tuple[str, str, str]] = []
    for raw in raw_proposals:
        if not isinstance(raw, dict):
            continue
        category = raw.get("category")
        content = raw.get("content")
        if category not in CATEGORIES or not isinstance(content, str):
            continue
        content = content.strip()
        if not content or len(content) > settings.memory_record_max_chars:
            continue
        digest = content_hash(content)
        if (category, digest) in seen:
            continue
        seen.add((category, digest))
        valid.append((category, content, digest))

    blocked: set[tuple[str, str]] = {
        (record.category, record.content_hash)
        for record in session.scalars(
            select(MemoryRecord).where(MemoryRecord.workspace_id == pass_row.workspace_id)
        )
    }
    for proposal in session.scalars(
        select(MemoryProposal).where(MemoryProposal.workspace_id == pass_row.workspace_id)
    ):
        if proposal.status in ("pending", "rejected"):
            blocked.add((proposal.category, proposal.content_hash))

    evidence_refs = {
        "brief_version_id": pass_row.trigger_id
        if pass_row.trigger_kind == "brief_confirm"
        else None,
        "blueprint_version_id": pass_row.trigger_id
        if pass_row.trigger_kind == "blueprint_confirm"
        else None,
        "generation_run_id": pass_row.trigger_id
        if pass_row.trigger_kind == "run_settled"
        else None,
    }
    language_value = canonical_language(language_raw)

    created: list[MemoryProposal] = []
    for category, content, digest in valid:
        if (category, digest) in blocked:
            continue
        if len(created) >= settings.memory_max_candidates_per_pass:
            break
        pending = session.scalar(
            select(MemoryProposal).where(
                MemoryProposal.workspace_id == pass_row.workspace_id,
                MemoryProposal.category == category,
                MemoryProposal.status == "pending",
            )
        )
        if pending is not None:
            pending.status = "superseded"
            pending.decided_at = utcnow()
        proposal = MemoryProposal(
            workspace_id=pass_row.workspace_id,
            pass_id=pass_row.id,
            category=category,
            content=content,
            content_hash=digest,
            value=language_value if category == "language_mode" else None,
            **evidence_refs,
        )
        session.add(proposal)
        created.append(proposal)
    session.flush()
    return created


def _language_raw_from_evidence(evidence: dict) -> str | None:
    if evidence.get("kind") == "brief_confirm":
        return _brief_language(evidence.get("fields") or {})
    if evidence.get("kind") == "run_settled":
        return _brief_language(evidence.get("brief_fields") or {})
    return None


def execute_pass(pass_id: uuid.UUID) -> str:
    """Worker entry: run one bounded proposal call to a settled pass state.

    Best-effort by contract — a provider failure settles this pass's own
    `failed` state and never touches the confirmation/run that triggered it."""

    from lessoncanvas.modules.run_orchestration.evidence import estimated_cost_usd

    session = SessionLocal()
    try:
        row = session.get(MemoryPass, pass_id)
        if row is None:
            return "missing_pass"
        if row.status == "completed":
            return "completed"
        row.status = "running"
        session.commit()
        try:
            evidence = _evidence_for_pass(session, row)
            if evidence is None:
                row.status = "completed"
                row.proposal_count = 0
                row.completed_at = utcnow()
                session.commit()
                return "completed"
            settings = get_settings()
            payload = {
                "kind": "memory_propose",
                "max_proposals": settings.memory_max_candidates_per_pass,
                "categories": list(CATEGORIES),
                "evidence": evidence,
                "existing": _existing_summary(session, row.workspace_id),
            }
            adapter = get_model_adapter()
            response = adapter.complete(
                MEMORY_PROPOSER_SYSTEM_PROMPT,
                json.dumps(payload, ensure_ascii=False),
            )
            data = parse_model_json(response.text)
            created = _persist_proposals(
                session, row, data.get("proposals", []), _language_raw_from_evidence(evidence)
            )
            row.status = "completed"
            row.proposal_count = len(created)
            row.prompt_tokens = response.prompt_tokens or None
            row.completion_tokens = response.completion_tokens or None
            if response.prompt_tokens and response.completion_tokens:
                row.cost_usd = estimated_cost_usd(
                    response.prompt_tokens, response.completion_tokens
                )
            row.completed_at = utcnow()
            workspace = session.get(Workspace, row.workspace_id)
            if workspace is not None:
                _audit(
                    session, row.workspace_id, workspace.subject, "memory.pass", str(row.id)
                )
            session.commit()
            return "completed"
        except (ModelProviderError, ValueError) as error:
            session.rollback()
            row = session.get(MemoryPass, pass_id)
            if row is None:
                return "missing_pass"
            row.status = "failed"
            session.commit()
            _ = error  # provider/validation failures settle the pass, never the trigger flow
            return "failed"
    finally:
        session.close()


def _record_out(session: Session, record: MemoryRecord) -> dict:
    disabled_count = (
        session.scalar(
            select(MemoryProjectOverride.id).where(
                MemoryProjectOverride.record_id == record.id,
                MemoryProjectOverride.enabled.is_(False),
            )
        )
        is not None
    )
    return {
        "id": str(record.id),
        "category": record.category,
        "content": record.content,
        "value": record.value,
        "brief_version_id": str(record.brief_version_id) if record.brief_version_id else None,
        "blueprint_version_id": (
            str(record.blueprint_version_id) if record.blueprint_version_id else None
        ),
        "generation_run_id": (
            str(record.generation_run_id) if record.generation_run_id else None
        ),
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "has_project_disabled": disabled_count,
    }


def _proposal_out(proposal: MemoryProposal, trigger_kind: str | None = None) -> dict:
    return {
        "id": str(proposal.id),
        "category": proposal.category,
        "content": proposal.content,
        "value": proposal.value,
        "status": proposal.status,
        "trigger_kind": trigger_kind,
        "brief_version_id": (
            str(proposal.brief_version_id) if proposal.brief_version_id else None
        ),
        "blueprint_version_id": (
            str(proposal.blueprint_version_id) if proposal.blueprint_version_id else None
        ),
        "generation_run_id": (
            str(proposal.generation_run_id) if proposal.generation_run_id else None
        ),
        "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
        "decided_at": proposal.decided_at.isoformat() if proposal.decided_at else None,
    }


def _pass_out(row: MemoryPass) -> dict:
    return {
        "id": str(row.id),
        "trigger_kind": row.trigger_kind,
        "trigger_id": str(row.trigger_id),
        "status": row.status,
        "proposal_count": row.proposal_count,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "cost_usd": row.cost_usd,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def list_memory(session: Session, workspace: Workspace) -> dict:
    settings = get_settings()
    records = list(
        session.scalars(
            select(MemoryRecord)
            .where(MemoryRecord.workspace_id == workspace.id)
            .order_by(MemoryRecord.created_at.desc())
        )
    )
    proposals = list(
        session.scalars(
            select(MemoryProposal)
            .where(MemoryProposal.workspace_id == workspace.id)
            .order_by(MemoryProposal.created_at.desc())
        )
    )
    passes = list(
        session.scalars(
            select(MemoryPass)
            .where(MemoryPass.workspace_id == workspace.id)
            .order_by(MemoryPass.created_at.desc())
        )
    )
    # U5: conflict summary against the workspace's most recent confirmed brief
    # (per-project conflicts render in the project's applied-context region).
    latest_brief_language = session.scalar(
        select(BriefVersion.fields_json)
        .where(BriefVersion.workspace_id == workspace.id)
        .order_by(BriefVersion.created_at.desc())
        .limit(1)
    )
    brief_language = (
        canonical_language(_brief_language(json.loads(latest_brief_language)))
        if latest_brief_language
        else None
    )
    record_outs = []
    for record in records:
        out = _record_out(session, record)
        out["conflicts_with_latest_brief"] = bool(
            record.category == "language_mode"
            and brief_language
            and record.value
            and record.value != brief_language
        )
        record_outs.append(out)
    pass_kinds = {
        row.id: row.trigger_kind
        for row in session.scalars(
            select(MemoryPass).where(MemoryPass.workspace_id == workspace.id)
        )
    }
    return {
        "records": record_outs,
        "proposals": [
            _proposal_out(proposal, pass_kinds.get(proposal.pass_id))
            for proposal in proposals
        ],
        "passes": [_pass_out(row) for row in passes],
        "quota": {"used": len(records), "limit": settings.memory_max_records},
    }


def _get_proposal(session: Session, workspace: Workspace, proposal_id: uuid.UUID) -> MemoryProposal:
    proposal = session.get(MemoryProposal, proposal_id)
    if proposal is None or proposal.workspace_id != workspace.id:
        raise MemoryNotFoundError("memory proposal not found")
    return proposal


def confirm_proposal(
    session: Session, workspace: Workspace, proposal_id: uuid.UUID, edited_content: str | None
) -> tuple[MemoryRecord, bool]:
    """Confirm one pending proposal into a workspace record (Spec D2/D8).

    The record cap is enforced under the workspace-row lock (F011 D9 race
    pattern); an identical already-confirmed record converges instead of
    duplicating. Returns (record, created)."""

    settings = get_settings()
    proposal = _get_proposal(session, workspace, proposal_id)
    if proposal.status != "pending":
        raise ProposalStateError("proposal is not pending")
    content = (edited_content if edited_content is not None else proposal.content).strip()
    if not content or len(content) > settings.memory_record_max_chars:
        raise MemoryCapError(
            "record content exceeds the length cap",
            {"max_chars": settings.memory_record_max_chars},
        )
    digest = content_hash(content)

    session.execute(select(Workspace).where(Workspace.id == workspace.id).with_for_update())
    identical = session.scalar(
        select(MemoryRecord)
        .where(
            MemoryRecord.workspace_id == workspace.id,
            MemoryRecord.category == proposal.category,
            MemoryRecord.content_hash == digest,
        )
        .limit(1)
    )
    if identical is not None:
        # Converge on the identical existing record instead of duplicating.
        proposal.status = "confirmed"
        proposal.decided_at = utcnow()
        _audit(session, workspace.id, workspace.subject, "memory.confirm", str(proposal.id))
        session.flush()
        return identical, False
    used = (
        len(
            list(
                session.scalars(
                    select(MemoryRecord.id).where(MemoryRecord.workspace_id == workspace.id)
                )
            )
        )
        or 0
    )
    if used >= settings.memory_max_records:
        raise MemoryCapError(
            "memory record limit reached",
            {"limit": settings.memory_max_records},
        )
    record = MemoryRecord(
        workspace_id=workspace.id,
        category=proposal.category,
        content=content,
        content_hash=digest,
        value=proposal.value,
        brief_version_id=proposal.brief_version_id,
        blueprint_version_id=proposal.blueprint_version_id,
        generation_run_id=proposal.generation_run_id,
    )
    session.add(record)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ProposalStateError("proposal was decided concurrently") from error
    proposal.status = "confirmed"
    proposal.decided_at = utcnow()
    _audit(session, workspace.id, workspace.subject, "memory.confirm", str(proposal.id))
    session.flush()
    return record, True


def reject_proposal(
    session: Session, workspace: Workspace, proposal_id: uuid.UUID
) -> MemoryProposal:
    proposal = _get_proposal(session, workspace, proposal_id)
    if proposal.status != "pending":
        raise ProposalStateError("proposal is not pending")
    try:
        proposal.status = "rejected"
        proposal.decided_at = utcnow()
        _audit(session, workspace.id, workspace.subject, "memory.reject", str(proposal.id))
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ProposalStateError("proposal was decided concurrently") from error
    return proposal


def edit_record(
    session: Session, workspace: Workspace, record_id: uuid.UUID, content: str
) -> MemoryRecord:
    settings = get_settings()
    record = session.get(MemoryRecord, record_id)
    if record is None or record.workspace_id != workspace.id:
        raise MemoryNotFoundError("memory record not found")
    content = content.strip()
    if not content or len(content) > settings.memory_record_max_chars:
        raise MemoryCapError(
            "record content exceeds the length cap",
            {"max_chars": settings.memory_record_max_chars},
        )
    record.content = content
    record.content_hash = content_hash(content)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise MemoryCapError("an identical memory record already exists") from error
    _audit(session, workspace.id, workspace.subject, "memory.edit", str(record.id))
    session.flush()
    return record


def delete_record(session: Session, workspace: Workspace, record_id: uuid.UUID) -> None:
    record = session.get(MemoryRecord, record_id)
    if record is None or record.workspace_id != workspace.id:
        raise MemoryNotFoundError("memory record not found")
    # Hard delete with its per-project overrides and pending proposals that
    # would recreate the deleted record identically (Spec deletion rules).
    for override in session.scalars(
        select(MemoryProjectOverride).where(MemoryProjectOverride.record_id == record.id)
    ):
        session.delete(override)
    for proposal in session.scalars(
        select(MemoryProposal).where(
            MemoryProposal.workspace_id == workspace.id,
            MemoryProposal.category == record.category,
            MemoryProposal.content_hash == record.content_hash,
            MemoryProposal.status == "pending",
        )
    ):
        session.delete(proposal)
    _audit(session, workspace.id, workspace.subject, "memory.delete", str(record.id))
    session.delete(record)
    session.flush()


def project_memory(session: Session, workspace: Workspace, project_id: uuid.UUID) -> dict:
    brief_fields_json = session.scalar(
        select(BriefVersion.fields_json)
        .where(BriefVersion.project_id == project_id)
        .order_by(BriefVersion.version.desc())
        .limit(1)
    )
    language_raw = _brief_language(json.loads(brief_fields_json)) if brief_fields_json else None
    effective = effective_memory(session, workspace.id, project_id, language_raw)
    records = list(
        session.scalars(
            select(MemoryRecord)
            .where(MemoryRecord.workspace_id == workspace.id)
            .order_by(MemoryRecord.created_at.desc())
        )
    )
    disabled = {
        row.record_id: row.enabled
        for row in session.scalars(
            select(MemoryProjectOverride).where(MemoryProjectOverride.project_id == project_id)
        )
    }
    record_outs = []
    for record in records:
        out = _record_out(session, record)
        out["project_enabled"] = disabled.get(record.id, True)
        record_outs.append(out)
    return {"effective": effective, "records": record_outs}


def set_override(
    session: Session,
    workspace: Workspace,
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    enabled: bool,
) -> MemoryProjectOverride:
    record = session.get(MemoryRecord, record_id)
    if record is None or record.workspace_id != workspace.id:
        raise MemoryNotFoundError("memory record not found")
    override = session.scalar(
        select(MemoryProjectOverride).where(
            MemoryProjectOverride.project_id == project_id,
            MemoryProjectOverride.record_id == record_id,
        )
    )
    if override is None:
        override = MemoryProjectOverride(
            project_id=project_id,
            workspace_id=workspace.id,
            record_id=record_id,
            enabled=enabled,
        )
        session.add(override)
    else:
        override.enabled = enabled
    _audit(
        session,
        workspace.id,
        workspace.subject,
        "memory.override_enable" if enabled else "memory.override_disable",
        str(record_id),
    )
    session.flush()
    return override


def memory_state_snapshot(session: Session, workspace_id: uuid.UUID) -> str:
    """F009 comparability pinning (Spec D6): bind the applied memory-set
    revision list at evaluation-creation time. Harness workspaces never
    confirm proposals, so their snapshot is the empty set by construction."""

    records = list(
        session.scalars(
            select(MemoryRecord)
            .where(MemoryRecord.workspace_id == workspace_id)
            .order_by(MemoryRecord.created_at)
        )
    )
    if not records:
        return json.dumps(
            {"memory_state": "empty", "record_ids": [], "record_hashes": []},
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "memory_state": "revision-set",
            "record_ids": [str(record.id) for record in records],
            "record_hashes": [record.content_hash for record in records],
        },
        ensure_ascii=False,
    )
