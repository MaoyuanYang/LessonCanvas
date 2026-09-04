"""F016 T3 (TS-009..TS-013): the quality-review specialist in all families.

Deterministic stack: fake adapter scripts review outcomes by lesson-title
markers (REVIEW_SEVERE / REVIEW_SEVERE_TWICE / REVIEW_MINOR /
REVIEW_PARSE_FAIL) and by the eval fault modes. Two-lesson units keep the
revise paths inside the pre-T4 flat cap.
"""

import json
import uuid

from sqlalchemy import select

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import GenerationRun, MemoryRecord, Project, TraceEvent
from lessoncanvas.modules.artifact_production.deck_graph import execute_deck_generation
from lessoncanvas.modules.artifact_production.exercise_graph import (
    execute_exercise_generation,
)
from lessoncanvas.modules.artifact_production.graph import execute_generation
from lessoncanvas.modules.run_orchestration import service as run_service

CORPUS_TEMPLATE = "\n".join(
    [
        "单元主题：{theme}",
        "课时数：{lesson_count}",
        "学情：高二学生，英语中等水平",
        "教学目标：提升阅读与表达能力",
        "教材定位：外研社必修一 Unit 3",
        "输出语言：中英双语",
        "评估倾向：形成性评价为主",
        "课时分配：共{periods}课时，每课2课时，评估聚焦综合输出",
    ]
)


def confirmed_blueprint_project(
    client, auth, *, lesson_count: int = 2, theme_marker: str | None = None
) -> str:
    theme = (
        f"{theme_marker} 环境保护与可持续发展"
        if theme_marker
        else "环境保护与可持续发展"
    )
    corpus = CORPUS_TEMPLATE.format(
        theme=theme, lesson_count=lesson_count, periods=lesson_count * 2
    )
    response = client.post("/projects", json={"name": "评审阶段测试"}, headers=auth)
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


def complete_plans(client, auth, db_session, project_id) -> GenerationRun:
    workspace_id = _workspace_id(db_session, project_id)
    run, _ = run_service.start_generation(db_session, workspace_id, uuid.UUID(project_id))
    db_session.commit()
    execute_generation(str(run.id))
    session = SessionLocal()
    try:
        return session.get(GenerationRun, run.id)
    finally:
        session.close()


def _workspace_id(db_session, project_id):
    return db_session.get(Project, uuid.UUID(project_id)).workspace_id


def _events(run_id) -> list[TraceEvent]:
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


def _artifacts(run_id, family="plans"):
    session = SessionLocal()
    try:
        fetch = {
            "plans": run_service.artifacts_of,
            "deck": run_service.deck_artifacts_of,
            "exercises": run_service.exercise_artifacts_of,
        }[family]
        return fetch(session, run_id)
    finally:
        session.close()


def _of_kind(events, prefix: str) -> list[TraceEvent]:
    return [e for e in events if e.event_type.startswith(prefix)]


# TS-009: review pass, incl. minor-only


def test_clean_review_passes_with_zero_findings(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth)
    run = complete_plans(client, auth, db_session, project_id)
    assert run.status == "complete"
    events = _events(run.id)
    assert len(_of_kind(events, "model.generation_review_lesson")) == 2
    assert _of_kind(events, "model.generation_revise_lesson") == []
    for artifact in _artifacts(run.id):
        assert artifact.review_rounds == 1
        assert artifact.review_outcome == "passed"
        assert json.loads(artifact.review_findings_json) == []
        assert artifact.status == "complete"


def test_minor_only_findings_pass_with_disclosure(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, theme_marker="REVIEW_MINOR")
    run = complete_plans(client, auth, db_session, project_id)
    assert run.status == "complete", "minor findings must never block"
    events = _events(run.id)
    assert _of_kind(events, "model.generation_revise_lesson") == []
    for artifact in _artifacts(run.id):
        findings = json.loads(artifact.review_findings_json)
        assert findings and findings[0]["severity"] == "minor"
        assert artifact.review_outcome == "passed"
        assert artifact.review_rounds == 1
        assert artifact.status == "complete"
    review_event = _of_kind(events, "model.generation_review_lesson")[0]
    payload = json.loads(review_event.payload_json)
    assert payload["minor_count"] >= 1 and payload["severe_count"] == 0


# TS-010: severe findings -> one revise round -> re-review passes


