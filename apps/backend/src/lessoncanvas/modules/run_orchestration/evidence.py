"""F006 Layered Run Evidence: owner-authorized derived projections over runs,
run events, traces, and interview rounds.

Read-only by construction (Spec D5): this module never mutates run, artifact,
version, or quota state. Its only write is the evidence narration's own trace
event and workspace-quota reservation (Spec D8). PostgreSQL tables remain the
only business truth; every projection here is derived at read time.
"""

import json
import threading
import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lessoncanvas.models import (
    DiscoveryRun,
    ExerciseArtifact,
    GenerationRun,
    InteractionMessage,
    LessonPlanArtifact,
    QuotaCounter,
    RunEvent,
    SlideDeckArtifact,
    TraceEvent,
)
from lessoncanvas.settings import get_settings

DISCOVERY_RUN_KINDS = ("discovery", "planning")
GENERATION_RUN_KINDS = ("lesson_plan", "slide_deck", "exercise")
NARRATION_EVENT_TYPE = "model.evidence_narration"
NARRATION_QUOTA_KEY = "evidence_narration"


class RunNotFoundError(Exception):
    pass


class NarrationQuotaError(Exception):
    pass


class InvalidEvidenceQueryError(Exception):
    pass


def _validated_cursor(cursor: str) -> str:
    try:
        micros_part, id_part = cursor.split("|", 1)
        if not micros_part.isdigit() or len(micros_part) != 19:
            raise ValueError(micros_part)
        uuid.UUID(id_part)
    except (ValueError, TypeError):
        raise InvalidEvidenceQueryError("invalid evidence cursor") from None
    return cursor


