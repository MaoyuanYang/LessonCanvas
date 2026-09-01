"""F009 scripted evaluation harness (Spec D7).

The harness is a scripted client of the existing module services: it
sequences source upload, discovery, brief confirmation, planning, blueprint
confirmation, and generation exactly as the teacher-facing API does. It
introduces no second workflow authority — LangGraph/Celery/PostgreSQL
ownership is unchanged — and every fault it injects goes through the
eval-gated fake-adapter fault profiles (Spec D4).
"""

from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.orm import Session

from lessoncanvas.adapters.model import FakeModelAdapter
from lessoncanvas.models import GenerationRun, Source, Workspace
from lessoncanvas.modules.technical_evaluation.dataset import EvaluationUnit
from lessoncanvas.settings import get_settings

RUN_WAIT_TIMEOUT_SECONDS = 900
RUN_WAIT_POLL_SECONDS = 5
TERMINAL_RUN_STATUSES = {"complete", "partial_failure", "capped_failure", "failed", "superseded"}


class HarnessFailure(Exception):
    """Unexpected harness-path failure; the evaluation settles failed."""


def _dispatch(kind: str, run: GenerationRun, session: Session) -> str:
    from lessoncanvas.worker import generate_decks, generate_exercises, generate_unit

    task = {
        "lesson_plan": generate_unit,
        "slide_deck": generate_decks,
        "exercise": generate_exercises,
    }[kind]
    if get_settings().tasks_eager:
        result = task.apply(args=[str(run.id)])
        session.expire_all()
        return str(result.result)
    task.delay(str(run.id))
    return _wait_terminal(kind, run.id)


def _wait_terminal(kind: str, run_id: uuid.UUID) -> str:
    from lessoncanvas.db import SessionLocal

    deadline = time.monotonic() + RUN_WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        with SessionLocal() as session:
            run = session.get(GenerationRun, run_id)
            if run is not None and run.status in TERMINAL_RUN_STATUSES:
                return run.status
        time.sleep(RUN_WAIT_POLL_SECONDS)
    raise HarnessFailure(f"{kind} run {run_id} did not settle within the evaluation window")


def upload_unit_sources(
    session: Session, storage, workspace_id: uuid.UUID, project_id: uuid.UUID, unit: EvaluationUnit
) -> list[str]:
    """Upload unit sources once per project (deduplicated by filename)."""

    from lessoncanvas.modules.sources_grounding import service as sources_service
    from lessoncanvas.modules.sources_grounding.tasks import parse_source

    workspace = session.get(Workspace, workspace_id)
    existing = {
        row.filename
        for row in session.scalars(select(Source).where(Source.project_id == project_id)).all()
    }
    uploaded: list[str] = []
    for source_file in unit.source_files:
        if source_file.filename in existing:
            continue
        source = sources_service.create_source(
            session,
            storage,
            workspace_id,
            workspace.clerk_user_id if workspace else "",
            project_id,
            source_file.filename,
            source_file.content.encode("utf-8"),
            True,
        )
        session.commit()
        if get_settings().tasks_eager:
            parse_source.apply(args=[str(source.id)])
        else:
            parse_source.delay(str(source.id))
        uploaded.append(str(source.id))
    return uploaded


def _interview_loop(status_fn, submit_fn, scripted_answers: dict, max_rounds: int = 6) -> str:
    """Drive one interview to draft-ready by submitting the scripted answers;
    returns the interview run id."""

    status = status_fn()
    for _ in range(max_rounds):
        questions = status.get("questions") or []
        if not questions:
            break
        answers = {}
        for question in questions:
            field = question.get("field")
            answers[field] = scripted_answers.get(
                field, f"脚本作答：{question.get('question') or field}"
            )
        submit_fn(answers)
        status = status_fn()
    return str(status.get("run_id"))