def test_severe_findings_trigger_single_revise_then_pass(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, theme_marker="REVIEW_SEVERE")
    run = complete_plans(client, auth, db_session, project_id)
    assert run.status == "complete"

    events = _events(run.id)
    reviews = _of_kind(events, "model.generation_review_lesson")
    revises = _of_kind(events, "model.generation_revise_lesson")
    assert len(reviews) == 4, "two rounds per lesson"
    assert len(revises) == 2, "exactly one revise round per lesson"
    rounds = [json.loads(e.payload_json)["round"] for e in reviews]
    assert sorted(rounds) == [1, 1, 2, 2]
    assert revises[0].event_type == "model.generation_revise_lesson"
    revise_payload = json.loads(revises[0].payload_json)["prompt"]
    assert revise_payload["findings"][0]["severity"] == "severe"

    for artifact in _artifacts(run.id):
        assert artifact.review_outcome == "passed_after_revise"
        assert artifact.review_rounds == 2
        assert artifact.status == "complete"
    # design + write + review + revise + re-review per lesson = 5 x 2
    assert run.model_calls == 10
    # Review never modifies confirmed intent: the run stays bound to the same
    # versions that were current at its start.
    assert (
        run.brief_version_id
        == run_service.current_brief_version(db_session, run.project_id).id
    )
    assert (
        run.blueprint_version_id
        == run_service.current_blueprint_version(db_session, run.project_id).id
    )


# TS-011: severe findings twice -> failed-after-revise


def test_failed_after_revise_names_review_stage(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, theme_marker="REVIEW_SEVERE_TWICE")
    run = complete_plans(client, auth, db_session, project_id)
    assert run.status == "terminal_failure"

    events = _events(run.id)
    assert len(_of_kind(events, "model.generation_review_lesson")) == 4
    assert len(_of_kind(events, "model.generation_revise_lesson")) == 2, "no third round"
    # No rendering of rejected drafts.
    assert _of_kind(events, "tool.render_lesson_plan_docx") == []

    for artifact in _artifacts(run.id):
        assert artifact.status == "failed"
        assert "review stage" in artifact.failure_reason
        assert artifact.review_outcome == "failed_after_revise"
        assert artifact.review_rounds == 2
        findings = json.loads(artifact.review_findings_json)
        assert findings and findings[0]["severity"] == "severe", "latest round kept"


# TS-012: decks and exercises gain review with unchanged writer contracts


def test_decks_gain_review_with_unchanged_writer_contract(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, lesson_count=2)
    complete_plans(client, auth, db_session, project_id)
    run, _ = run_service.start_deck_generation(
        db_session, _workspace_id(db_session, project_id), uuid.UUID(project_id)
    )
    db_session.commit()
    execute_deck_generation(str(run.id))
    session = SessionLocal()
    try:
        run = session.get(GenerationRun, run.id)
        assert run.status == "complete"
    finally:
        session.close()

    events = _events(run.id)
    reviews = _of_kind(events, "model.generation_review_deck")
    assert len(reviews) == 2
    write_payload = json.loads(
        _of_kind(events, "model.generation_write_deck")[0].payload_json
    )["prompt"]
    assert "design" not in write_payload, "deck writer inputs are unchanged (D2)"
    for artifact in _artifacts(run.id, "deck"):
        assert artifact.review_outcome == "passed"
        assert artifact.status == "complete"


def test_exercises_gain_review_with_memory_context(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, lesson_count=2)
    complete_plans(client, auth, db_session, project_id)
    db_session.add(
        MemoryRecord(
            workspace_id=_workspace_id(db_session, project_id),
            category="assessment_style",
            content="练习偏好包含一道阅读理解题",
            content_hash="hash-review-test-1",
        )
    )
    db_session.commit()
    run, _ = run_service.start_exercise_generation(
        db_session,
        _workspace_id(db_session, project_id),
        uuid.UUID(project_id),
        "consolidation",
    )
    db_session.commit()
    execute_exercise_generation(str(run.id))
    session = SessionLocal()
    try:
        run = session.get(GenerationRun, run.id)
        assert run.status == "complete"
    finally:
        session.close()

    events = _events(run.id)
    reviews = _of_kind(events, "model.generation_review_exercises")
    assert len(reviews) == 2
    review_payload = json.loads(reviews[0].payload_json)["prompt"]
    assert review_payload.get("memory_context"), "reviewer receives budgeted memory (D6)"
    assert review_payload["dimensions"] == [
        "plan_coverage",
        "grounding",
        "consistency",
    ]
    write_payload = json.loads(
        _of_kind(events, "model.generation_write_exercises")[0].payload_json
    )["prompt"]
    assert "design" not in write_payload, "exercise writer inputs are unchanged (D2)"
    for artifact in _artifacts(run.id, "exercises"):
        assert artifact.review_outcome == "passed"