def estimated_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Write-time estimate from the settings price table; always labeled as an
    estimate at display time and never provider-billed truth (Spec D2)."""

    settings = get_settings()
    return round(
        prompt_tokens / 1_000_000 * settings.model_price_prompt_per_mtok
        + completion_tokens / 1_000_000 * settings.model_price_completion_per_mtok,
        6,
    )


def trace_model_label() -> str:
    settings = get_settings()
    return f"{settings.model_adapter}:{settings.deepseek_model}"


def _artifact_rows(session: Session, run: GenerationRun) -> list:
    kind = run.artifact_kind
    model = {
        "lesson_plan": LessonPlanArtifact,
        "slide_deck": SlideDeckArtifact,
        "exercise": ExerciseArtifact,
    }.get(kind)
    if model is None:
        return []
    return list(
        session.scalars(
            select(model).where(model.run_id == run.id).order_by(model.lesson_index)
        )
    )


def _artifact_out(artifact) -> dict:
    data = {
        "id": str(artifact.id),
        "lesson_index": artifact.lesson_index,
        "status": artifact.status,
        "failure_reason": artifact.failure_reason,
        "retry_count": artifact.retry_count,
    }
    for extra in ("slide_count", "category_count", "item_count"):
        if hasattr(artifact, extra):
            data[extra] = getattr(artifact, extra)
    return data


def _trace_stats(session: Session, run_id: uuid.UUID) -> dict:
    rows = list(
        session.scalars(select(TraceEvent).where(TraceEvent.run_id == run_id)).all()
    )
    cost_total = sum(
        event.cost_usd or 0.0
        for event in rows
        if event.prompt_tokens is not None
    )
    tokens_recorded = [event for event in rows if event.prompt_tokens is not None]
    model_latency = sum(
        event.latency_ms or 0 for event in rows if event.event_type.startswith("model.")
    )
    kinds = sorted({event.event_type for event in rows})
    model_events = [
        event for event in rows if event.event_type.startswith("model.")
    ]
    gaps: list[str] = []
    if any(event.prompt_tokens is None for event in model_events):
        gaps.append("token_usage_not_recorded")
    if any(event.model is None for event in model_events):
        gaps.append("model_not_recorded")
    return {
        "cost_usd_estimated": round(cost_total, 6),
        "cost_estimate_complete": bool(rows) and len(tokens_recorded) == len(rows),
        "model_latency_ms_total": model_latency,
        "trace_event_count": len(rows),
        "model_call_count": sum(
            1 for event in rows if event.event_type.startswith("model.")
        ),
        "tool_call_count": sum(
            1 for event in rows if event.event_type.startswith("tool.")
        ),
        "evidence_kinds": kinds,
        "telemetry_gaps": gaps,
    }


def _cursor_of(created_at, row_id) -> str:
    """URL-safe, lexicographically sortable cursor: fixed-width epoch micros
    plus row id (no '+' that query strings would decode as a space)."""

    micros = int(created_at.timestamp() * 1_000_000)
    return f"{micros:019d}|{row_id}"


def run_inventory(
    session: Session,
    project_id: uuid.UUID,
    after_cursor: str | None = None,
    limit: int | None = None,
) -> dict:
    settings = get_settings()
    page = min(
        limit or settings.evidence_inventory_page_default,
        settings.evidence_events_page_max,
    )

    entries: list[dict] = []

    discovery_runs = list(
        session.scalars(
            select(DiscoveryRun).where(DiscoveryRun.project_id == project_id)
        )
    )
    for run in discovery_runs:
        stats = _trace_stats(session, run.id)
        entries.append(
            {
                "run_id": str(run.id),
                "kind": run.kind,
                "status": run.status,
                "created_at": run.created_at,
                "cursor": _cursor_of(run.created_at, run.id),
                "model_calls": run.model_calls,
                "model_call_cap": None,
                "round_count": run.round_count,
                "brief_version": None,
                "blueprint_version": None,
                "difficulty": None,
                "language_mode": None,
                "complete_count": None,
                "total_count": None,
                **stats,
            }
        )

    generation_runs = list(
        session.scalars(
            select(GenerationRun).where(GenerationRun.project_id == project_id)
        )
    )
    for run in generation_runs:
        from lessoncanvas.models import BlueprintVersion, BriefVersion

        brief = session.get(BriefVersion, run.brief_version_id)
        blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
        artifacts = _artifact_rows(session, run)
        stats = _trace_stats(session, run.id)
        entries.append(
            {
                "run_id": str(run.id),
                "kind": run.artifact_kind,
                "status": run.status,
                "created_at": run.created_at,
                "cursor": _cursor_of(run.created_at, run.id),
                "model_calls": run.model_calls,
                "model_call_cap": run.model_call_cap,
                "round_count": None,
                "brief_version": brief.version if brief else None,
                "blueprint_version": blueprint.version if blueprint else None,
                "difficulty": run.difficulty,
                "language_mode": artifacts[0].language_mode if artifacts else None,
                "complete_count": sum(1 for a in artifacts if a.status == "complete"),
                "total_count": len(artifacts),
                **stats,
            }
        )

    entries.sort(key=lambda item: item["created_at"], reverse=True)
    if after_cursor:
        after_cursor = _validated_cursor(after_cursor)
        entries = [
            item
            for item in entries
            if _cursor_of(item["created_at"], item["run_id"]) < after_cursor
        ]
    page_rows = entries[:page]
    next_cursor = (
        page_rows[-1]["cursor"] if len(entries) > page and page_rows else None
    )
    return {
        "runs": [
            {**row, "created_at": row["created_at"].isoformat()} for row in page_rows
        ],
        "next_cursor": next_cursor,
    }


def resolve_run(
    session: Session, project_id: uuid.UUID, run_id: uuid.UUID
) -> tuple[str, DiscoveryRun | GenerationRun]:
    """Resolve a run of either family inside the owned project, or raise."""

    discovery = session.get(DiscoveryRun, run_id)
    if discovery is not None:
        if discovery.project_id != project_id:
            raise RunNotFoundError("run not found")
        return discovery.kind, discovery
    generation = session.get(GenerationRun, run_id)
    if generation is not None and generation.project_id == project_id:
        return generation.artifact_kind, generation
    raise RunNotFoundError("run not found")


def run_summary(session: Session, project_id: uuid.UUID, run_id: uuid.UUID) -> dict:
    kind, run = resolve_run(session, project_id, run_id)
    stats = _trace_stats(session, run.id)

    if isinstance(run, DiscoveryRun):
        return {
            "run_id": str(run.id),
            "kind": run.kind,
            "status": run.status,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
            "round_count": run.round_count,
            "model_calls": run.model_calls,
            "model_call_cap": None,
            "brief_version": None,
            "blueprint_version": None,
            "difficulty": None,
            "language_mode": None,
            "artifacts": [],
            "complete_count": None,
            "total_count": None,
            "interview_message_count": (
                session.scalar(
                    select(func.count(InteractionMessage.id)).where(
                        InteractionMessage.run_id == run.id
                    )
                )
                or 0
            ),
            "superseded_by": None,
            "recovery_view": None,
            **stats,
        }

    from lessoncanvas.models import BlueprintVersion, BriefVersion

    brief = session.get(BriefVersion, run.brief_version_id)
    blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
    artifacts = _artifact_rows(session, run)
    recovery_view = {
        "lesson_plan": "generation",
        "slide_deck": "decks",
        "exercise": "exercises",
    }.get(run.artifact_kind)
    superseded_by = None
    if run.status == "superseded":
        current_brief = session.scalar(
            select(BriefVersion)
            .where(BriefVersion.project_id == project_id)
            .order_by(BriefVersion.version.desc())
        )
        current_blueprint = session.scalar(
            select(BlueprintVersion)
            .where(BlueprintVersion.project_id == project_id)
            .order_by(BlueprintVersion.version.desc())
        )
        superseded_by = {
            "brief_version": current_brief.version if current_brief else None,
            "blueprint_version": current_blueprint.version if current_blueprint else None,
        }
    return {
        "run_id": str(run.id),
        "kind": run.artifact_kind,
        "status": run.status,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
        "round_count": None,
        "model_calls": run.model_calls,
        "model_call_cap": run.model_call_cap,
        "brief_version": brief.version if brief else None,
        "blueprint_version": blueprint.version if blueprint else None,
        "difficulty": run.difficulty,
        "language_mode": artifacts[0].language_mode if artifacts else None,
        "artifacts": [_artifact_out(artifact) for artifact in artifacts],
        "complete_count": sum(1 for a in artifacts if a.status == "complete"),
        "total_count": len(artifacts),
        "interview_message_count": None,
        "superseded_by": superseded_by,
        "recovery_view": (
            recovery_view
            if run.status in ("partial_failure", "capped_failure")
            else None
        ),
        **stats,
    }


def _trace_event_row(event: TraceEvent) -> dict:
    payload = json.loads(event.payload_json)
    lesson_index = payload.get("lesson_index") if isinstance(payload, dict) else None
    tokens_recorded = event.prompt_tokens is not None
    return {
        "cursor": _cursor_of(event.created_at, event.id),
        "source": "trace",
        "event_type": event.event_type,
        "created_at": event.created_at.isoformat(),
        "latency_ms": event.latency_ms,
        "prompt_tokens": event.prompt_tokens,
        "completion_tokens": event.completion_tokens,
        # Honesty rule: a stored cost is only meaningful when token usage was
        # recorded; otherwise the gap is explicit, never zero-masked (Spec D2/D9).
        "cost_usd": event.cost_usd if tokens_recorded else None,
        "model": event.model,
        "lesson_index": lesson_index,
        "payload": payload,
    }


def _run_event_row(event: RunEvent) -> dict:
    payload = json.loads(event.payload_json)
    lesson_index = payload.get("lesson_index") if isinstance(payload, dict) else None
    return {
        "cursor": _cursor_of(event.created_at, event.id),
        "source": "run_event",
        "event_type": event.event_type,
        "created_at": event.created_at.isoformat(),
        "latency_ms": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "cost_usd": None,
        "model": None,
        "lesson_index": lesson_index,
        "payload": payload,
    }


def _message_row(message: InteractionMessage) -> dict:
    return {
        "cursor": _cursor_of(message.created_at, message.id),
        "source": "interview",
        "event_type": "interview_round",
        "created_at": message.created_at.isoformat(),
        "latency_ms": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "cost_usd": None,
        "model": None,
        "lesson_index": None,
        "payload": {
            "role": message.role,
            "content": message.content,
            "round_index": message.round_index,
        },
    }


def evidence_events(
    session: Session,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    after_cursor: str | None = None,
    limit: int | None = None,
    kind: str | None = None,
) -> dict:
    _, run = resolve_run(session, project_id, run_id)
    settings = get_settings()
    page = min(
        limit or settings.evidence_events_page_default,
        settings.evidence_events_page_max,
    )

    rows: list[dict] = []
    for event in session.scalars(
        select(TraceEvent).where(TraceEvent.run_id == run.id)
    ):
        rows.append(_trace_event_row(event))
    if isinstance(run, DiscoveryRun):
        for message in session.scalars(
            select(InteractionMessage).where(InteractionMessage.run_id == run.id)
        ):
            rows.append(_message_row(message))
    else:
        for event in session.scalars(
            select(RunEvent).where(RunEvent.run_id == run.id)
        ):
            rows.append(_run_event_row(event))

    rows.sort(key=lambda row: (row["created_at"], row["cursor"]))
    known_kinds = {row["event_type"] for row in rows}
    if kind:
        if kind not in known_kinds:
            raise InvalidEvidenceQueryError("unknown evidence kind")
        rows = [row for row in rows if row["event_type"] == kind]
    if after_cursor:
        after_cursor = _validated_cursor(after_cursor)
        rows = [row for row in rows if row["cursor"] > after_cursor]
    page_rows = rows[:page]
    next_cursor = page_rows[-1]["cursor"] if len(rows) > page and page_rows else None
    return {
        "run_id": str(run.id),
        "events": page_rows,
        "next_cursor": next_cursor,
    }


# --- Evidence narration (Spec D8) -----------------------------------------


class _NarrationState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.tokens: list[str] = []
        self.complete = False
        self.stop_requested = False
        self.error: str | None = None

    def full_text(self) -> str:
        with self.lock:
            return "".join(self.tokens)


_narrations: dict[str, _NarrationState] = {}
_registry_lock = threading.Lock()


def get_evidence_narration(run_id: str) -> _NarrationState | None:
    with _registry_lock:
        return _narrations.get(run_id)


def reserve_narration_quota(session: Session, workspace_id: uuid.UUID) -> None:
    """Workspace-level reservation via quota counters (Spec D8): evidence
    narration never charges any run's model-call cap."""

    limit = get_settings().evidence_narration_quota_per_workspace
    counter = session.scalar(
        select(QuotaCounter).where(
            QuotaCounter.workspace_id == workspace_id,
            QuotaCounter.key == NARRATION_QUOTA_KEY,
        )
    )
    if counter is None:
        session.add(
            QuotaCounter(
                workspace_id=workspace_id,
                key=NARRATION_QUOTA_KEY,
                used=1,
                limit=limit,
            )
        )
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            counter = session.scalar(
                select(QuotaCounter).where(
                    QuotaCounter.workspace_id == workspace_id,
                    QuotaCounter.key == NARRATION_QUOTA_KEY,
                )
            )
            if counter is None or counter.used >= counter.limit:
                raise NarrationQuotaError("evidence narration quota exhausted") from None
            counter.used += 1
        return
    if counter.used >= counter.limit:
        raise NarrationQuotaError("evidence narration quota exhausted")
    counter.used += 1


