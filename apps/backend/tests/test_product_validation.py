"""F010 Teacher Product Validation tests (Spec AC-001..AC-010; Test Design
TS-001..TS-015). All scenarios run on the deterministic stack — the Feature
makes zero model calls."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy import select

from lessoncanvas.models import (
    BlueprintVersion,
    BriefVersion,
    ExerciseArtifact,
    GenerationRun,
    LessonPlanArtifact,
    ProductValidationAssignment,
    ProductValidationEvidence,
    Project,
    RunEvent,
    SlideDeckArtifact,
    Workspace,
)
from lessoncanvas.modules.product_validation import rubric
from lessoncanvas.modules.product_validation import service as pv_service

CORPUS = "\n".join(
    [
        "单元主题：环境保护与可持续发展",
        "课时数：3",
        "学情：高二学生，英语中等水平",
        "教学目标：提升阅读与表达能力；发展批判性思维",
        "教材定位：外研社必修一 Unit 3",
        "输出语言：中英双语",
        "评估倾向：形成性评价为主",
        "课时分配：共6课时，每课2课时，评估聚焦综合输出",
    ]
)


def valid_evidence_payload(
    *,
    score: int = 5,
    severe_findings: list | None = None,
    structural_rework: bool = False,
) -> dict:
    return {
        "scores": {
            key: {"score": score, "note": f"{key} 的评审证据说明"}
            for key in rubric.DIMENSION_KEYS
        },
        "severe_findings": severe_findings or [],
        "structural_rework_required": structural_rework,
        "structural_rework_reason": "需要重新组织单元结构" if structural_rework else None,
        "overall_comment": "整体可用",
        "attestation": {
            "evaluator_reference": "外部高中英语教师-01",
            "completed_date": "2026-09-01",
        },
    }


# ---------------------------------------------------------------------------
# TS-001 (schema half): rubric governance — full-violation listing, nothing
# persisted by the pure validator, valid payload accepted.
# ---------------------------------------------------------------------------


class TestRubricSchema:
    def test_valid_payload_passes(self):
        assert rubric.validate_evidence(valid_evidence_payload()) == []

    @pytest.mark.parametrize(
        "mutation,expected_field",
        [
            # out-of-range / non-integer score
            (lambda p: p["scores"]["knowledge_correctness"].__setitem__("score", 6),
             "scores.knowledge_correctness.score"),
            (lambda p: p["scores"]["language_quality"].__setitem__("score", "4"),
             "scores.language_quality.score"),
            # missing evidence note
            (lambda p: p["scores"]["objective_alignment"].__setitem__("note", "  "),
             "scores.objective_alignment.note"),
            # missing dimension entry
            (lambda p: p["scores"].pop("teaching_usability"),
             "scores.teaching_usability"),
            # unknown dimension
            (lambda p: p["scores"].__setitem__("extra_dim", {"score": 3, "note": "x"}),
             "scores.extra_dim"),
        ],
    )
    def test_dimension_violations_listed(self, mutation, expected_field):
        payload = valid_evidence_payload()
        mutation(payload)
        violations = rubric.validate_evidence(payload)
        assert any(v.startswith(expected_field) for v in violations)
        # every dimension violation is reported in one pass
        assert len(violations) >= 1

    def test_every_violation_listed_at_once(self):
        payload = valid_evidence_payload()
        payload["scores"]["knowledge_correctness"]["score"] = 0
        payload["scores"]["language_quality"].pop("note")
        payload["severe_findings"] = [
            {"class": "not_a_class", "lesson_reference": "", "evidence": ""}
        ]
        payload["structural_rework_required"] = "yes"
        payload.pop("attestation")
        violations = rubric.validate_evidence(payload)
        assert len(violations) == 7
        joined = "\n".join(violations)
        for field in (
            "scores.knowledge_correctness.score",
            "scores.language_quality.note",
            "severe_findings[0].class",
            "severe_findings[0].lesson_reference",
            "severe_findings[0].evidence",
            "structural_rework_required",
            "attestation",
        ):
            assert field in joined

    def test_severe_finding_rules(self):
        payload = valid_evidence_payload(
            severe_findings=[
                {"class": "answer_error", "lesson_reference": 3, "evidence": "答案与题目不匹配"}
            ]
        )
        assert rubric.validate_evidence(payload) == []
        bad = valid_evidence_payload(
            severe_findings=[{"class": "answer_error", "lesson_reference": 3}]
        )
        assert any("severe_findings[0].evidence" in v for v in rubric.validate_evidence(bad))

    def test_structural_rework_reason_required_only_when_true(self):
        rework_no_reason = valid_evidence_payload(structural_rework=True)
        rework_no_reason["structural_rework_reason"] = None
        violations = rubric.validate_evidence(rework_no_reason)
        assert any(v.startswith("structural_rework_reason") for v in violations)
        assert rubric.validate_evidence(valid_evidence_payload(structural_rework=True)) == []

    def test_attestation_date_validated(self):
        payload = valid_evidence_payload()
        payload["attestation"]["completed_date"] = "2026-02-30"
        assert any("completed_date" in v for v in rubric.validate_evidence(payload))
        payload["attestation"]["evaluator_reference"] = ""
        violations = rubric.validate_evidence(payload)
        assert any("evaluator_reference" in v for v in violations)

    def test_rubric_revision_is_fixed(self):
        assert rubric.RUBRIC_REVISION == "rubric-r1"
        sheet = rubric.rubric_sheet()
        assert sheet["rubric_revision"] == "rubric-r1"
        assert len(sheet["dimensions"]) == 5
        assert {c["class"] for c in sheet["severe_finding_classes"]} == set(
            rubric.SEVERE_FINDING_CLASSES
        )


# ---------------------------------------------------------------------------
# TS-002 / TS-003 (pure halves): thresholds, determinism, and the exact
# outcome rules — computed without any model call.
# ---------------------------------------------------------------------------


class TestOutcomeComputation:
    def test_all_thresholds_met_passes(self):
        outcome = rubric.compute_outcome(valid_evidence_payload(score=5))
        assert outcome["outcome"] == "passed"
        assert outcome["core_mean"] == 5.0
        assert outcome["violated_rules"] == []

    def test_single_severe_finding_fails(self):
        payload = valid_evidence_payload(
            severe_findings=[
                {"class": "knowledge_error", "lesson_reference": "2", "evidence": "事实性错误"}
            ]
        )
        outcome = rubric.compute_outcome(payload)
        assert outcome["outcome"] == "failed"
        assert "severe_finding_present" in outcome["violated_rules"]

    def test_core_mean_below_threshold_fails(self):
        payload = valid_evidence_payload(score=3)
        outcome = rubric.compute_outcome(payload)
        assert outcome["outcome"] == "failed"
        assert outcome["core_mean"] == 3.0
        assert "core_mean_below_threshold" in outcome["violated_rules"]

    def test_mean_exactly_at_threshold_passes(self):
        payload = valid_evidence_payload(score=4)
        payload["scores"]["knowledge_correctness"]["score"] = 5
        payload["scores"]["language_quality"]["score"] = 3
        outcome = rubric.compute_outcome(payload)
        assert outcome["core_mean"] == 4.0
        assert outcome["outcome"] == "passed"

    def test_structural_rework_fails(self):
        outcome = rubric.compute_outcome(valid_evidence_payload(structural_rework=True))
        assert outcome["outcome"] == "failed"
        assert "structural_rework_required" in outcome["violated_rules"]

    def test_identical_evidence_identical_outcome(self):
        payload = valid_evidence_payload(
            score=4,
            severe_findings=[
                {"class": "language_error", "lesson_reference": 1, "evidence": "拼写错误示范"}
            ],
        )
        assert rubric.compute_outcome(payload) == rubric.compute_outcome(payload)

    def test_invalid_evidence_rejected_by_compute(self):
        payload = valid_evidence_payload()
        payload["scores"]["knowledge_correctness"]["score"] = 9
        with pytest.raises(ValueError, match="rubric schema"):
            rubric.compute_outcome(payload)


# ---------------------------------------------------------------------------
# TS-008 (deletion half): rows and evidence documents removed with the
# project through the real cascade service.
# ---------------------------------------------------------------------------


class _StubStorage:
    def __init__(self):
        self.deleted: list[str] = []

    def delete(self, key: str) -> None:
        self.deleted.append(key)

    def list_prefix(self, prefix: str) -> list[str]:
        return []

    def exists(self, key: str) -> bool:
        return False


class TestModelCascade:
    def test_rows_deleted_with_project(self, db_session):
        from lessoncanvas.modules.identity_workspace.deletion import delete_project_cascade

        workspace = Workspace(subject="owner_a")
        db_session.add(workspace)
        db_session.flush()
        project = Project(workspace_id=workspace.id, name="evaluation anchor")
        db_session.add(project)
        db_session.flush()
        assignment = ProductValidationAssignment(
            project_id=project.id,
            workspace_id=workspace.id,
            unit_key="travelling-around",
            dataset_revision="eval-datasets-r1",
            package_json="{}",
            package_digest="digest-1",
            rubric_revision=rubric.RUBRIC_REVISION,
            created_by="owner_a",
        )
        db_session.add(assignment)
        db_session.flush()
        evidence = ProductValidationEvidence(
            assignment_id=assignment.id,
            evidence_revision="r1",
            evidence_json="{}",
            capture_channel="owner_mediated_import",
            document_object_key="artifacts/evidence/rubric.pdf",
            document_filename="rubric.pdf",
            outcome="passed",
            outcome_json="{}",
        )
        db_session.add(evidence)
        db_session.commit()

        storage = _StubStorage()
        delete_project_cascade(db_session, storage, workspace.id, project.id)
        db_session.commit()

        assert db_session.query(ProductValidationEvidence).count() == 0
        assert db_session.query(ProductValidationAssignment).count() == 0
        # Evidence-document objects are swept through the same artifacts-bucket
        # adapter path as F008 export objects (covered by test_deletion.py).


# ---------------------------------------------------------------------------
# Service-level fixtures: a confirmed project with a technically complete
# package, built through the real API against the fake adapter.
# ---------------------------------------------------------------------------


def _confirmed_blueprint_project(client, auth) -> str:
    response = client.post("/projects", json={"name": "产品验证测试"}, headers=auth)
    project_id = response.json()["id"]
    upload = client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", CORPUS.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    )
    assert upload.status_code == 201, upload.text
    assert client.post(f"/projects/{project_id}/discovery/start", headers=auth).status_code == 200
    assert client.post(f"/projects/{project_id}/brief/confirm", headers=auth).status_code == 200
    assert client.post(f"/projects/{project_id}/planning/start", headers=auth).status_code == 200
    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    base = state["draft_revision"]
    for finding in state.get("findings", []):
        if finding.get("tier") == "waivable" and finding.get("status") == "open":
            base = client.post(
                f"/projects/{project_id}/blueprint/decisions",
                json={
                    "finding_id": finding["id"],
                    "reason": "以教材与教师判断为准",
                    "base_revision": base,
                },
                headers=auth,
            ).json()["draft_revision"]
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": base},
        headers=auth,
    )
    assert confirmed.status_code == 200, confirmed.text
    return project_id


def _complete_unit(client, auth, project_id: str) -> None:
    assert client.post(f"/projects/{project_id}/generation/start", headers=auth).status_code == 200
    assert (
        client.post(f"/projects/{project_id}/decks/generation/start", headers=auth).status_code
        == 200
    )
    assert (
        client.post(
            f"/projects/{project_id}/exercises/generation/start",
            json={"difficulty": "foundation"},
            headers=auth,
        ).status_code
        == 200
    )


def _complete_project(client, auth) -> str:
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    return project_id


def _workspace_of(db_session, project_id: str):
    project = db_session.get(Project, uuid.UUID(project_id))
    return db_session.get(Workspace, project.workspace_id)


def _purge_family_run(db_session, project_id: str, family: str) -> None:
    project_uuid = uuid.UUID(project_id)
    model = {
        "lesson_plan": LessonPlanArtifact,
        "slide_deck": SlideDeckArtifact,
        "exercise": ExerciseArtifact,
    }[family]
    runs = list(
        db_session.scalars(
            select(GenerationRun).where(
                GenerationRun.project_id == project_uuid,
                GenerationRun.artifact_kind == family,
            )
        )
    )
    for run in runs:
        db_session.execute(sql_delete(RunEvent).where(RunEvent.run_id == run.id))
        db_session.execute(sql_delete(model).where(model.run_id == run.id))
        db_session.execute(sql_delete(GenerationRun).where(GenerationRun.id == run.id))
    db_session.commit()


class _Doc:
    def __init__(self, filename: str = "rubric.pdf", content_type: str = "application/pdf"):
        self.filename = filename
        self.content_type = content_type
        self.data = b"%PDF-1.4 original completed rubric document"


# ---------------------------------------------------------------------------
# TS-004: assignment creation — binding, idempotency (sequential +
# concurrent), incomplete-package rejection.
# ---------------------------------------------------------------------------


class TestAssignmentCreation:
    def test_binds_immutable_package_identity(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)

        assignment, created = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "travelling-around"
        )
        assert created is True
        assert assignment.dataset_revision == "eval-datasets-r1"
        assert assignment.brief_version_id is not None
        assert assignment.blueprint_version_id is not None
        assert assignment.rubric_revision == rubric.RUBRIC_REVISION
        assert assignment.state == "pending_evidence"
        package = __import__("json").loads(assignment.package_json)
        assert package["lessons"], "package must record per-lesson members"
        for lesson in package["lessons"]:
            for family in ("lesson_plan", "slide_deck", "exercise"):
                member = lesson["members"][family]
                assert member["state"] == "complete"
                assert member["artifact_id"]
                assert member["files"], "members must carry checksums"

    def test_sequential_duplicate_returns_existing(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)

        first, created_first = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "natural-disasters"
        )
        second, created_second = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "natural-disasters"
        )
        assert created_first is True and created_second is False
        assert second.id == first.id
        assert (
            db_session.query(ProductValidationAssignment).count() == 1
        ), "duplicate create must not fork a second row"

    def test_concurrent_duplicates_converge_on_one_row(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace_id = _workspace_of(db_session, project_id).id
        project_uuid = uuid.UUID(project_id)

        def create(_):
            from lessoncanvas.db import SessionLocal

            with SessionLocal() as session:
                workspace = session.get(Workspace, workspace_id)
                return pv_service.create_assignment(
                    session, workspace, project_uuid, "cultural-heritage"
                )

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(create, range(4)))
        ids = {assignment.id for assignment, _ in results}
        assert len(ids) == 1, "concurrent duplicate creates must converge on one assignment"

    def test_incomplete_package_rejected_with_named_gaps(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        _purge_family_run(db_session, project_id, "slide_deck")
        workspace = _workspace_of(db_session, project_id)

        with pytest.raises(pv_service.ProductValidationError) as error:
            pv_service.create_assignment(
                db_session, workspace, uuid.UUID(project_id), "travelling-around"
            )
        gaps = error.value.details["gaps"]
        assert gaps and all(gap["family"] == "slide_deck" for gap in gaps)
        assert error.value.details["gate"] == "complete_package"
        assert db_session.query(ProductValidationAssignment).count() == 0

    def test_unknown_unit_rejected(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        with pytest.raises(pv_service.ProductValidationError, match="unknown evaluation unit"):
            pv_service.create_assignment(
                db_session, workspace, uuid.UUID(project_id), "not-a-unit"
            )


# ---------------------------------------------------------------------------
# TS-002/TS-005 (service halves): import, outcome recording, idempotency,
# revision supersession, immutability.
# ---------------------------------------------------------------------------


class TestEvidenceImport:
    def _assignment(self, client, auth, db_session, unit="travelling-around"):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        assignment, _ = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), unit
        )
        return project_id, workspace, assignment

    def test_import_records_outcome_and_concludes_assignment(self, client, auth, db_session):
        project_id, workspace, assignment = self._assignment(client, auth, db_session)
        evidence, created = pv_service.import_evidence(
            db_session,
            workspace,
            uuid.UUID(project_id),
            assignment.id,
            "r1",
            valid_evidence_payload(score=5),
            _Doc(),
        )
        assert created is True
        assert evidence.outcome == "passed"
        assert evidence.capture_channel == "owner_mediated_import"
        assert evidence.document_object_key
        db_session.expire_all()
        refreshed = db_session.get(ProductValidationAssignment, assignment.id)
        assert refreshed.state == "passed"
        assert refreshed.concluded_at is not None

    def test_failed_outcome_from_severe_finding(self, client, auth, db_session):
        project_id, workspace, assignment = self._assignment(client, auth, db_session)
        payload = valid_evidence_payload(
            severe_findings=[
                {"class": "knowledge_error", "lesson_reference": "1", "evidence": "事实错误"}
            ]
        )
        evidence, _ = pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), assignment.id, "r1", payload, _Doc()
        )
        assert evidence.outcome == "failed"
        db_session.expire_all()
        assert db_session.get(ProductValidationAssignment, assignment.id).state == "failed"

    def test_invalid_evidence_persists_nothing(self, client, auth, db_session):
        project_id, workspace, assignment = self._assignment(client, auth, db_session)
        payload = valid_evidence_payload()
        payload["scores"]["knowledge_correctness"]["score"] = 9
        with pytest.raises(pv_service.ProductValidationError) as error:
            pv_service.import_evidence(
                db_session, workspace, uuid.UUID(project_id), assignment.id, "r1", payload, _Doc()
            )
        assert error.value.details["violations"]
        assert db_session.query(ProductValidationEvidence).count() == 0
        db_session.expire_all()
        refreshed = db_session.get(ProductValidationAssignment, assignment.id)
        assert refreshed.state == "pending_evidence"

    def test_duplicate_revision_idempotent(self, client, auth, db_session):
        project_id, workspace, assignment = self._assignment(client, auth, db_session)
        first, created_first = pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), assignment.id, "r1",
            valid_evidence_payload(score=5), _Doc(),
        )
        second, created_second = pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), assignment.id, "r1",
            valid_evidence_payload(score=3), _Doc(),  # different content, same revision
        )
        assert created_first is True and created_second is False
        assert second.id == first.id
        assert second.outcome == "passed", "duplicate must not recompute from new content"
        assert db_session.query(ProductValidationEvidence).count() == 1

    def test_corrected_revision_supersedes_and_prior_stays_immutable(
        self, client, auth, db_session
    ):
        project_id, workspace, assignment = self._assignment(client, auth, db_session)
        r1, _ = pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), assignment.id, "r1",
            valid_evidence_payload(
                severe_findings=[
                    {"class": "answer_error", "lesson_reference": 2, "evidence": "答案错误"}
                ]
            ),
            _Doc(),
        )
        assert r1.outcome == "failed"

        corrected = valid_evidence_payload(score=5)
        r2, created = pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), assignment.id, "r2", corrected, _Doc()
        )
        assert created is True
        assert r2.outcome == "passed"
        db_session.expire_all()
        prior = db_session.get(ProductValidationEvidence, r1.id)
        assert prior.status == "superseded"
        assert prior.superseded_by_evidence_id == r2.id
        assert prior.outcome == "failed", "prior evidence stays historical and immutable"
        assert db_session.get(ProductValidationAssignment, assignment.id).state == "passed"

    def test_document_boundary_enforced(self, client, auth, db_session):
        project_id, workspace, assignment = self._assignment(client, auth, db_session)
        with pytest.raises(pv_service.ProductValidationError, match="type is not allowed"):
            pv_service.import_evidence(
                db_session, workspace, uuid.UUID(project_id), assignment.id, "r1",
                valid_evidence_payload(), _Doc("evil.exe", "application/x-msdownload"),
            )
        assert db_session.query(ProductValidationEvidence).count() == 0
        empty = _Doc()
        empty.data = b""
        with pytest.raises(pv_service.ProductValidationError, match="is required"):
            pv_service.import_evidence(
                db_session, workspace, uuid.UUID(project_id), assignment.id, "r1",
                valid_evidence_payload(), empty,
            )
        assert db_session.query(ProductValidationEvidence).count() == 0

    def test_conclude_not_complete(self, client, auth, db_session):
        project_id, workspace, assignment = self._assignment(client, auth, db_session)
        concluded = pv_service.conclude_not_complete(
            db_session,
            workspace,
            uuid.UUID(project_id),
            assignment.id,
            "评审教师在交付窗口内无法完成评审",
        )
        assert concluded.state == "not_complete"
        assert concluded.not_complete_reason
        with pytest.raises(pv_service.ProductValidationError, match="immutable"):
            pv_service.conclude_not_complete(
                db_session, workspace, uuid.UUID(project_id), assignment.id, "再次结论"
            )


# ---------------------------------------------------------------------------
# TS-003/TS-006 (service halves): overall-status derivation and staleness.
# ---------------------------------------------------------------------------


class TestOverallAndStaleness:
    def test_not_evaluated_without_assignments(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        assert (
            pv_service.derive_overall_status(db_session, uuid.UUID(project_id))
            == "not_evaluated"
        )

    def test_in_progress_with_pending_units(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        project_uuid = uuid.UUID(project_id)
        pv_service.create_assignment(db_session, workspace, project_uuid, "travelling-around")
        pv_service.create_assignment(db_session, workspace, project_uuid, "natural-disasters")
        assert pv_service.derive_overall_status(db_session, project_uuid) == "in_progress"

    def test_failed_is_definitive_even_with_pending_units(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        project_uuid = uuid.UUID(project_id)
        failed_assignment, _ = pv_service.create_assignment(
            db_session, workspace, project_uuid, "travelling-around"
        )
        pv_service.create_assignment(db_session, workspace, project_uuid, "natural-disasters")
        pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), failed_assignment.id, "r1",
            valid_evidence_payload(
                severe_findings=[
                    {"class": "language_error", "lesson_reference": 1, "evidence": "语言错误"}
                ]
            ),
            _Doc(),
        )
        assert pv_service.derive_overall_status(db_session, uuid.UUID(project_id)) == "failed"

    def test_passed_requires_every_unit(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        first, _ = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "travelling-around"
        )
        pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), first.id, "r1",
            valid_evidence_payload(score=5), _Doc(),
        )
        second, _ = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "cultural-heritage"
        )
        pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), second.id, "r1",
            valid_evidence_payload(score=4), _Doc(),
        )
        assert pv_service.derive_overall_status(db_session, uuid.UUID(project_id)) == "passed"

    def test_not_complete_from_concluded_unit(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        assignment, _ = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "travelling-around"
        )
        pv_service.conclude_not_complete(
            db_session, workspace, uuid.UUID(project_id), assignment.id, "教师不可用"
        )
        assert pv_service.derive_overall_status(db_session, uuid.UUID(project_id)) == "not_complete"

    def _newer_pair(self, db_session, project_id: str):
        """Simulate a newer confirmed pair (F007 regeneration path outcome)."""
        project_uuid = uuid.UUID(project_id)
        brief = db_session.scalar(
            select(BriefVersion).where(BriefVersion.project_id == project_uuid)
        )
        blueprint = db_session.scalar(
            select(BlueprintVersion).where(BlueprintVersion.project_id == project_uuid)
        )
        newer_brief = BriefVersion(
            project_id=project_uuid,
            workspace_id=brief.workspace_id,
            version=brief.version + 1,
            source_revision=brief.source_revision + 1,
            fields_json=brief.fields_json,
        )
        db_session.add(newer_brief)
        db_session.flush()
        newer_blueprint = BlueprintVersion(
            project_id=project_uuid,
            workspace_id=blueprint.workspace_id,
            version=blueprint.version + 1,
            source_revision=blueprint.source_revision + 1,
            brief_version_id=newer_brief.id,
            payload_json=blueprint.payload_json,
        )
        db_session.add(newer_blueprint)
        db_session.commit()

    def test_stale_after_newer_confirmed_pair_and_result_never_transfers(
        self, client, auth, db_session
    ):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        assignment, _ = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "travelling-around"
        )
        pv_service.import_evidence(
            db_session, workspace, uuid.UUID(project_id), assignment.id, "r1",
            valid_evidence_payload(score=5), _Doc(),
        )
        assert pv_service.derive_overall_status(db_session, uuid.UUID(project_id)) == "passed"

        self._newer_pair(db_session, project_id)

        overview = pv_service.overview(db_session, uuid.UUID(project_id))
        row = overview["assignments"][0]
        assert row["state"] == "stale"
        assert row["staleness"]["reason"] == "newer_confirmed_pair"
        assert overview["overall_status"] == "not_complete"
        assert row["outcome"] == "passed", "historical outcome stays readable, never transfers"

        # import onto the stale assignment is blocked
        with pytest.raises(pv_service.ProductValidationError, match="superseded"):
            pv_service.import_evidence(
                db_session, workspace, uuid.UUID(project_id), assignment.id, "r2",
                valid_evidence_payload(score=5), _Doc(),
            )

        # a new assignment on the new package starts not_evaluated for that unit
        newer_assignment, created = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "travelling-around"
        )
        assert created is True and newer_assignment.id != assignment.id

    def test_stale_after_package_artifact_change(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        workspace = _workspace_of(db_session, project_id)
        assignment, _ = pv_service.create_assignment(
            db_session, workspace, uuid.UUID(project_id), "travelling-around"
        )
        assert pv_service.assignment_staleness(db_session, assignment) is None

        _purge_family_run(db_session, project_id, "exercise")
        staleness = pv_service.assignment_staleness(db_session, assignment)
        assert staleness is not None
        assert staleness["reason"] == "package_changed"

    def test_overview_carries_bounded_conclusion_and_rubric_revision(
        self, client, auth, db_session
    ):
        project_id = _complete_project(client, auth)
        overview = pv_service.overview(db_session, uuid.UUID(project_id))
        assert overview["rubric_revision"] == "rubric-r1"
        assert overview["overall_status"] == "not_evaluated"
        assert "不可推广" in overview["bounded_conclusion"]


# ---------------------------------------------------------------------------
# TS-001/TS-007/TS-008/TS-009/TS-010 (API halves): endpoints, live shared
# surfaces, authorization/non-disclosure, publication boundary.
# ---------------------------------------------------------------------------


def _api_assign(client, auth, project_id: str, unit: str = "travelling-around") -> dict:
    response = client.post(
        f"/projects/{project_id}/product-validation/assignments",
        json={"unit_key": unit},
        headers=auth,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _api_import(
    client,
    auth,
    project_id: str,
    assignment_id: str,
    revision: str = "r1",
    payload: dict | None = None,
):
    import json as _json

    return client.post(
        f"/projects/{project_id}/product-validation/assignments/{assignment_id}/evidence",
        data={
            "evidence_revision": revision,
            "evidence": _json.dumps(
                payload or valid_evidence_payload(score=5), ensure_ascii=False
            ),
        },
        files={"document": ("rubric.pdf", b"%PDF-1.4 original", "application/pdf")},
        headers=auth,
    )


class TestAPI:
    def test_owner_journey_create_import_overview_document(self, client, auth):
        project_id = _complete_project(client, auth)

        empty = client.get(f"/projects/{project_id}/product-validation", headers=auth)
        assert empty.status_code == 200
        assert empty.json()["overall_status"] == "not_evaluated"

        assignment = _api_assign(client, auth, project_id)
        assert assignment["state"] == "pending_evidence"

        detail = client.get(
            f"/projects/{project_id}/product-validation/assignments/{assignment['id']}",
            headers=auth,
        )
        assert detail.status_code == 200
        body = detail.json()
        assert body["package"]["lessons"], "detail exposes the bound package identity"
        assert body["rubric_sheet"]["rubric_revision"] == "rubric-r1"

        imported = _api_import(client, auth, project_id, assignment["id"])
        assert imported.status_code == 201, imported.text
        assert imported.json()["outcome"] == "passed"
        evidence_id = imported.json()["id"]

        overview = client.get(f"/projects/{project_id}/product-validation", headers=auth).json()
        assert overview["overall_status"] == "passed"
        assert overview["assignments"][0]["outcome"] == "passed"

        document = client.get(
            f"/projects/{project_id}/product-validation/assignments/{assignment['id']}"
            f"/evidence/{evidence_id}/document",
            headers=auth,
        )
        assert document.status_code == 200
        assert document.content == b"%PDF-1.4 original"

    def test_requirement_errors_carry_every_violation(self, client, auth):
        project_id = _complete_project(client, auth)
        assignment = _api_assign(client, auth, project_id)
        payload = valid_evidence_payload()
        payload["scores"]["knowledge_correctness"]["score"] = 9
        payload["severe_findings"] = [{"class": "wrong"}]
        response = _api_import(client, auth, project_id, assignment["id"], payload=payload)
        assert response.status_code == 422
        details = response.json()["error"]["details"]["violations"]
        assert any(v.startswith("scores.knowledge_correctness.score") for v in details)
        assert any(v.startswith("severe_findings[0]") for v in details)

        bad_json = client.post(
            f"/projects/{project_id}/product-validation/assignments/{assignment['id']}/evidence",
            data={"evidence_revision": "r1", "evidence": "{not json"},
            files={"document": ("rubric.pdf", b"%PDF-1.4", "application/pdf")},
            headers=auth,
        )
        assert bad_json.status_code == 422

    def test_incomplete_package_rejected_with_named_gaps(self, client, auth, db_session):
        project_id = _complete_project(client, auth)
        _purge_family_run(db_session, project_id, "slide_deck")
        response = client.post(
            f"/projects/{project_id}/product-validation/assignments",
            json={"unit_key": "travelling-around"},
            headers=auth,
        )
        assert response.status_code == 422
        gaps = response.json()["error"]["details"]["gaps"]
        assert gaps and all(gap["family"] == "slide_deck" for gap in gaps)

    def test_unknown_unit_rejected(self, client, auth):
        project_id = _complete_project(client, auth)
        response = client.post(
            f"/projects/{project_id}/product-validation/assignments",
            json={"unit_key": "not-a-unit"},
            headers=auth,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "REQUIREMENT"

    def test_shared_surfaces_show_live_separate_status(self, client, auth):
        project_id = _complete_project(client, auth)
        assignment = _api_assign(client, auth, project_id)
        failing = valid_evidence_payload(
            severe_findings=[
                {"class": "knowledge_error", "lesson_reference": 1, "evidence": "事实错误"}
            ]
        )
        assert (
            _api_import(client, auth, project_id, assignment["id"], payload=failing).status_code
            == 201
        )

        alignment = client.get(f"/projects/{project_id}/alignment", headers=auth).json()
        assert alignment["technical_status"] == "validated"
        assert alignment["product_validation_status"] == "failed"

        report = client.get(f"/projects/{project_id}/alignment/report", headers=auth).json()
        assert report["product_validation_status"] == "failed"

        tech_report = client.get(
            f"/projects/{project_id}/technical-evaluation/report", headers=auth
        ).json()
        assert tech_report["product_validation_status"] == "failed"
        assert "独立" in tech_report["technical_note"]
        assert "F010" not in tech_report["technical_note"]

    def test_cross_workspace_and_unauthenticated_no_disclosure(
        self, client, auth, teacher_b_token
    ):
        project_id = _complete_project(client, auth)
        assignment = _api_assign(client, auth, project_id)
        other = {"Authorization": f"Bearer {teacher_b_token}"}
        base = f"/projects/{project_id}/product-validation"
        for method, path, kwargs in (
            ("get", base, {}),
            ("post", f"{base}/assignments", {"json": {"unit_key": "travelling-around"}}),
            ("get", f"{base}/assignments/{assignment['id']}", {}),
            (
                "post",
                f"{base}/assignments/{assignment['id']}/evidence",
                {
                    "data": {"evidence_revision": "r1", "evidence": "{}"},
                    "files": {"document": ("r.pdf", b"%PDF", "application/pdf")},
                },
            ),
            (
                "post",
                f"{base}/assignments/{assignment['id']}/conclusion",
                {"json": {"reason": "cannot complete the review"}},
            ),
            (
                "get",
                f"{base}/assignments/{assignment['id']}/evidence/{assignment['id']}/document",
                {},
            ),
        ):
            response = getattr(client, method)(path, headers=other, **kwargs)
            assert response.status_code == 404, f"{method} {path} leaked: {response.status_code}"

        anonymous = client.get(base)
        assert anonymous.status_code == 401

    def test_publication_boundary_pseudonymous_only(self, client, auth):
        project_id = _complete_project(client, auth)
        assignment = _api_assign(client, auth, project_id)
        assert _api_import(client, auth, project_id, assignment["id"]).status_code == 201

        detail = client.get(
            f"/projects/{project_id}/product-validation/assignments/{assignment['id']}",
            headers=auth,
        ).json()
        current = [row for row in detail["evidence_history"] if row["status"] == "current"][0]
        attestation = current["evidence"]["attestation"]
        assert attestation["evaluator_reference"], "pseudonymous reference is recorded"
        assert set(attestation) == {"evaluator_reference", "completed_date"}

        alignment = client.get(f"/projects/{project_id}/alignment", headers=auth).json()
        tech_report = client.get(
            f"/projects/{project_id}/technical-evaluation/report", headers=auth
        ).json()
        serialized = str(alignment) + str(tech_report)
        assert "evaluator_reference" not in serialized
        assert "外部高中英语教师-01" not in serialized

    def test_untrusted_content_stored_verbatim_as_data(self, client, auth):
        project_id = _complete_project(client, auth)
        assignment = _api_assign(client, auth, project_id)
        payload = valid_evidence_payload()
        payload["scores"]["knowledge_correctness"]["note"] = (
            "<script>alert('x')</script> {{7*7}} <img src=x onerror=alert(1)>"
        )
        payload["overall_comment"] = "../../etc/passwd"
        response = _api_import(client, auth, project_id, assignment["id"], payload=payload)
        assert response.status_code == 201
        detail = client.get(
            f"/projects/{project_id}/product-validation/assignments/{assignment['id']}",
            headers=auth,
        ).json()
        note = detail["evidence_history"][0]["evidence"]["scores"]["knowledge_correctness"]["note"]
        assert note == "<script>alert('x')</script> {{7*7}} <img src=x onerror=alert(1)>"

    def test_conclusion_endpoint_records_honest_reason(self, client, auth):
        project_id = _complete_project(client, auth)
        assignment = _api_assign(client, auth, project_id)
        response = client.post(
            f"/projects/{project_id}/product-validation/assignments/{assignment['id']}/conclusion",
            json={"reason": "评审教师在交付窗口内无法完成评审"},
            headers=auth,
        )
        assert response.status_code == 200
        assert response.json()["state"] == "not_complete"
        overview = client.get(f"/projects/{project_id}/product-validation", headers=auth).json()
        assert overview["overall_status"] == "not_complete"
