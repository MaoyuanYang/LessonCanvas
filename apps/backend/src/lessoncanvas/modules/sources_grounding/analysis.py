"""F016 D1: the source-analysis specialist.

One bounded model call per source, triggered when the parse task settles
successfully. Output is server-side normalized as untrusted input and stored
latest-wins in `source_analyses` with per-attempt telemetry; analysis failure
never blocks the source. Discovery and planning consume a bounded labeled
digest as subordinate context — analysis content never enters a system prompt
and never overrides confirmed intent.
"""

import json
import time
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from lessoncanvas.models import Source, SourceAnalysis, SourceChunk
from lessoncanvas.settings import get_settings

SOURCE_ANALYSIS_SYSTEM = (
    "You are a source-analysis specialist for senior-high English teaching "
    "materials. Analyze the provided source chunks and respond with a JSON "
    "object only, shaped like "
    '{"analysis": {"topics": ["..."], "language_points": ["..."], '
    '"suitability": {"recommended": true, "audience_fit": "...", '
    '"cautions": ["..."]}, "key_passages": [{"chunk_position": 1, '
    '"digest": "..."}]}}; chunk_position must reference one of the provided '
    "chunks; base every statement on the provided text; no prose."
)

# Server-side bounds applied during normalization (untrusted output).
_MAX_TOPICS = 8
_MAX_LANGUAGE_POINTS = 8
_MAX_KEY_PASSAGES = 6
_MAX_CAUTIONS = 5
_MAX_TOPIC_CHARS = 160
_MAX_PASSAGE_DIGEST_CHARS = 200
_MAX_FIT_CHARS = 300


class AnalysisInProgressError(Exception):
    """One analysis per source may be in flight (F016 D1 one-in-flight rule)."""


# A worker crash mid-analysis would otherwise strand the row in `analyzing`;
# a takeover is allowed once the claim is older than this bound.
ANALYSIS_CLAIM_STALE_AFTER_SECONDS = 10 * 60


def _bounded_texts(values: object, limit: int, chars: int) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values[:limit]:
        if isinstance(value, str) and value.strip():
            out.append(value.strip()[:chars])
    return out


def normalize_analysis(raw: dict, chunk_positions: set[int]) -> dict:
    """Bound and validate model output as untrusted input.

    Key passages whose chunk_position does not resolve to a real chunk are
    dropped (never fabricated); unknown fields are discarded entirely.
    """

    suitability_raw = raw.get("suitability")
    suitability_raw = suitability_raw if isinstance(suitability_raw, dict) else {}
    recommended = suitability_raw.get("recommended")
    passages: list[dict] = []
    for passage in raw.get("key_passages") or []:
        if not isinstance(passage, dict) or len(passages) >= _MAX_KEY_PASSAGES:
            continue
        position = passage.get("chunk_position")
        digest = passage.get("digest")
        if not isinstance(position, int) or position not in chunk_positions:
            continue
        if not isinstance(digest, str) or not digest.strip():
            continue
        passages.append(
            {"chunk_position": position, "digest": digest.strip()[:_MAX_PASSAGE_DIGEST_CHARS]}
        )
    return {
        "topics": _bounded_texts(raw.get("topics"), _MAX_TOPICS, _MAX_TOPIC_CHARS),
        "language_points": _bounded_texts(
            raw.get("language_points"), _MAX_LANGUAGE_POINTS, _MAX_TOPIC_CHARS
        ),
        "suitability": {
            "recommended": bool(recommended) if recommended is not None else None,
            "audience_fit": (
                str(suitability_raw.get("audience_fit") or "").strip()[:_MAX_FIT_CHARS]
                or None
            ),
            "cautions": _bounded_texts(
                suitability_raw.get("cautions"), _MAX_CAUTIONS, _MAX_TOPIC_CHARS
            ),
        },
        "key_passages": passages,
    }


def _analysis_row(session: Session, source: Source) -> SourceAnalysis:
    row = session.scalars(
        select(SourceAnalysis).where(SourceAnalysis.source_id == source.id)
    ).first()
    if row is None:
        row = SourceAnalysis(
            source_id=source.id,
            project_id=source.project_id,
            workspace_id=source.workspace_id,
            status="pending",
        )
        session.add(row)
        session.flush()
    return row


def claim_analysis(session: Session, source: Source) -> SourceAnalysis:
    """Transition the row to analyzing unless one is already in flight.

    The one-in-flight rule makes duplicate triggers (retry while analyzing,
    double parse settlement) explicit errors instead of silent double calls.
    A stale claim (crashed worker) older than the takeover bound is allowed
    to be superseded, so the row can never be stranded in `analyzing`.
    """

    row = _analysis_row(session, source)
    if row.status == "analyzing":
        claimed_at = row.updated_at
        if claimed_at is not None:
            age = datetime.now(claimed_at.tzinfo) - claimed_at
            if age.total_seconds() < ANALYSIS_CLAIM_STALE_AFTER_SECONDS:
                raise AnalysisInProgressError(
                    "analysis already in flight for this source"
                )
    row.status = "analyzing"
    row.error = None
    session.flush()
    return row