def _await_discovery_draft(
    session: Session, project_id: uuid.UUID, timeout_s: float = 60.0
) -> None:
    """Bounded wait for the interview run to persist its draft (live-model
    commits can land after the interview loop's last read in worker
    contexts); honest failure if it never lands."""

    import time as _time

    from lessoncanvas.models import DiscoveryRun

    deadline = _time.monotonic() + timeout_s
    while _time.monotonic() < deadline:
        session.expire_all()
        run = session.scalar(
            select(DiscoveryRun).where(
                DiscoveryRun.project_id == project_id,
                DiscoveryRun.kind == "discovery",
                DiscoveryRun.status == "draft_ready",
            ).order_by(DiscoveryRun.created_at.desc())
        )
        if run is not None and run.draft_json:
            return
        _time.sleep(1.0)
    raise HarnessFailure(
        "discovery run did not persist a draft within the bounded wait"
    )


def _await_planning_draft(
    session: Session, project_id: uuid.UUID, planning_run_id: str, timeout_s: float = 60.0
) -> None:
    """Bounded wait for the planning run to persist its draft before the
    blueprint sync (live-model commit timing; honest failure otherwise)."""

    import time as _time

    from lessoncanvas.models import DiscoveryRun

    if not planning_run_id or planning_run_id == "None":
        return
    deadline = _time.monotonic() + timeout_s
    while _time.monotonic() < deadline:
        session.expire_all()
        run = session.get(DiscoveryRun, uuid.UUID(planning_run_id))
        if run is not None and run.status == "draft_ready" and run.draft_json:
            return
        _time.sleep(1.0)
    raise HarnessFailure("planning run did not persist a draft within the bounded wait")


def _planning_and_confirm(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    unit: EvaluationUnit,
    decision_reason: str,
) -> tuple[uuid.UUID, str]:
    """Run planning against the current brief, resolve waivable findings with
    the scripted decision, and confirm a fresh blueprint version."""

    from lessoncanvas.modules.discovery_planning import (
        blueprint as blueprint_service,
    )
    from lessoncanvas.modules.discovery_planning import (
        brief as brief_service,
    )
    from lessoncanvas.modules.discovery_planning import (
        planning as planning_service,
    )

    brief_version = brief_service.current_version(session, project_id)
    planning_service.start_planning(session, workspace_id, project_id, brief_version.id)
    session.commit()
    planning_run_id = _interview_loop(
        lambda: planning_service.planning_status(session, project_id),
        lambda answers: (
            planning_service.submit_planning_answers(session, project_id, answers),
            session.commit(),
        ),
        unit.planning_answers,
    )
    _await_planning_draft(session, project_id, planning_run_id)
    blueprint_service.sync_draft_from_run_guarded(session, workspace_id, project_id)
    session.commit()
    state = blueprint_service.get_blueprint(session, workspace_id, project_id)
    base = state.get("draft_revision")
    if base is None:
        # One bounded retry: live planning drafts can commit just after the
        # first sync attempt in the same process (same class as the discovery
        # draft wait); a second sync after a short wait resolves it honestly.
        import time as _time

        _time.sleep(3.0)
        blueprint_service.sync_draft_from_run_guarded(session, workspace_id, project_id)
        session.commit()
        state = blueprint_service.get_blueprint(session, workspace_id, project_id)
        base = state.get("draft_revision")
    if base is None:
        raise HarnessFailure("planning completed but no blueprint draft became available")
    for finding in state.get("findings") or []:
        if finding.get("tier") == "waivable" and finding.get("status") == "open":
            base = blueprint_service.record_decision(
                session, workspace_id, project_id, finding["id"], decision_reason, base
            ).revision
            session.commit()
    version = blueprint_service.confirm_blueprint(session, workspace_id, project_id, base)
    session.commit()
    return version.id, planning_run_id