def _narration_input(session: Session, run_id: uuid.UUID) -> dict:
    from lessoncanvas.db import SessionLocal

    narrate_session = SessionLocal()
    try:
        summary = run_summary(narrate_session, _project_of(narrate_session, run_id), run_id)
        return {
            "kind": "evidence_narration",
            "run_kind": summary["kind"],
            "status": summary["status"],
            "model_calls": summary["model_calls"],
            "model_call_cap": summary["model_call_cap"],
            "complete_count": summary["complete_count"],
            "total_count": summary["total_count"],
            "cost_usd_estimated": summary["cost_usd_estimated"],
            "model_latency_ms_total": summary["model_latency_ms_total"],
            "failed_artifacts": [
                {
                    "lesson_index": artifact["lesson_index"],
                    "failure_reason": artifact["failure_reason"],
                }
                for artifact in summary["artifacts"]
                if artifact["status"] == "failed"
            ],
            "telemetry_gaps": summary["telemetry_gaps"],
        }
    finally:
        narrate_session.close()


def _project_of(session: Session, run_id: uuid.UUID) -> uuid.UUID:
    discovery = session.get(DiscoveryRun, run_id)
    if discovery is not None:
        return discovery.project_id
    generation = session.get(GenerationRun, run_id)
    if generation is not None:
        return generation.project_id
    raise RunNotFoundError("run not found")