def test_deck_severe_findings_revise_path(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, lesson_count=2)
    _patch_lesson_titles(client, auth, project_id, {1: "第1课 REVIEW_SEVERE 阅读"})
    complete_plans(client, auth, db_session, project_id)
    run, _ = run_service.start_deck_generation(
        db_session, _workspace_id(db_session, project_id), uuid.UUID(project_id)
    )
    db_session.commit()
    execute_deck_generation(str(run.id))
    session = SessionLocal()
    try:
        run = session.get(GenerationRun, run.id)
        assert run.status == "complete"
    finally:
        session.close()

    events = _events(run.id)
    assert len(_of_kind(events, "model.generation_review_deck")) == 3, "2 + 1 re-review"
    assert len(_of_kind(events, "model.generation_revise_deck")) == 1
    artifacts = _artifacts(run.id, "deck")
    outcomes = {a.lesson_index: a.review_outcome for a in artifacts}
    assert outcomes[1] == "passed_after_revise"
    assert outcomes[2] == "passed"


# TS-013: unparseable review output + no-bypass of deterministic validation


def test_unparseable_review_output_never_silently_passes(client, auth, db_session):
    project_id = confirmed_blueprint_project(client, auth, theme_marker="REVIEW_PARSE_FAIL")
    run = complete_plans(client, auth, db_session, project_id)
    assert run.status == "terminal_failure"

    events = _events(run.id)
    reviews = _of_kind(events, "model.generation_review_lesson")
    assert reviews, "review attempts are traced"
    assert all(json.loads(e.payload_json)["parse_failed"] for e in reviews)
    assert _of_kind(events, "tool.render_lesson_plan_docx") == []
    for artifact in _artifacts(run.id):
        assert artifact.status == "failed"
        assert "review" in artifact.failure_reason or "unparseable" in artifact.failure_reason


def test_review_pass_never_bypasses_structural_validation(client, auth, db_session):
    # DECK_TOO_LONG decks pass review but fail the structural validator: the
    # deterministic gate stays mandatory after any review outcome.
    project_id = confirmed_blueprint_project(client, auth, lesson_count=2)
    _patch_lesson_titles(client, auth, project_id, {1: "第1课 DECK_TOO_LONG 阅读"})
    complete_plans(client, auth, db_session, project_id)
    run, _ = run_service.start_deck_generation(
        db_session, _workspace_id(db_session, project_id), uuid.UUID(project_id)
    )
    db_session.commit()
    execute_deck_generation(str(run.id))
    session = SessionLocal()
    try:
        run = session.get(GenerationRun, run.id)
        assert run.status == "partial_failure"
    finally:
        session.close()

    events = _events(run.id)
    assert _of_kind(events, "model.generation_review_deck"), "review ran first"
    artifacts = _artifacts(run.id, "deck")
    assert artifacts[0].status == "failed"
    assert artifacts[0].review_outcome == "passed", "review passed, structure still failed it"
    assert artifacts[1].status == "complete"


def _patch_lesson_titles(client, auth, project_id, title_overrides: dict[int, str]) -> None:
    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    lessons = []
    for lesson in state["draft"]["lessons"]:
        index = lesson["index"]
        lessons.append(
            {
                "index": index,
                "title": title_overrides.get(index, lesson.get("title")),
                "objective_ids": lesson.get("objective_ids") or [],
                "assessment_intent": lesson.get("assessment_intent"),
                "period_count": lesson.get("period_count"),
            }
        )
    patched = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={
            "payload": {"unit": state["draft"]["unit"], "lessons": lessons},
            "base_revision": state["draft_revision"],
        },
        headers=auth,
    )
    assert patched.status_code == 200, patched.text
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": patched.json()["draft_revision"]},
        headers=auth,
    )
    assert confirmed.status_code == 200, confirmed.text
