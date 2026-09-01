"""F009 TS-001: evaluation-dataset governance — three licensed, manifest-verified
synthetic units with fail-closed loading; plus the deletion-cascade half of
TS-013 for the F009 tables."""

import json
import shutil
import uuid

import pytest
from sqlalchemy import select

from lessoncanvas.models import TechnicalEvaluation, TechnicalEvaluationResult
from lessoncanvas.modules.technical_evaluation.dataset import (
    DatasetGovernanceError,
    load_dataset,
    package_root,
)

pytestmark = pytest.mark.skipif(
    package_root().joinpath("manifest.json").is_file() is False,
    reason="dataset package missing",
)


def _copy_dataset(tmp_path):
    root = tmp_path / "dataset"
    shutil.copytree(package_root(), root)
    return root


def _rehash(root, relative: str) -> None:
    import hashlib

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def test_dataset_loads_three_licensed_manifest_verified_units():
    bundle = load_dataset()

    assert bundle.revision == "eval-datasets-r1"
    assert bundle.license == "CC0-1.0"
    assert set(bundle.units) == {"travelling-around", "natural-disasters", "cultural-heritage"}
    assert bundle.units["travelling-around"].output_mode == "english"
    assert bundle.units["natural-disasters"].output_mode == "chinese"
    assert bundle.units["cultural-heritage"].output_mode == "bilingual"
    for unit in bundle.units.values():
        assert unit.license == "CC0-1.0"
        assert unit.synthetic is True
        assert unit.source_files
        assert unit.expected_evidence_direction
        for source in unit.source_files:
            assert source.content.startswith("LessonCanvas Evaluation Dataset")
            assert "CC0-1.0" in source.content.splitlines()[0]
    assert bundle.units["travelling-around"].output_language_value == "English"
    assert bundle.units["natural-disasters"].output_language_value == "中文"
    assert bundle.units["cultural-heritage"].output_language_value == "中英双语"


def test_dataset_fails_closed_on_tampered_file(tmp_path):
    root = _copy_dataset(tmp_path)
    target = root / "units/travelling-around/sources/01-reading-passage.txt"
    target.write_text(target.read_text(encoding="utf-8") + "\ntampered", encoding="utf-8")

    with pytest.raises(DatasetGovernanceError, match="file hash must match the manifest"):
        load_dataset(root)


def test_dataset_fails_closed_on_unlisted_file(tmp_path):
    root = _copy_dataset(tmp_path)
    (root / "units/natural-disasters/sources/03-extra.txt").write_text(
        "unlisted content", encoding="utf-8"
    )

    with pytest.raises(DatasetGovernanceError, match="must be manifest-listed"):
        load_dataset(root)


def test_dataset_fails_closed_on_missing_manifest_entry(tmp_path):
    root = _copy_dataset(tmp_path)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["files"]["units/cultural-heritage/unit.json"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(DatasetGovernanceError, match="must be manifest-listed"):
        load_dataset(root)


def test_dataset_fails_closed_on_unlicensed_unit(tmp_path):
    root = _copy_dataset(tmp_path)
    unit_path = root / "units/travelling-around/unit.json"
    payload = json.loads(unit_path.read_text(encoding="utf-8"))
    payload["license"] = "ALL_RIGHTS_RESERVED"
    unit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _rehash(root, "units/travelling-around/unit.json")

    with pytest.raises(DatasetGovernanceError, match="CC0-1.0 dedication"):
        load_dataset(root)


def test_dataset_fails_closed_on_unit_key_mismatch(tmp_path):
    root = _copy_dataset(tmp_path)
    unit_path = root / "units/natural-disasters/unit.json"
    payload = json.loads(unit_path.read_text(encoding="utf-8"))
    payload["unit_key"] = "some-other-unit"
    unit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _rehash(root, "units/natural-disasters/unit.json")

    with pytest.raises(DatasetGovernanceError, match="unit_key must match"):
        load_dataset(root)


def test_dataset_fails_closed_on_unlicensed_source_header(tmp_path):
    root = _copy_dataset(tmp_path)
    target = root / "units/cultural-heritage/sources/01-reading-passage.txt"
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    target.write_text("".join(lines[1:]), encoding="utf-8")
    _rehash(root, "units/cultural-heritage/sources/01-reading-passage.txt")

    with pytest.raises(DatasetGovernanceError, match="license header"):
        load_dataset(root)


def test_evaluation_rows_deleted_with_project(client, auth, db_session):
    from lessoncanvas.models import Project

    project_id = client.post("/projects", json={"name": "评估级联"}, headers=auth).json()["id"]
    project = db_session.scalar(select(Project).where(Project.id == uuid.UUID(project_id)))

    evaluation = TechnicalEvaluation(
        project_id=project.id,
        workspace_id=project.workspace_id,
        dataset_revision="eval-datasets-r1",
        unit_key="travelling-around",
        pass_index=1,
        mode="deterministic",
        scenario="full_pipeline",
        model_config_json="{}",
        memory_state_json='{"memory_state": "empty (F013 not implemented)"}',
        created_by="teacher_a",
    )
    db_session.add(evaluation)
    db_session.flush()
    db_session.add(
        TechnicalEvaluationResult(
            evaluation_id=evaluation.id,
            criterion_key="C-MEM-1",
            classification="blocking",
            outcome="pass",
            evidence_json="{}",
        )
    )
    db_session.commit()

    response = client.delete(f"/projects/{project_id}", headers=auth)
    assert response.status_code in (200, 202), response.text
    assert db_session.scalar(select(TechnicalEvaluation.id)) is None
    assert db_session.scalar(select(TechnicalEvaluationResult.id)) is None
