"""F009 technical evaluation: criteria-engine honesty (TS-002/003/010),
idempotent creation (TS-004), deterministic full pipeline (TS-005), fault
scenarios (TS-006..TS-009), report contract (TS-012), and authorization
non-disclosure (TS-013)."""

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from lessoncanvas.adapters.model import FakeModelAdapter, ModelProviderError
from lessoncanvas.models import (
    GenerationRun,
    TechnicalEvaluation,
    TraceEvent,
)
from lessoncanvas.modules.technical_evaluation import criteria, service
from lessoncanvas.modules.technical_evaluation.criteria import CriterionResult
from lessoncanvas.settings import get_settings


def _create_project(client, auth) -> str:
    return client.post("/projects", json={"name": "技术评估"}, headers=auth).json()["id"]


def _create_pass(
    client, auth, project_id, scenario="full_pipeline", mode="deterministic", pass_index=1
):
    response = client.post(
        f"/projects/{project_id}/technical-evaluation/runs",
        json={
            "unit_key": "travelling-around",
            "pass_index": pass_index,
            "mode": mode,
            "scenario": scenario,
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# TS-002 / TS-003 / TS-010 (engine level)
# ---------------------------------------------------------------------------


def test_engine_deterministic_classification_and_judge_boundary(db_session):
    results = [
        CriterionResult("C-MEM-1", criteria.BLOCKING, "pass", None, {}),
        CriterionResult("M-JUDGE", criteria.DIAGNOSTIC, None, {"opinion": "looks fine"}, {}),
    ]
    assert criteria.overall_outcome(results) == "pass"
    # A model-judge opinion never participates in the overall outcome.
    results.append(CriterionResult("M-JUDGE", criteria.DIAGNOSTIC, None, {"opinion": "pass"}, {}))
    assert criteria.overall_outcome(results) == "pass"
    # Any failed blocking criterion fails the pass even with every diagnostic present.
    results[0] = CriterionResult("C-MEM-1", criteria.BLOCKING, "fail", None, {})
    assert criteria.overall_outcome(results) == "fail"
    # Missing evidence never counts as pass.
    results[0] = CriterionResult("C-MEM-1", criteria.BLOCKING, "missing_evidence", None, {})
    assert criteria.overall_outcome(results) == "missing_evidence"
    # Identical inputs yield identical outcomes (pure function over results).
    assert criteria.overall_outcome(results) == criteria.overall_outcome(results)


def test_engine_missing_evidence_never_zeroes_cost(db_session):
    # A cost metric with no recorded usage surfaces nulls and missing counts,
    # never a fabricated zero cost (TS-003 honesty).
    evaluation = TechnicalEvaluation(
        project_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_revision="eval-datasets-r1",
        unit_key="travelling-around",
        pass_index=1,
        mode="deterministic",
        scenario="full_pipeline",
        model_config_json="{}",
        memory_state_json=service.MEMORY_STATE_EMPTY_JSON,
        created_by="teacher_a",
        run_ids_json=json.dumps([str(uuid.uuid4())]),
    )
    trace_run_id = uuid.UUID(json.loads(evaluation.run_ids_json)[0])
    db_session.add(
        TraceEvent(
            run_id=trace_run_id,
            event_type="model.narration",
            prompt_tokens=None,
            completion_tokens=None,
            cost_usd=None,
            payload_json="{}",
        )
    )
    db_session.commit()

    measured = criteria.measure_cost(db_session, evaluation)
    assert measured.measured is not None
    assert measured.measured["estimated_cost_usd"] is None
    assert measured.measured["narration_events_missing_usage"] == 1


def test_engine_memory_pinning_evaluates_recording_itself(db_session):
    recorded = TechnicalEvaluation(memory_state_json=service.MEMORY_STATE_EMPTY_JSON)
    assert criteria.evaluate_memory_pinning(recorded).outcome == "pass"
    unrecorded = TechnicalEvaluation(memory_state_json="{}")
    assert criteria.evaluate_memory_pinning(unrecorded).outcome == "fail"


# ---------------------------------------------------------------------------
# TS-004: idempotent creation
# ---------------------------------------------------------------------------


def test_evaluation_create_is_idempotent_single_execution(client, auth, db_session):
    project_id = _create_project(client, auth)

    first = _create_pass(client, auth, project_id)
    assert first["created"] is True
    assert first["evaluation"]["status"] == "completed"

    model_calls_before = len(
        db_session.scalars(select(TraceEvent.id).where(TraceEvent.event_type.startswith("model."))).all()
    )
    duplicate = _create_pass(client, auth, project_id)
    assert duplicate["created"] is False
    assert duplicate["evaluation"]["evaluation_id"] == first["evaluation"]["evaluation_id"]
    model_calls_after = len(
        db_session.scalars(select(TraceEvent.id).where(TraceEvent.event_type.startswith("model."))).all()
    )
    assert model_calls_after == model_calls_before  # no second pipeline execution

    concurrent = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(
            lambda _: client.post(
                f"/projects/{project_id}/technical-evaluation/runs",
                json={
                    "unit_key": "natural-disasters",
                    "pass_index": 2,
                    "mode": "deterministic",
                    "scenario": "full_pipeline",
                },
                headers=auth,
            ),
            range(2),
        ):
            concurrent.append(result.json()["evaluation"]["evaluation_id"])
    assert concurrent[0] == concurrent[1]
    from sqlalchemy import func

    assert (
        db_session.scalar(
            select(func.count(TechnicalEvaluation.id)).where(
                TechnicalEvaluation.project_id == uuid.UUID(project_id),
                TechnicalEvaluation.unit_key == "natural-disasters",
            )
        )
        == 1
    )


# ---------------------------------------------------------------------------
# TS-005: deterministic full pipeline with complete binding
# ---------------------------------------------------------------------------


def test_full_pipeline_binds_versions_runs_artifacts_config_memory(client, auth, db_session):
    project_id = _create_project(client, auth)
    payload = _create_pass(client, auth, project_id)
    evaluation = payload["evaluation"]

    assert evaluation["status"] == "completed"
    assert evaluation["overall_outcome"] in ("pass", "missing_evidence", "fail")
    assert evaluation["memory_state"]["memory_state"] == criteria.MEMORY_STATE_EMPTY
    assert evaluation["brief_version_id"] and evaluation["blueprint_version_id"]

    outcomes = {item["criterion_key"]: item for item in evaluation["criteria"]}
    expected_keys = {"C-TRACE-1", "C-GROUND-1", "C-ART-1", "C-MEM-1", "M-LAT", "M-COST", "M-COVER"}
    assert set(outcomes) >= expected_keys
    assert outcomes["C-TRACE-1"]["outcome"] == "pass"
    assert outcomes["C-GROUND-1"]["outcome"] == "pass"
    assert outcomes["C-ART-1"]["outcome"] == "pass"
    assert outcomes["C-MEM-1"]["outcome"] == "pass"
    for diagnostic in ("M-LAT", "M-COST", "M-COVER"):
        assert outcomes[diagnostic]["classification"] == "diagnostic"
        assert outcomes[diagnostic]["outcome"] is None

    run_ids = _evaluation_run_ids(db_session, evaluation["evaluation_id"])
    assert len(run_ids) >= 5  # discovery + planning + three artifact runs
    for run_id in run_ids:
        assert db_session.get(GenerationRun, run_id) is not None or _is_interview_run(
            db_session, run_id
        )


def _evaluation_run_ids(db_session, evaluation_id):
    row = db_session.get(TechnicalEvaluation, uuid.UUID(evaluation_id))
    return [uuid.UUID(value) for value in json.loads(row.run_ids_json)]


def _is_interview_run(db_session, run_id):
    from lessoncanvas.models import DiscoveryRun

    return db_session.get(DiscoveryRun, run_id) is not None


# ---------------------------------------------------------------------------
# TS-006: provider/worker failure recovery
# ---------------------------------------------------------------------------


def test_fault_recovery_resumes_same_run_no_duplicate_billing(
    client, auth, db_session, monkeypatch
):
    monkeypatch.setattr(get_settings(), "eval_fault_profile", "enabled", raising=False)
    project_id = _create_project(client, auth)
    payload = _create_pass(
        client, auth, project_id, scenario="fault:worker_provider_failure"
    )
    evaluation = payload["evaluation"]

    assert evaluation["status"] == "completed"
    outcome = _criterion(evaluation, "C-RECOV-1")
    assert outcome["outcome"] == "pass"
    observation = outcome["evidence"]["observation"]
    assert observation["preserved_lessons"], "pre-failure scope must be preserved"
    run = db_session.get(GenerationRun, uuid.UUID(observation["run_id"]))
    assert run.status == "complete"
    assert run.model_calls == observation["expected_model_calls"]


def test_fault_profiles_gated_to_fake_evaluation_environments(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "model_adapter", "deepseek", raising=False)
    with pytest.raises(ModelProviderError):
        FakeModelAdapter.activate_eval_faults(
            {"generation_write_lesson": {"lesson_index": 1, "mode": "provider_persistent"}}
        )
    monkeypatch.setattr(settings, "model_adapter", "fake", raising=False)
    monkeypatch.setattr(settings, "eval_fault_profile", "", raising=False)
    with pytest.raises(ModelProviderError):
        FakeModelAdapter.activate_eval_faults(
            {"generation_write_lesson": {"lesson_index": 1, "mode": "provider_persistent"}}
        )
    monkeypatch.setattr(settings, "eval_fault_profile", "enabled", raising=False)
    FakeModelAdapter.activate_eval_faults(
        {"generation_write_lesson": {"lesson_index": 1, "mode": "truncated_json"}}
    )
    response = FakeModelAdapter().complete(
        "system", json.dumps({"kind": "generation_write_lesson", "lesson": {"lesson_index": 1}})
    )
    assert "}" not in response.text  # truncated payload, unparseable
    FakeModelAdapter.activate_eval_faults(None)


# ---------------------------------------------------------------------------
# TS-007: duplicate submission
# ---------------------------------------------------------------------------


def test_fault_duplicate_submission_converges_on_one_run(client, auth, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "eval_fault_profile", "enabled", raising=False)
    project_id = _create_project(client, auth)
    payload = _create_pass(client, auth, project_id, scenario="fault:duplicate_submission")
    evaluation = payload["evaluation"]

    outcome = _criterion(evaluation, "C-IDEM-1")
    assert outcome["outcome"] == "pass"
    evidence = outcome["evidence"]
    assert len(evidence["returned_run_ids"]) == 2
    assert evidence["returned_run_ids"][0] == evidence["returned_run_ids"][1]
    assert len(evidence["distinct_runs_for_kind"]) == 1


# ---------------------------------------------------------------------------
# TS-008: stale-version supersession
# ---------------------------------------------------------------------------


def test_fault_stale_version_superseded_never_publishes(client, auth, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "eval_fault_profile", "enabled", raising=False)
    project_id = _create_project(client, auth)
    payload = _create_pass(client, auth, project_id, scenario="fault:stale_version")
    evaluation = payload["evaluation"]

    outcome = _criterion(evaluation, "C-SUPER-1")
    assert outcome["outcome"] == "pass"
    observation = outcome["evidence"]["observation"]
    stale = db_session.get(GenerationRun, uuid.UUID(observation["stale_run_id"]))
    assert stale.status == "superseded"
    newer = db_session.get(GenerationRun, uuid.UUID(observation["newer_run_id"]))
    assert newer.status == "complete"
    assert newer.brief_version_id != stale.brief_version_id


# ---------------------------------------------------------------------------
# TS-009: partial render
# ---------------------------------------------------------------------------


def test_fault_partial_render_records_explicit_failure(client, auth, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "eval_fault_profile", "enabled", raising=False)
    project_id = _create_project(client, auth)
    payload = _create_pass(client, auth, project_id, scenario="fault:partial_render")
    evaluation = payload["evaluation"]

    outcome = _criterion(evaluation, "C-RENDER-1")
    assert outcome["outcome"] == "pass"
    observation = outcome["evidence"]["observation"]
    assert observation["settled_status_after_fault"] in ("partial_failure", "capped_failure")
    run = db_session.get(GenerationRun, uuid.UUID(observation["run_id"]))
    assert run.status == "complete"  # recovered after the fault cleared


# ---------------------------------------------------------------------------
# TS-012: overview/report contract
# ---------------------------------------------------------------------------


def test_report_contract_comparison_and_supersession(client, auth, db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "eval_fault_profile", "enabled", raising=False)
    project_id = _create_project(client, auth)
    created = _create_pass(client, auth, project_id, scenario="full_pipeline")
    assert created["evaluation"]["status"] == "completed"

    # With only a full pass recorded, the fault-evidence blocking criteria
    # have no records yet: the set-level outcome stays missing_evidence.
    data = client.get(
        f"/projects/{project_id}/technical-evaluation/report", headers=auth
    ).json()
    assert data["overall_outcome"] == "missing_evidence"

    for scenario in (
        "fault:duplicate_submission",
        "fault:stale_version",
        "fault:worker_provider_failure",
        "fault:partial_render",
    ):
        created = _create_pass(client, auth, project_id, scenario=scenario)
        assert created["evaluation"]["status"] == "completed", scenario

    report = client.get(f"/projects/{project_id}/technical-evaluation/report", headers=auth)
    assert report.status_code == 200, report.text
    data = report.json()
    assert data["dataset_revision"] == "eval-datasets-r1"
    assert data["product_validation_status"] == "not_evaluated"
    assert data["overall_outcome"] == "pass"  # every blocking class evidenced, none failed
    comparison = next(item for item in data["comparisons"] if item["pass_index"] == 1)
    assert comparison["comparison_available"] is False
    assert comparison["comparison_unavailable_reason"] == "该单元仅有此一遍"

    # Second pass of the same unit makes the comparison available; failure of
    # any pass stays explicit and unmasked.
    _create_pass(client, auth, project_id, pass_index=2)
    data = client.get(
        f"/projects/{project_id}/technical-evaluation/report", headers=auth
    ).json()
    first = next(item for item in data["comparisons"] if item["pass_index"] == 1)
    assert first["comparison_available"] is True
    assert sorted(first["comparable_pass_indexes"]) == [2]


def test_overview_marks_superseded_dataset_revision(client, auth, db_session):
    project_id = _create_project(client, auth)
    _create_pass(client, auth, project_id)
    row = db_session.scalar(select(TechnicalEvaluation))
    row.dataset_revision = "eval-datasets-r0"
    db_session.commit()

    overview = client.get(f"/projects/{project_id}/technical-evaluation", headers=auth).json()
    assert overview["passes"][0]["superseded_configuration"] is True


def test_create_rejects_unknown_unit_and_wrong_mode(client, auth, db_session):
    project_id = _create_project(client, auth)
    response = client.post(
        f"/projects/{project_id}/technical-evaluation/runs",
        json={"unit_key": "not-a-unit", "pass_index": 1, "mode": "deterministic"},
        headers=auth,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUIREMENT"

    response = client.post(
        f"/projects/{project_id}/technical-evaluation/runs",
        json={"unit_key": "travelling-around", "pass_index": 1, "mode": "live"},
        headers=auth,
    )
    assert response.status_code == 422
    assert "live" in response.json()["error"]["message"]


# ---------------------------------------------------------------------------
# TS-013: authorization non-disclosure
# ---------------------------------------------------------------------------


def test_cross_workspace_no_disclosure(client, auth, teacher_b_token, db_session):
    project_id = _create_project(client, auth)
    _create_pass(client, auth, project_id)
    other = {"Authorization": f"Bearer {teacher_b_token}"}
    evaluation_id = str(
        db_session.scalar(select(TechnicalEvaluation.id).where(
            TechnicalEvaluation.project_id == uuid.UUID(project_id)
        ))
    )

    for path in (
        f"/projects/{project_id}/technical-evaluation",
        f"/projects/{project_id}/technical-evaluation/report",
        f"/projects/{project_id}/technical-evaluation/runs/{evaluation_id}",
    ):
        response = client.get(path, headers=other)
        assert response.status_code in (403, 404), path
    response = client.post(
        f"/projects/{project_id}/technical-evaluation/runs",
        json={"unit_key": "travelling-around", "pass_index": 9, "mode": "deterministic"},
        headers=other,
    )
    assert response.status_code in (403, 404)
    unauthenticated = client.get(f"/projects/{project_id}/technical-evaluation")
    assert unauthenticated.status_code == 401


def _criterion(evaluation, key):
    return next(item for item in evaluation["criteria"] if item["criterion_key"] == key)


# ---------------------------------------------------------------------------
# TS-011: narration stream usage captured into trace events (F006 L-1)
# ---------------------------------------------------------------------------


def test_narration_stream_usage_captured_into_trace_events(client, auth, db_session):
    from lessoncanvas.modules.run_orchestration.evidence import estimated_cost_usd

    project_id = _create_project(client, auth)
    payload = _create_pass(client, auth, project_id)
    run_ids = _evaluation_run_ids(db_session, payload["evaluation"]["evaluation_id"])
    lesson_runs = [
        run_id
        for run_id in run_ids
        if (run := db_session.get(GenerationRun, run_id)) is not None
        and run.artifact_kind == "lesson_plan"
    ]
    run_id = lesson_runs[0]

    response = client.post(
        f"/projects/{project_id}/evidence/{run_id}/narrate", headers=auth
    )
    assert response.status_code == 202, response.text

    # Narration completes in a background thread; poll for the trace row.
    row = None
    for _ in range(40):
        db_session.expire_all()
        row = db_session.scalar(
            select(TraceEvent)
            .where(
                TraceEvent.run_id == run_id,
                TraceEvent.event_type == "model.evidence_narration",
            )
            .order_by(TraceEvent.created_at.desc())
        )
        if row is not None:
            break
        time.sleep(0.05)
    assert row is not None
    assert row.prompt_tokens is not None and row.completion_tokens is not None
    expected = round(estimated_cost_usd(row.prompt_tokens, row.completion_tokens), 6)
    assert row.cost_usd == expected


def test_deepseek_stream_requests_provider_usage(monkeypatch):
    import httpx

    from lessoncanvas.adapters.model import DeepSeekAdapter

    captured: dict = {}

    class _FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield 'data: {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 11}}'
            yield "data: [DONE]"

    def fake_stream(method, url, **kwargs):
        captured.update(kwargs)
        return _FakeStream()

    monkeypatch.setattr(httpx, "stream", fake_stream)
    tokens, usage = DeepSeekAdapter().stream_with_usage("sys", "user-payload")
    assert list(tokens) == []
    assert usage == {"prompt_tokens": 7, "completion_tokens": 11}
    assert captured["json"]["stream_options"] == {"include_usage": True}