def analyze_source(session: Session, source_id: uuid.UUID) -> SourceAnalysis:
    """Run one bounded analysis call and settle the row ready or failed."""

    from lessoncanvas.adapters.model import (
        ModelProviderError,
        get_model_adapter,
        parse_model_json,
    )
    from lessoncanvas.modules.run_orchestration.evidence import (
        estimated_cost_usd,
        trace_model_label,
    )

    source = session.get(Source, source_id)
    if source is None or source.status != "ready":
        raise ValueError("source is not ready for analysis")
    row = claim_analysis(session, source)
    chunks = list(
        session.scalars(
            select(SourceChunk)
            .where(SourceChunk.source_id == source.id)
            .order_by(SourceChunk.position)
        ).all()
    )
    payload = {
        "kind": "source_analysis",
        "filename": source.filename,
        "chunks": [
            {"position": chunk.position, "excerpt": chunk.text[:200]}
            for chunk in chunks[:12]
        ],
    }
    started = time.monotonic()
    try:
        response = get_model_adapter().complete(
            SOURCE_ANALYSIS_SYSTEM, json.dumps(payload, ensure_ascii=False)
        )
        data = parse_model_json(response.text)
        normalized = normalize_analysis(
            data.get("analysis") or {}, {chunk.position for chunk in chunks}
        )
        latency = int((time.monotonic() - started) * 1000)
        has_usage = response.prompt_tokens or response.completion_tokens
        row.status = "ready"
        row.payload_json = json.dumps(normalized, ensure_ascii=False)
        row.error = None
        row.model = trace_model_label()
        row.latency_ms = latency
        row.prompt_tokens = response.prompt_tokens or None
        row.completion_tokens = response.completion_tokens or None
        row.cost_usd = (
            estimated_cost_usd(response.prompt_tokens, response.completion_tokens)
            if has_usage
            else None
        )
    except (ModelProviderError, ValueError) as error:
        row.status = "failed"
        row.payload_json = None
        row.error = str(error)[:500] or error.__class__.__name__
        row.model = None
        row.latency_ms = None
        row.prompt_tokens = None
        row.completion_tokens = None
        row.cost_usd = None
    session.flush()
    return row


def _digest_entry(analysis: SourceAnalysis) -> dict:
    payload = json.loads(analysis.payload_json or "{}")
    return {
        "filename": None,  # filled by the caller (join with the source row)
        "topics": payload.get("topics") or [],
        "language_points": payload.get("language_points") or [],
        "suitability": payload.get("suitability") or {},
        "key_passages": payload.get("key_passages") or [],
    }


def analyses_digest(session: Session, project_id: uuid.UUID) -> dict:
    """Bounded labeled digest of ready analyses for discovery/planning
    payloads (F016 spec: subordinate context with explicit state)."""

    settings = get_settings()
    sources = list(
        session.scalars(
            select(Source).where(
                Source.project_id == project_id, Source.status == "ready"
            )
        ).all()
    )
    if not sources:
        return {
            "state": "none",
            "reason": "no ready sources",
            "budget_chars": settings.analysis_digest_budget_chars,
            "sources": [],
        }
    analyses = {
        analysis.source_id: analysis
        for analysis in session.scalars(
            select(SourceAnalysis).where(
                SourceAnalysis.project_id == project_id,
                SourceAnalysis.status == "ready",
            )
        ).all()
    }
    entries: list[dict] = []
    used = 0
    truncated = False
    failed_count = 0
    for source in sources:
        analysis = analyses.get(source.id)
        if analysis is None:
            if _has_failed_analysis(session, source.id):
                failed_count += 1
            continue
        entry = _digest_entry(analysis)
        entry["filename"] = source.filename
        cost = len(json.dumps(entry, ensure_ascii=False))
        if used + cost > settings.analysis_digest_budget_chars:
            truncated = True
            continue
        used += cost
        entries.append(entry)
    if not entries:
        return {
            "state": "none",
            "reason": (
                "no ready analyses"
                if failed_count == 0
                else f"no ready analyses ({failed_count} failed)"
            ),
            "budget_chars": settings.analysis_digest_budget_chars,
            "sources": [],
        }
    state = "ready" if len(entries) == len(sources) else "partial"
    digest: dict = {
        "state": state,
        "budget_chars": settings.analysis_digest_budget_chars,
        "sources": entries,
    }
    if truncated:
        digest["truncated"] = True
    if failed_count:
        digest["failed_sources"] = failed_count
    return digest


def _has_failed_analysis(session: Session, source_id: uuid.UUID) -> bool:
    row = session.scalars(
        select(SourceAnalysis.status).where(SourceAnalysis.source_id == source_id)
    ).first()
    return row == "failed"
