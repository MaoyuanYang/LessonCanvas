"""F016 D4: the activity-design specialist stage (lesson-plan path).

The designer runs once per lesson before the writer: one bounded model call
producing a structured activity design bound to blueprint objectives and the
lesson's retrieved evidence. Deterministic validation gates the design; one
corrective retry, then an honest per-lesson stage failure. The design is a
traced intermediate stored on the artifact row — evidence-visible only, never
teacher-editable (Spec D4).
"""

import json
import time

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter, parse_model_json
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.run_orchestration import service as run_service
from lessoncanvas.settings import get_settings

DESIGNER_RETRIES = 1

DESIGNER_SYSTEM = (
    "You are an activity-design specialist for senior-high English lessons. "
    "Given one lesson's confirmed objectives, context, and retrieved evidence, "
    "design the lesson's teaching activities. Respond with a JSON object only, "
    "shaped like "
    '{"design": {"objective_ids": ["obj-1"], "activities": [{"name": "...", '
    '"type": "...", "description": "...", "timing_minutes": 15}], '
    '"assessment_approach": "...", "evidence_references": '
    '[{"chunk_position": 1}]}}; objective_ids must come from the lesson\'s '
    "objective ids; chunk_position must reference retrieved chunks; no prose."
)


class DesignStageError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def normalize_design(raw: dict, objective_ids: set[str], hit_positions: set[int]) -> dict:
    """Bound and validate the design as untrusted model output.

    Unknown objective ids and evidence references that do not resolve to the
    lesson's retrieved set are dropped; dropping every objective id leaves the
    design invalid (the caller treats an empty binding as a validation
    failure, since a design must anchor to confirmed intent).
    """

    settings = get_settings()
    raw_ids = raw.get("objective_ids")
    bound = (
        [str(i) for i in raw_ids if str(i) in objective_ids]
        if isinstance(raw_ids, list)
        else []
    )
    activities: list[dict] = []
    for activity in raw.get("activities") or []:
        if not isinstance(activity, dict) or len(activities) >= settings.design_activity_count_max:
            continue
        name = str(activity.get("name") or "").strip()[:60]
        description = str(activity.get("description") or "").strip()[:400]
        timing = activity.get("timing_minutes")
        if not name or not description or not isinstance(timing, int):
            continue
        if not (
            settings.design_timing_minutes_min
            <= timing
            <= settings.design_timing_minutes_max
        ):
            continue
        activities.append(
            {
                "name": name,
                "type": str(activity.get("type") or "").strip()[:30] or None,
                "description": description,
                "timing_minutes": timing,
            }
        )
    references: list[dict] = []
    for reference in raw.get("evidence_references") or []:
        if not isinstance(reference, dict) or len(references) >= 6:
            continue
        position = reference.get("chunk_position")
        if isinstance(position, int) and position in hit_positions:
            references.append({"chunk_position": position})
    return {
        "objective_ids": bound,
        "activities": activities,
        "assessment_approach": str(raw.get("assessment_approach") or "").strip()[:400] or None,
        "evidence_references": references,
    }


def design_problems(design: dict) -> list[str]:
    """Deterministic validation of a normalized design (Spec: validated
    against blueprint objectives)."""

    settings = get_settings()
    problems: list[str] = []
    if not design.get("objective_ids"):
        problems.append("design binds to no blueprint objective of this lesson")
    count = len(design.get("activities") or [])
    if count < settings.design_activity_count_min:
        problems.append(f"design has fewer than {settings.design_activity_count_min} activities")
    return problems


def design_stage(
    session,
    run,
    artifact,
    context: dict,
    objective_ids: set[str],
    retrieval_result: dict | None,
    memory_context: list | None = None,
) -> dict | None:
    """Run the designer with one corrective retry; store the validated design.

    Returns the normalized design, or None after an honest stage failure
    (artifact left failed with a reason naming the design stage).
    """

    from lessoncanvas.modules.run_orchestration.caps import CapExhaustedError

    adapter = get_model_adapter()
    hits = (retrieval_result or {}).get("hits") or []
    hit_positions = {hit["position"] for hit in hits}
    lesson_payload = {
        **context,
        "objective_ids": sorted(objective_ids),
    }
    design: dict | None = None
    problems: list[str] = []
    attempts = 0
    while attempts <= DESIGNER_RETRIES:
        attempts += 1
        if not run_service.reserve_model_call(session, run.id):
            raise CapExhaustedError("model call cap reached")
        session.commit()
        artifact.status = "designing"
        session.commit()
        run_service.append_event(
            session,
            run.id,
            "lesson",
            {"lesson_index": artifact.lesson_index, "status": "designing"},
        )
        session.commit()

        user_payload = {
            "kind": "generation_design_lesson",
            "language_mode": artifact.language_mode,
            "lesson": lesson_payload,
            "grounding_state": (retrieval_result or {}).get("grounding_state", "none"),
        }
        if hits:
            user_payload["retrieved"] = [
                {"position": hit["position"], "text": hit["text"]} for hit in hits
            ]
        if memory_context:
            user_payload["memory_context"] = memory_context
        if attempts > 1 and problems:
            # Corrective retry carries the validation findings as labeled data.
            user_payload["previous_problems"] = problems
        started = time.monotonic()
        try:
            response = adapter.complete(
                DESIGNER_SYSTEM, json.dumps(user_payload, ensure_ascii=False)
            )
        except ModelProviderError:
            session.rollback()
            raise
        latency = int((time.monotonic() - started) * 1000)
        try:
            raw_design = parse_model_json(response.text).get("design", {})
        except ValueError:
            record_trace(
                session,
                run.id,
                "model.generation_design_lesson",
                {"prompt": user_payload, "response": response.text[:2000], "parse_failed": True},
                latency,
                usage=response,
            )
            session.commit()
            problems = ["unparseable design response"]
            continue
        design = normalize_design(raw_design, objective_ids, hit_positions)
        problems = design_problems(design)
        record_trace(
            session,
            run.id,
            "model.generation_design_lesson",
            {
                "prompt": user_payload,
                "response": design,
                "validation_problems": problems,
                "attempt": attempts,
            },
            latency,
            usage=response,
        )
        session.commit()
        if not problems:
            artifact.design_json = json.dumps(design, ensure_ascii=False)
            artifact.design_status = "ready"
            session.commit()
            return design

    artifact.design_status = "failed"
    artifact.status = "failed"
    artifact.failure_reason = (
        "design stage failed: " + ("; ".join(problems) if problems else "invalid design")
    )
    session.commit()
    run_service.append_event(
        session,
        run.id,
        "lesson",
        {"lesson_index": artifact.lesson_index, "status": "failed",
         "reason": artifact.failure_reason},
    )
    session.commit()
    return None
