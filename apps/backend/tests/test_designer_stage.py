"""F016 T2 (TS-006..TS-008): the activity-design specialist in the plans path.

Deterministic stack (fake adapter scripts designs by lesson-title markers and
eval faults); live design quality is evidenced at delivery (TS-022).
"""

import json
import uuid

import pytest
from sqlalchemy import select

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import GenerationRun, MemoryRecord, Project, TraceEvent
from lessoncanvas.modules.artifact_production.graph import execute_generation
from lessoncanvas.modules.run_orchestration import service as run_service

CORPUS = "\n".join(
    [
        "单元主题：环境保护与可持续发展",
        "课时数：6",
        "学情：高二学生，英语中等水平",
        "教学目标：提升阅读与表达能力",
        "教材定位：外研社必修一 Unit 3",
        "输出语言：中英双语",
        "评估倾向：形成性评价为主",
        "课时分配：共12课时，每课2课时，评估聚焦综合输出",
    ]
)


def confirmed_blueprint_project(client, auth, theme_marker: str | None = None) -> str:
    """Same flow as tests.test_generation.confirmed_blueprint_project with an
    optional marker riding the unit theme into every lesson title."""

    corpus = CORPUS
    if theme_marker:
        corpus = corpus.replace(
            "单元主题：环境保护与可持续发展",
            f"单元主题：{theme_marker} 环境保护与可持续发展",
        )
    response = client.post("/projects", json={"name": "设计阶段测试"}, headers=auth)
    assert response.status_code == 201
    project_id = response.json()["id"]
    upload = client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", corpus.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    )
    assert upload.status_code == 201, upload.text
    assert client.post(f"/projects/{project_id}/discovery/start", headers=auth).status_code == 200
    assert (
        client.post(f"/projects/{project_id}/brief/confirm", headers=auth).status_code == 200
    )
    assert client.post(f"/projects/{project_id}/planning/start", headers=auth).status_code == 200
    blueprint = client.get(f"/projects/{project_id}/blueprint", headers=auth)
    assert blueprint.status_code == 200
    state = blueprint.json()
    base = state["draft_revision"]
    for finding in state.get("findings", []):
        if finding.get("tier") == "waivable" and finding.get("status") == "open":
            decision = client.post(
                f"/projects/{project_id}/blueprint/decisions",
                json={
                    "finding_id": finding["id"],
                    "reason": "以教材与教师判断为准",
                    "base_revision": base,
                },
                headers=auth,
            )
            assert decision.status_code == 200, decision.text
            base = decision.json()["draft_revision"]
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": base},
        headers=auth,
    )
    assert confirmed.status_code == 200, confirmed.text
    return project_id


def _start_and_execute(db_session, project_id, auth=None) -> GenerationRun:
    project = db_session.get(Project, uuid.UUID(project_id))
    run, _ = run_service.start_generation(db_session, project.workspace_id, project.id)
    db_session.commit()
    execute_generation(str(run.id))
    session = SessionLocal()
    try:
        return session.get(GenerationRun, run.id)
    finally:
        session.close()


def _trace_events(run_id) -> list[TraceEvent]:
    session = SessionLocal()
    try:
        return list(
            session.scalars(
                select(TraceEvent)
                .where(TraceEvent.run_id == run_id)
                .order_by(TraceEvent.created_at, TraceEvent.id)
            ).all()
        )
    finally:
        session.close()


def _artifacts(run_id):
    session = SessionLocal()
    try:
        return run_service.artifacts_of(session, run_id)
    finally:
        session.close()


# TS-006: designer stage contract


def test_plans_run_executes_design_then_write_per_lesson(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth)
    run = _start_and_execute(db_session, project_id)
    assert run.status == "complete", run.failure_json

    events = _trace_events(run.id)
    design_events = [e for e in events if e.event_type == "model.generation_design_lesson"]
    write_events = [e for e in events if e.event_type == "model.generation_write_lesson"]
    review_events = [e for e in events if e.event_type == "model.generation_review_lesson"]
    artifacts = _artifacts(run.id)
    assert len(artifacts) == 6
    assert len(design_events) == 6, "one design call per lesson"
    assert len(write_events) == 6
    assert len(review_events) == 6, "one clean review round per lesson"

    for artifact in artifacts:
        assert artifact.status == "complete"
        assert artifact.design_status == "ready"
        design = json.loads(artifact.design_json)
        assert design["objective_ids"], "design binds to blueprint objectives"
        assert len(design["activities"]) >= 3

    # Stage order and per-stage attribution: each design event precedes its
    # lesson's write event and carries latency and a model label.
    lesson_orders: dict[int, list[str]] = {}
    for event in events:
        if event.event_type not in (
            "model.generation_design_lesson",
            "model.generation_write_lesson",
            "model.generation_review_lesson",
        ):
            continue
        prompt = json.loads(event.payload_json)["prompt"]
        index = prompt["lesson"]["lesson_index"]
        lesson_orders.setdefault(index, []).append(event.event_type)
    for index, order in lesson_orders.items():
        assert order == [
            "model.generation_design_lesson",
            "model.generation_write_lesson",
            "model.generation_review_lesson",
        ], f"lesson {index} stage order violated"
    for event in design_events + write_events:
        assert event.latency_ms is not None
        assert event.model

    # The writer demonstrably consumes the design (labeled payload field).
    first_write = json.loads(write_events[0].payload_json)["prompt"]
    assert first_write.get("design", {}).get("activities")

    # Accounting: design+write+review per lesson = 18 model calls, all reserved.
    assert run.model_calls == 18