def _produce_narration(run_id: str, state: _NarrationState, user_payload: dict) -> None:
    from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter
    from lessoncanvas.db import SessionLocal

    started = time.monotonic()
    try:
        adapter = get_model_adapter()
        for token in adapter.stream(
            "You are a teaching-workbench explainer. Explain this run's outcome to the "
            "teacher in calm Simplified Chinese: what was requested, what happened, what "
            "failed and why, what recovered, and what it cost in estimated terms. Do not "
            "invent facts beyond the provided run summary.",
            json.dumps(user_payload, ensure_ascii=False),
        ):
            with state.condition:
                state.tokens.append(token)
                state.condition.notify_all()
    except ModelProviderError as error:
        with state.condition:
            state.error = str(error)
            state.complete = True
            state.condition.notify_all()
        with _registry_lock:
            _narrations.pop(run_id, None)
        return

    full_text = state.full_text()
    latency = int((time.monotonic() - started) * 1000)
    session = SessionLocal()
    try:
        session.add(
            TraceEvent(
                run_id=uuid.UUID(run_id),
                event_type=NARRATION_EVENT_TYPE,
                payload_json=json.dumps(
                    {"prompt": user_payload, "response": full_text}, ensure_ascii=False
                ),
                latency_ms=latency,
                cost_usd=None,
            )
        )
        session.commit()
    finally:
        session.close()
    with state.condition:
        state.complete = True
        state.condition.notify_all()
    # A completed narration is no longer active: a later narrate is a fresh
    # owner action with its own quota reservation (Spec D8).
    with _registry_lock:
        _narrations.pop(run_id, None)


def start_evidence_narration(
    session: Session, workspace_id: uuid.UUID, project_id: uuid.UUID, run_id: uuid.UUID
) -> _NarrationState:
    resolve_run(session, project_id, run_id)
    active = get_evidence_narration(str(run_id))
    if active is not None:
        return active
    reserve_narration_quota(session, workspace_id)
    session.commit()

    state = _NarrationState()
    with _registry_lock:
        _narrations[str(run_id)] = state
    payload = _narration_input(session, run_id)
    thread = threading.Thread(
        target=_produce_narration, args=(str(run_id), state, payload), daemon=True
    )
    thread.start()
    return state


def stop_evidence_narration(run_id: uuid.UUID) -> bool:
    state = get_evidence_narration(str(run_id))
    if state is None:
        return False
    with state.condition:
        state.stop_requested = True
        state.condition.notify_all()
    return True


def last_narration_text(session: Session, run_id: uuid.UUID) -> str | None:
    event = session.scalar(
        select(TraceEvent)
        .where(TraceEvent.run_id == run_id, TraceEvent.event_type == NARRATION_EVENT_TYPE)
        .order_by(TraceEvent.created_at.desc())
    )
    if event is None:
        return None
    payload = json.loads(event.payload_json)
    return payload.get("response")
