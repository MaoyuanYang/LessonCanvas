"""F009 evaluation-dataset loader with fail-closed governance (Spec D1).

The dataset ships inside the distribution under
``lessoncanvas/evaluation_datasets``. Loading verifies the SHA-256 manifest
over every file, requires the CC0-1.0 dedication on every unit file, and
rejects any unlisted or unexpected file. Any violation raises
``DatasetGovernanceError`` naming the rule; no partial dataset is returned.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path

LICENSE_DEDICATION = "CC0-1.0"
LICENSE_HEADER = "LessonCanvas Evaluation Dataset"
OUTPUT_MODES = ("english", "chinese", "bilingual")


class DatasetGovernanceError(Exception):
    """Raised when the dataset violates its governance rules; loading fails closed."""


@dataclass(frozen=True)
class SourceFile:
    relative_path: str
    filename: str
    content: str


@dataclass(frozen=True)
class EvaluationUnit:
    unit_key: str
    title: str
    output_mode: str
    output_language_value: str
    license: str
    synthetic: bool
    description: str
    source_files: tuple[SourceFile, ...]
    discovery_answers: dict
    planning_answers: dict
    expected_evidence_direction: dict


@dataclass(frozen=True)
class DatasetBundle:
    revision: str
    license: str
    units: dict[str, EvaluationUnit]


def package_root() -> Path:
    return Path(str(resources.files("lessoncanvas.evaluation_datasets")))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition: bool, rule: str) -> None:
    if not condition:
        raise DatasetGovernanceError(f"dataset governance violation: {rule}")


def load_dataset(root: Path | None = None) -> DatasetBundle:
    base = root if root is not None else package_root()
    manifest_path = base / "manifest.json"
    _require(manifest_path.is_file(), "manifest.json must exist (fail closed)")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DatasetGovernanceError(
            "dataset governance violation: manifest.json must be valid JSON"
        ) from error

    revision = manifest.get("dataset_revision")
    _require(
        isinstance(revision, str) and bool(revision.strip()),
        "manifest must carry a non-empty dataset_revision",
    )
    listed: dict[str, str] = manifest.get("files") or {}
    _require(
        manifest.get("license") == LICENSE_DEDICATION,
        f"manifest license must be the {LICENSE_DEDICATION} dedication",
    )

    units_root = base / "units"
    present: set[str] = set()
    for path in sorted(units_root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            present.add(path.relative_to(base).as_posix())
    _require(
        present == set(listed),
        "every dataset file must be manifest-listed and every listed file must exist "
        f"(unlisted: {sorted(present - set(listed))}, missing: {sorted(set(listed) - present)})",
    )
    for relative, expected in listed.items():
        _require(
            _sha256(base / relative) == expected,
            f"file hash must match the manifest: {relative}",
        )

    units: dict[str, EvaluationUnit] = {}
    for unit_dir in sorted(p for p in units_root.iterdir() if p.is_dir()):
        unit_json_path = unit_dir / "unit.json"
        _require(
            unit_json_path.is_file(), f"unit directory must contain unit.json: {unit_dir.name}"
        )
        try:
            payload = json.loads(unit_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise DatasetGovernanceError(
                f"dataset governance violation: unit.json must be valid JSON: {unit_dir.name}"
            ) from error

        _require(
            payload.get("license") == LICENSE_DEDICATION,
            f"unit.json must carry the {LICENSE_DEDICATION} dedication: {unit_dir.name}",
        )
        _require(
            payload.get("synthetic") is True,
            f"unit must be declared synthetic: {unit_dir.name}",
        )
        unit_key = payload.get("unit_key")
        _require(
            unit_key == unit_dir.name,
            f"unit_key must match its directory name: {unit_dir.name}",
        )
        _require(
            payload.get("output_mode") in OUTPUT_MODES,
            f"output_mode must be one of {OUTPUT_MODES}: {unit_dir.name}",
        )
        source_paths = payload.get("source_files") or []
        _require(
            isinstance(source_paths, list) and bool(source_paths),
            f"unit must declare at least one source file: {unit_dir.name}",
        )
        sources: list[SourceFile] = []
        for relative in source_paths:
            source_path = unit_dir / str(relative)
            _require(
                source_path.is_file(),
                f"declared source must exist: {unit_dir.name}/{relative}",
            )
            content = source_path.read_text(encoding="utf-8")
            _require(
                content.startswith(LICENSE_HEADER)
                and LICENSE_DEDICATION in content.splitlines()[0],
                f"every source file must carry the license header: {unit_dir.name}/{relative}",
            )
            sources.append(
                SourceFile(
                    relative_path=str(relative),
                    filename=source_path.name,
                    content=content,
                )
            )
        for field in ("discovery_answers", "planning_answers"):
            _require(
                isinstance(payload.get(field), dict),
                f"unit {field} must be an object: {unit_dir.name}",
            )
        units[str(unit_key)] = EvaluationUnit(
            unit_key=str(unit_key),
            title=str(payload.get("title") or unit_key),
            output_mode=str(payload["output_mode"]),
            output_language_value=str(payload.get("output_language_value") or ""),
            license=str(payload["license"]),
            synthetic=True,
            description=str(payload.get("description") or ""),
            source_files=tuple(sources),
            discovery_answers=dict(payload.get("discovery_answers") or {}),
            planning_answers=dict(payload.get("planning_answers") or {}),
            expected_evidence_direction=dict(payload.get("expected_evidence_direction") or {}),
        )

    _require(len(units) >= 3, "dataset must contain the three representative units")
    return DatasetBundle(revision=str(revision), license=str(manifest["license"]), units=units)


@lru_cache
def cached_dataset() -> DatasetBundle:
    return load_dataset()