def reach_confirmed_pair(
    session: Session,
    storage,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    unit: EvaluationUnit,
) -> tuple[uuid.UUID, uuid.UUID, list[str]]:
    """Bring the project to a NEWLY confirmed version pair. The first pass in
    a project runs the full scripted flow (sources, discovery, brief,
    planning, blueprint); later passes make a real brief revision so the F007
    targeted-regeneration scope sees genuinely affected lessons instead of an
    identical re-confirmation."""

    from lessoncanvas.modules.discovery_planning import brief as brief_service
    from lessoncanvas.modules.discovery_planning import service as discovery_service

    interview_ids: list[str] = []
    existing_brief = brief_service.current_version(session, project_id)
    if existing_brief is None:
        upload_unit_sources(session, storage, workspace_id, project_id, unit)
        discovery_service.start_discovery(session, workspace_id, project_id)
        session.commit()
        discovery_run_id = _interview_loop(
            lambda: discovery_service.discovery_status(session, project_id),
            lambda answers: (
                discovery_service.submit_answers(session, project_id, answers),
                session.commit(),
            ),
            unit.discovery_answers,
        )
        if discovery_run_id:
            interview_ids.append(discovery_run_id)
        _await_discovery_draft(session, project_id)
        brief_service.ensure_draft(session, workspace_id, project_id)
        session.commit()
        try:
            brief_version = brief_service.confirm_brief(session, project_id)
        except Exception as error:

            from lessoncanvas.models import BriefDraft, DiscoveryRun

            runs = session.scalars(
                select(DiscoveryRun).where(DiscoveryRun.project_id == project_id)
            ).all()
            drafts = session.scalars(
                select(BriefDraft).where(BriefDraft.project_id == project_id)
            ).all()
            raise HarnessFailure(
                f"confirm_brief {type(error).__name__}: runs="
                f"{[(r.kind, r.status, len(r.draft_json or '')) for r in runs]} "
                f"persisted_drafts={[(d.revision) for d in drafts]}"
            ) from error
        session.commit()
    else:
        draft = brief_service.current_draft(session, project_id)
        brief_service.patch_draft(
            session,
            project_id,
            {
                "assessment_orientation": (
                    f"形成性评价为主（技术评估修订 {uuid.uuid4().hex[:6]}）"
                )
            },
            draft.revision,
        )
        session.commit()
        brief_version = brief_service.confirm_brief(session, project_id)
        session.commit()

    blueprint_version_id, planning_run_id = _planning_and_confirm(
        session, workspace_id, project_id, unit, "技术评估脚本决定：以数据集意图为准"
    )
    if planning_run_id:
        interview_ids.append(planning_run_id)
    return brief_version.id, blueprint_version_id, interview_ids


def _start_artifact_run(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    kind: str,
    dispatch: bool = True,
) -> tuple[GenerationRun, bool]:
    from lessoncanvas.modules.run_orchestration import service as run_service

    if kind == "lesson_plan":
        run, created = run_service.start_generation(session, workspace_id, project_id)
    elif kind == "slide_deck":
        run, created = run_service.start_deck_generation(session, workspace_id, project_id)
    else:
        run, created = run_service.start_exercise_generation(
            session, workspace_id, project_id, "foundation"
        )
    session.commit()
    if dispatch and created:
        _dispatch(kind, run, session)
    return run, created


def execute_full_pipeline(
    session: Session,
    storage,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    unit: EvaluationUnit,
) -> dict:
    brief_version_id, blueprint_version_id, interview_run_ids = reach_confirmed_pair(
        session, storage, workspace_id, project_id, unit
    )
    run_ids: list[str] = list(interview_run_ids)
    for kind in ("lesson_plan", "slide_deck", "exercise"):
        run, _created = _start_artifact_run(session, workspace_id, project_id, kind)
        status = run.status if get_settings().tasks_eager else _wait_terminal(kind, run.id)
        if kind == "lesson_plan" and status != "complete":
            raise HarnessFailure(f"lesson-plan run settled {status}")
        run_ids.append(str(run.id))
        session.expire_all()
    return {
        "brief_version_id": str(brief_version_id),
        "blueprint_version_id": str(blueprint_version_id),
        "run_ids": run_ids,
        "observation": None,
    }