# TS-007: design validation failure paths


def test_invalid_design_retries_once_then_honest_stage_failure(client, auth, db_session):
    # The marker rides the unit theme into every lesson title: every design
    # references a bogus objective id twice, so all lessons fail the stage.
    project_id = confirmed_blueprint_project(client, auth, theme_marker="DESIGN_INVALID")
    run = _start_and_execute(db_session, project_id)
    assert run.status == "terminal_failure"

    events = _trace_events(run.id)
    design_events = [e for e in events if e.event_type == "model.generation_design_lesson"]
    write_events = [e for e in events if e.event_type == "model.generation_write_lesson"]
    assert len(design_events) == 12, "one corrective retry per lesson (6 x 2)"
    assert write_events == [], "no drafting after a failed design stage"
    for event in design_events:
        payload = json.loads(event.payload_json)
        assert payload["validation_problems"]

    artifacts = _artifacts(run.id)
    assert {artifact.status for artifact in artifacts} == {"failed"}
    assert all("design stage failed" in (artifact.failure_reason or "") for artifact in artifacts)


def test_single_lesson_design_fault_preserves_completed_lessons(
    client, auth, db_session, monkeypatch
):
    from lessoncanvas.adapters.model import FakeModelAdapter
    from lessoncanvas.settings import get_settings

    project_id = confirmed_blueprint_project(client, auth)
    monkeypatch.setattr(get_settings(), "eval_fault_profile", "enabled", raising=False)
    FakeModelAdapter.activate_eval_faults(
        {"generation_design_lesson": {"lesson_index": 2, "mode": "design_invalid"}}
    )
    try:
        run = _start_and_execute(db_session, project_id)
    finally:
        FakeModelAdapter.activate_eval_faults(None)

    assert run.status == "partial_failure"
    artifacts = _artifacts(run.id)
    failed = [a for a in artifacts if a.status == "failed"]
    assert [a.lesson_index for a in failed] == [2]
    assert "design stage failed" in failed[0].failure_reason
    assert sum(1 for a in artifacts if a.status == "complete") == 5


# TS-008: memory injection + untrusted discipline


@pytest.fixture()
def confirmed_memory(db_session, client, auth):
    def _install(project_id: str) -> None:
        project = db_session.get(Project, uuid.UUID(project_id))
        db_session.add(
            MemoryRecord(
                workspace_id=project.workspace_id,
                category="pacing_preference",
                content="偏好每课包含一个 15 分钟的输出活动环节",
                content_hash="hash-designer-test-1",
            )
        )
        db_session.commit()

    return _install


def test_designer_receives_budgeted_memory_context(client, auth, db_session, confirmed_memory):
    project_id = confirmed_blueprint_project(client, auth)
    confirmed_memory(project_id)
    run = _start_and_execute(db_session, project_id)
    assert run.status == "complete"
    events = _trace_events(run.id)
    design_event = next(
        e for e in events if e.event_type == "model.generation_design_lesson"
    )
    prompt = json.loads(design_event.payload_json)["prompt"]
    assert any(
        "输出活动" in json.dumps(item, ensure_ascii=False)
        for item in prompt.get("memory_context", [])
    ), "designer payload must carry the confirmed memory as labeled context"


def test_injected_design_content_stays_inert_labeled_data(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, theme_marker="DESIGN_INJECT")
    run = _start_and_execute(db_session, project_id)
    assert run.status == "complete"

    artifacts = _artifacts(run.id)
    design = json.loads(artifacts[0].design_json)
    assert any(
        "IGNORE ALL PREVIOUS INSTRUCTIONS" in a["description"] for a in design["activities"]
    ), "hostile design text is stored verbatim (untrusted input kept inspectable)"

    events = _trace_events(run.id)
    write_event = next(
        e for e in events if e.event_type == "model.generation_write_lesson"
    )
    prompt = json.loads(write_event.payload_json)["prompt"]
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in json.dumps(
        prompt.get("design", {}), ensure_ascii=False
    ), "the writer sees the design only as labeled JSON user payload"

    from lessoncanvas.modules.artifact_production.design import DESIGNER_SYSTEM

    assert "IGNORE" not in DESIGNER_SYSTEM
    assert all(artifact.status == "complete" for artifact in artifacts)