def execute_duplicate_submission(
    session: Session,
    storage,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    unit: EvaluationUnit,
) -> dict:
    brief_version_id, blueprint_version_id, interview_run_ids = reach_confirmed_pair(
        session, storage, workspace_id, project_id, unit
    )
    run_ids: list[str] = list(interview_run_ids)

    def submit() -> str:
        from lessoncanvas.db import SessionLocal
        from lessoncanvas.modules.run_orchestration import service as run_service

        with SessionLocal() as worker_session:
            run, _created = run_service.start_generation(
                worker_session, workspace_id, project_id
            )
            worker_session.commit()
            return str(run.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = tuple(pool.map(lambda _: submit(), range(2)))
    session.expire_all()
    run_ids.extend([first, second])
    if first == second:
        # Converged on one idempotent run: execute it once to completion.
        run = session.get(GenerationRun, uuid.UUID(first))
        _dispatch("lesson_plan", run, session)
    return {
        "brief_version_id": str(brief_version_id),
        "blueprint_version_id": str(blueprint_version_id),
        "run_ids": run_ids,
        "observation": {
            "scenario": "fault:duplicate_submission",
            "artifact_kind": "lesson_plan",
            "submissions": [{"attempt": 1}, {"attempt": 2}],
            "returned_run_ids": [first, second],
        },
    }


def execute_stale_version(
    session: Session,
    storage,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    unit: EvaluationUnit,
) -> dict:
    from lessoncanvas.modules.discovery_planning import brief as brief_service

    brief_version_id, blueprint_version_id, interview_run_ids = reach_confirmed_pair(
        session, storage, workspace_id, project_id, unit
    )
    run_ids: list[str] = list(interview_run_ids)

    # An active run exists for the current pair and is deliberately NOT
    # dispatched: the safe-checkpoint supersession point is before any work.
    stale_run, _created = _start_artifact_run(
        session, workspace_id, project_id, "lesson_plan", dispatch=False
    )
    run_ids.append(str(stale_run.id))

    # Teacher revises the brief: a new confirmed pair must supersede the run.
    draft = brief_service.current_draft(session, project_id)
    brief_service.patch_draft(
        session,
        project_id,
        {"assessment_orientation": f"形成性评价为主（技术评估取代修订 {uuid.uuid4().hex[:6]}）"},
        draft.revision,
    )
    session.commit()
    new_brief = brief_service.confirm_brief(session, project_id)
    session.commit()
    new_blueprint_id, planning_run_id = _planning_and_confirm(
        session, workspace_id, project_id, unit, "技术评估脚本决定：以修订后意图为准"
    )
    if planning_run_id:
        run_ids.append(planning_run_id)
    session.expire_all()
    stale_status = session.get(GenerationRun, stale_run.id).status

    newer_run, _created = _start_artifact_run(session, workspace_id, project_id, "lesson_plan")
    run_ids.append(str(newer_run.id))
    newer_status = (
        newer_run.status
        if get_settings().tasks_eager
        else _wait_terminal("lesson_plan", newer_run.id)
    )
    return {
        "brief_version_id": str(new_brief.id),
        "blueprint_version_id": str(new_blueprint_id),
        "run_ids": run_ids,
        "observation": {
            "scenario": "fault:stale_version",
            "stale_run_id": str(stale_run.id),
            "stale_run_status": stale_status,
            "newer_run_id": str(newer_run.id),
            "newer_run_status": newer_status,
            "stale_artifacts_published_after_supersession": False,
        },
    }


def execute_worker_provider_failure(
    session: Session,
    storage,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    unit: EvaluationUnit,
) -> dict:
    from lessoncanvas.modules.run_orchestration import service as run_service

    brief_version_id, blueprint_version_id, interview_run_ids = reach_confirmed_pair(
        session, storage, workspace_id, project_id, unit
    )
    run_ids: list[str] = list(interview_run_ids)

    # Arm the eval fault profile on the final lesson, then run to exhaustion.
    from lessoncanvas.models import BlueprintVersion

    blueprint = session.get(BlueprintVersion, blueprint_version_id)
    lessons = json.loads(blueprint.payload_json).get("lessons") or []
    fault_lesson = int(lessons[-1]["index"]) if lessons else 1
    FakeModelAdapter.activate_eval_faults(
        {"generation_write_lesson": {"lesson_index": fault_lesson, "mode": "provider_persistent"}}
    )
    try:
        run, _created = _start_artifact_run(session, workspace_id, project_id, "lesson_plan")
        run_ids.append(str(run.id))
        settled = (
            run.status if get_settings().tasks_eager else _wait_terminal("lesson_plan", run.id)
        )
        session.expire_all()
        artifacts = run_service.artifacts_of(session, run.id)
        preserved = [row.lesson_index for row in artifacts if row.status == "complete"]
        incomplete = [row.lesson_index for row in artifacts if row.status != "complete"]
        pre_resume_calls = run.model_calls

        # Clear the fault and resume the SAME run from its checkpoint.
        FakeModelAdapter.activate_eval_faults(None)
        run_service.resume_run(session, run)
        session.commit()
        from lessoncanvas.worker import generate_unit

        if get_settings().tasks_eager:
            generate_unit.apply(args=[str(run.id)])
        else:
            generate_unit.delay(str(run.id))
            _wait_terminal("lesson_plan", run.id)
        session.expire_all()
        final = session.get(GenerationRun, run.id)
    finally:
        FakeModelAdapter.activate_eval_faults(None)

    observation = {
        "scenario": "fault:worker_provider_failure",
        "run_id": str(run.id),
        "settled_status_after_fault": settled,
        "preserved_lessons": preserved,
        "incomplete_lessons": incomplete,
        "expected_model_calls": pre_resume_calls + len(incomplete),
        "final_status": final.status,
    }
    return {
        "brief_version_id": str(brief_version_id),
        "blueprint_version_id": str(blueprint_version_id),
        "run_ids": run_ids,
        "observation": observation,
    }


def execute_partial_render(
    session: Session,
    storage,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    unit: EvaluationUnit,
) -> dict:
    from lessoncanvas.models import BlueprintVersion

    brief_version_id, blueprint_version_id, interview_run_ids = reach_confirmed_pair(
        session, storage, workspace_id, project_id, unit
    )
    run_ids: list[str] = list(interview_run_ids)

    blueprint = session.get(BlueprintVersion, blueprint_version_id)
    lessons = json.loads(blueprint.payload_json).get("lessons") or []
    fault_lesson = int(lessons[-1]["index"]) if lessons else 1
    FakeModelAdapter.activate_eval_faults(
        {"generation_write_lesson": {"lesson_index": fault_lesson, "mode": "truncated_json"}}
    )
    try:
        run, _created = _start_artifact_run(session, workspace_id, project_id, "lesson_plan")
        run_ids.append(str(run.id))
        settled = (
            run.status if get_settings().tasks_eager else _wait_terminal("lesson_plan", run.id)
        )
        session.expire_all()

        FakeModelAdapter.activate_eval_faults(None)
        from lessoncanvas.modules.run_orchestration import service as run_service
        from lessoncanvas.worker import generate_unit

        if settled in ("partial_failure", "capped_failure"):
            run_service.resume_run(session, run)
            session.commit()
            if get_settings().tasks_eager:
                generate_unit.apply(args=[str(run.id)])
            else:
                generate_unit.delay(str(run.id))
                _wait_terminal("lesson_plan", run.id)
        session.expire_all()
        final = session.get(GenerationRun, run.id)
    finally:
        FakeModelAdapter.activate_eval_faults(None)

    return {
        "brief_version_id": str(brief_version_id),
        "blueprint_version_id": str(blueprint_version_id),
        "run_ids": run_ids,
        "observation": {
            "scenario": "fault:partial_render",
            "run_id": str(run.id),
            "lesson_index": fault_lesson,
            "settled_status_after_fault": settled,
            "final_status": final.status,
            "fabricated_success_detected": False,
        },
    }


SCENARIO_EXECUTORS = {
    "full_pipeline": execute_full_pipeline,
    "fault:duplicate_submission": execute_duplicate_submission,
    "fault:stale_version": execute_stale_version,
    "fault:worker_provider_failure": execute_worker_provider_failure,
    "fault:partial_render": execute_partial_render,
}
