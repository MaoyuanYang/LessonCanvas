"""F010 product-validation service (Spec D2/D3/D5/D6/D8): version-bound
assignment fixing, structured rubric-evidence import, deterministic outcome
computation, overall-status derivation, and read-side staleness. Zero model
calls; evaluation never mutates the content it measures."""

from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lessoncanvas.models import (
    AuditEvent,
    ProductValidationAssignment,
    ProductValidationEvidence,
    utcnow,
)
from lessoncanvas.modules.alignment_evaluation import service as alignment_service
from lessoncanvas.modules.product_validation import rubric
from lessoncanvas.modules.run_orchestration import service as run_service
from lessoncanvas.modules.technical_evaluation.dataset import (
    DatasetGovernanceError,
    cached_dataset,
)

FAMILIES = alignment_service.FAMILIES
CAPTURE_CHANNEL = "owner_mediated_import"

# Evidence-document upload boundary (untrusted file; stored privately in the
# artifacts bucket, deleted with the project).
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
DOCUMENT_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "image/png",
    "image/jpeg",
}

# F011 AC-005: the declared content type must agree with the leading bytes.
_ZIP_HEAD = b"PK\x03\x04"


def _content_matches(content_type: str, data: bytes) -> bool:
    head = data[:16]
    if content_type == "application/pdf":
        return head.startswith(b"%PDF-")
    if content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ):
        return head.startswith(_ZIP_HEAD)
    if content_type == "text/plain":
        for trim in range(4):  # the head may cut a multi-byte character
            try:
                head[: len(head) - trim or None].decode("utf-8")
                return True
            except UnicodeDecodeError:
                continue
        return False
    if content_type == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return head.startswith(b"\xff\xd8")
    return False

OVERALL_NOT_EVALUATED = "not_evaluated"
OVERALL_IN_PROGRESS = "in_progress"
OVERALL_NOT_COMPLETE = "not_complete"
OVERALL_PASSED = "passed"
OVERALL_FAILED = "failed"

STALE_NEWER_PAIR = "newer_confirmed_pair"
STALE_PACKAGE_CHANGED = "package_changed"


class ProductValidationError(Exception):
    """Requirement-class failure with field-level details."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AssignmentNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Package identity and staleness (Spec D5)
# ---------------------------------------------------------------------------


def _blueprint_lessons(payload_json: str | None) -> list[dict]:
    if not payload_json:
        return []
    payload = json.loads(payload_json)
    return sorted(payload.get("lessons") or [], key=lambda lesson: int(lesson.get("index") or 0))


def _package_snapshot(session: Session, project_id: uuid.UUID, brief, blueprint) -> dict:
    """Immutable identity of the current-of-record package under one confirmed
    pair: per-lesson per-family artifact ids and file checksums through the
    F008 alignment reads (current run first, then F007 retention)."""

    members = alignment_service.current_members(session, project_id, brief, blueprint)
    lessons = _blueprint_lessons(blueprint.payload_json)
    lesson_rows = []
    for lesson in lessons:
        index = int(lesson.get("index") or 0)
        lesson_rows.append(
            {
                "index": index,
                "title": lesson.get("title"),
                "members": {
                    family: members[(family, index)]
                    for family in FAMILIES
                },
            }
        )
    return {
        "brief_version": brief.version,
        "blueprint_version": blueprint.version,
        "brief_version_id": str(brief.id),
        "blueprint_version_id": str(blueprint.id),
        "lessons": lesson_rows,
    }


def _identity_core(snapshot: dict, unit_key: str, dataset_revision: str) -> list:
    """The stable identity the digest covers: pair ids plus every lesson's
    per-family artifact ids and file checksums."""
    rows = []
    for lesson in snapshot["lessons"]:
        for family in sorted(FAMILIES):
            member = lesson["members"][family]
            rows.append(
                [
                    lesson["index"],
                    family,
                    member.get("artifact_id"),
                    tuple(
                        (file.get("role"), file.get("checksum"))
                        for file in member.get("files", [])
                    ),
                ]
            )
    return [
        unit_key,
        dataset_revision,
        snapshot["brief_version_id"],
        snapshot["blueprint_version_id"],
        rows,
    ]


def _digest(snapshot: dict, unit_key: str, dataset_revision: str) -> str:
    payload = json.dumps(
        _identity_core(snapshot, unit_key, dataset_revision),
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _package_gaps(snapshot: dict) -> list[dict]:
    """Missing/incomplete family members named per lesson (F008 D3 vocabulary)."""
    gaps = []
    for lesson in snapshot["lessons"]:
        for family in FAMILIES:
            member = lesson["members"][family]
            if member.get("state") != "complete":
                gaps.append(
                    {
                        "lesson_index": lesson["index"],
                        "family": family,
                        "state": member.get("state", "missing"),
                    }
                )
    return gaps


def _current_pair(session: Session, project_id: uuid.UUID):
    return (
        run_service.current_brief_version(session, project_id),
        run_service.current_blueprint_version(session, project_id),
    )


def assignment_staleness(
    session: Session, assignment: ProductValidationAssignment
) -> dict | None:
    """Read-side staleness derivation (Spec D5): newer confirmed pair in the
    project, or the bound pair's current-of-record package identity drifted.
    Never mutates stored outcomes."""

    brief, blueprint = _current_pair(session, assignment.project_id)
    if (
        brief is None
        or blueprint is None
        or str(brief.id) != str(assignment.brief_version_id)
        or str(blueprint.id) != str(assignment.blueprint_version_id)
    ):
        if brief is not None and blueprint is not None:
            newer = f"简报 v{brief.version} · 蓝图 v{blueprint.version}"
        else:
            newer = "已有更新的确认版本对"
        return {"reason": STALE_NEWER_PAIR, "superseded_by": newer}
    snapshot = _package_snapshot(session, assignment.project_id, brief, blueprint)
    digest_now = _digest(snapshot, assignment.unit_key, assignment.dataset_revision)
    if digest_now != assignment.package_digest:
        return {"reason": STALE_PACKAGE_CHANGED, "superseded_by": "当前包的工件记录已变化"}
    return None


# ---------------------------------------------------------------------------
# Assignment creation (Spec D2/D8)
# ---------------------------------------------------------------------------


def create_assignment(
    session: Session, workspace, project_id: uuid.UUID, unit_key: str
) -> tuple[ProductValidationAssignment, bool]:
    """Fix the current complete package for a dataset unit as an immutable
    review assignment. Idempotent per (project, unit, package identity)."""

    try:
        bundle = cached_dataset()
    except DatasetGovernanceError as error:
        session.rollback()
        raise ProductValidationError(
            "evaluation dataset failed its governance check",
            {"rule": str(error)},
        ) from error
    if unit_key not in bundle.units:
        raise ProductValidationError(
            "unknown evaluation unit",
            {"unit_key": unit_key, "dataset_revision": bundle.revision},
        )

    brief, blueprint = _current_pair(session, project_id)
    if brief is None or blueprint is None:
        raise ProductValidationError(
            "confirmed brief and blueprint versions are required before fixing a review package",
            {"gate": "confirmed_pair"},
        )

    snapshot = _package_snapshot(session, project_id, brief, blueprint)
    gaps = _package_gaps(snapshot)
    if gaps:
        raise ProductValidationError(
            "the unit package is not technically complete; every lesson needs a complete "
            "lesson plan, slide deck, and exercise+answer set before review",
            {"gate": "complete_package", "gaps": gaps},
        )

    digest = _digest(snapshot, unit_key, bundle.revision)

    existing = session.scalars(
        select(ProductValidationAssignment).where(
            ProductValidationAssignment.project_id == project_id,
            ProductValidationAssignment.unit_key == unit_key,
            ProductValidationAssignment.package_digest == digest,
        )
    ).first()
    if existing is not None:
        return existing, False

    assignment = ProductValidationAssignment(
        project_id=project_id,
        workspace_id=workspace.id,
        unit_key=unit_key,
        dataset_revision=bundle.revision,
        brief_version_id=brief.id,
        blueprint_version_id=blueprint.id,
        package_json=json.dumps(snapshot, ensure_ascii=False),
        package_digest=digest,
        rubric_revision=rubric.RUBRIC_REVISION,
        created_by=workspace.subject,
    )
    session.add(assignment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalars(
            select(ProductValidationAssignment).where(
                ProductValidationAssignment.project_id == project_id,
                ProductValidationAssignment.unit_key == unit_key,
                ProductValidationAssignment.package_digest == digest,
            )
        ).first()
        if existing is None:
            raise
        return existing, False
    session.add(
        AuditEvent(
            workspace_id=workspace.id,
            actor=workspace.subject,
            action="product_validation.assignment_created",
            target_type="product_validation_assignment",
            target_id=str(assignment.id),
        )
    )
    session.commit()
    return assignment, True


# ---------------------------------------------------------------------------
# Evidence import and outcome recording (Spec D3/D6/D8)
# ---------------------------------------------------------------------------


def _get_assignment(
    session: Session, project_id: uuid.UUID, assignment_id: uuid.UUID
) -> ProductValidationAssignment:
    assignment = session.scalars(
        select(ProductValidationAssignment).where(
            ProductValidationAssignment.id == assignment_id,
            ProductValidationAssignment.project_id == project_id,
        )
    ).first()
    if assignment is None:
        raise AssignmentNotFoundError(str(assignment_id))
    return assignment


def _store_document(
    project_id: uuid.UUID, assignment_id: uuid.UUID, evidence_revision: str, document
) -> dict:
    """Store the evaluator's original completed rubric document (untrusted
    file) in the private artifacts bucket; returns stored metadata."""

    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.settings import get_settings

    data = document.data
    content_type = (document.content_type or "").split(";")[0].strip().lower()
    if not data:
        raise ProductValidationError(
            "the evaluator's original completed rubric document is required",
            {"field": "document"},
        )
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ProductValidationError(
            "rubric document exceeds the size limit",
            {"field": "document", "max_bytes": MAX_DOCUMENT_BYTES},
        )
    if content_type not in DOCUMENT_CONTENT_TYPES:
        raise ProductValidationError(
            "rubric document type is not allowed",
            {"field": "document", "allowed": sorted(DOCUMENT_CONTENT_TYPES)},
        )
    if not _content_matches(content_type, data):
        raise ProductValidationError(
            "rubric document content does not match its declared type",
            {"field": "document", "declared": content_type},
        )
    # Filename is untrusted metadata: keep only the final path component.
    safe_name = (document.filename or "rubric-document").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    key = f"product-validation/{project_id}/{assignment_id}/{evidence_revision}/{uuid.uuid4()}"
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
    storage.ensure_bucket()
    storage.put(key, data)
    return {
        "object_key": key,
        "filename": safe_name[:255],
        "content_type": content_type,
        "size_bytes": len(data),
        "checksum": hashlib.sha256(data).hexdigest(),
    }


def _best_effort_delete_document(object_key: str) -> None:
    """Cleanup for the exceptional commit-failure path so no private evidence
    object can outlive its owning row."""
    try:
        from lessoncanvas.adapters.storage import StorageAdapter
        from lessoncanvas.settings import get_settings

        StorageAdapter(bucket=get_settings().s3_bucket_artifacts).delete(object_key)
    except Exception:
        pass


def import_evidence(
    session: Session,
    workspace,
    project_id: uuid.UUID,
    assignment_id: uuid.UUID,
    evidence_revision: str,
    evidence: dict,
    document,
) -> tuple[ProductValidationEvidence, bool]:
    """Validate and import the evaluator's completed rubric evidence, compute
    the deterministic outcome in the same transaction, and supersede any prior
    evidence revision. Idempotent per (assignment, evidence revision)."""

    if not isinstance(evidence_revision, str) or not evidence_revision.strip():
        raise ProductValidationError(
            "evidence_revision is required", {"field": "evidence_revision"}
        )
    evidence_revision = evidence_revision.strip()[:32]

    assignment = _get_assignment(session, project_id, assignment_id)
    staleness = assignment_staleness(session, assignment)
    if staleness is not None:
        raise ProductValidationError(
            "the assignment's package was superseded; fix a new assignment before importing",
            {"gate": "stale_assignment", **staleness},
        )

    existing = session.scalars(
        select(ProductValidationEvidence).where(
            ProductValidationEvidence.assignment_id == assignment.id,
            ProductValidationEvidence.evidence_revision == evidence_revision,
        )
    ).first()
    if existing is not None:
        return existing, False

    violations = rubric.validate_evidence(evidence)
    if violations:
        raise ProductValidationError(
            "rubric evidence does not satisfy the fixed schema",
            {"violations": violations},
        )
    outcome = rubric.compute_outcome(evidence)

    prior_current = session.scalars(
        select(ProductValidationEvidence).where(
            ProductValidationEvidence.assignment_id == assignment.id,
            ProductValidationEvidence.status == "current",
        )
    ).first()

    row = ProductValidationEvidence(
        assignment_id=assignment.id,
        evidence_revision=evidence_revision,
        evidence_json=json.dumps(evidence, ensure_ascii=False),
        capture_channel=CAPTURE_CHANNEL,
        outcome=outcome["outcome"],
        outcome_json=json.dumps(outcome, ensure_ascii=False),
    )
    if prior_current is not None:
        prior_current.status = "superseded"
        session.add(prior_current)
    session.add(row)
    # Flush first so identity collisions surface before any private object is
    # stored; the document is only written once the row is certain to commit.
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = session.scalars(
            select(ProductValidationEvidence).where(
                ProductValidationEvidence.assignment_id == assignment.id,
                ProductValidationEvidence.evidence_revision == evidence_revision,
            )
        ).first()
        if existing is None:
            raise
        return existing, False

    try:
        document_meta = _store_document(project_id, assignment.id, evidence_revision, document)
    except ProductValidationError:
        # The flushed row must not survive a document-boundary rejection.
        session.rollback()
        raise
    row.document_object_key = document_meta["object_key"]
    row.document_filename = document_meta["filename"]
    row.document_content_type = document_meta["content_type"]
    row.document_size_bytes = document_meta["size_bytes"]
    row.document_checksum = document_meta["checksum"]
    if prior_current is not None:
        prior_current.superseded_by_evidence_id = row.id
        session.add(prior_current)

    assignment.state = outcome["outcome"]
    assignment.concluded_at = utcnow()
    session.add(assignment)
    try:
        session.commit()
    except Exception:
        # Never leave a private evidence object without its owning row.
        _best_effort_delete_document(document_meta["object_key"])
        raise
    session.add(
        AuditEvent(
            workspace_id=workspace.id,
            actor=workspace.subject,
            action="product_validation.evidence_imported",
            target_type="product_validation_evidence",
            target_id=str(row.id),
        )
    )
    session.commit()
    return row, True


def conclude_not_complete(
    session: Session, workspace, project_id: uuid.UUID, assignment_id: uuid.UUID, reason: str
) -> ProductValidationAssignment:
    """Conclude an assignment the evaluator cannot complete, recording the
    honest reason (Spec D9 fallback). Terminal states are immutable."""

    if not isinstance(reason, str) or not reason.strip():
        raise ProductValidationError(
            "a recorded reason is required to conclude not-complete",
            {"field": "reason"},
        )
    assignment = _get_assignment(session, project_id, assignment_id)
    if assignment.state != "pending_evidence":
        raise ProductValidationError(
            "only a pending assignment can be concluded not-complete; concluded "
            "outcomes are immutable",
            {"current_state": assignment.state},
        )
    assignment.state = "not_complete"
    assignment.not_complete_reason = reason.strip()
    assignment.concluded_at = utcnow()
    session.add(assignment)
    session.add(
        AuditEvent(
            workspace_id=workspace.id,
            actor=workspace.subject,
            action="product_validation.concluded_not_complete",
            target_type="product_validation_assignment",
            target_id=str(assignment.id),
        )
    )
    session.commit()
    return assignment


# ---------------------------------------------------------------------------
# Reads: overview, detail, and the shared-surface status (Spec D6/D7)
# ---------------------------------------------------------------------------


def _display_state(
    session: Session, assignment: ProductValidationAssignment
) -> tuple[str, dict | None]:
    staleness = assignment_staleness(session, assignment)
    if staleness is not None:
        return "stale", staleness
    return assignment.state, None


def _latest_assignment_per_unit(
    assignments: list[ProductValidationAssignment],
) -> dict[str, ProductValidationAssignment]:
    latest: dict[str, ProductValidationAssignment] = {}
    for assignment in sorted(assignments, key=lambda row: row.created_at):
        latest[assignment.unit_key] = assignment
    return latest


def derive_overall_status(session: Session, project_id: uuid.UUID) -> str:
    """Spec D6 precedence: not_evaluated -> failed (definitive) ->
    not_complete (not_complete or stale latest) -> in_progress -> passed."""

    assignments = list(
        session.scalars(
            select(ProductValidationAssignment).where(
                ProductValidationAssignment.project_id == project_id
            )
        )
    )
    if not assignments:
        return OVERALL_NOT_EVALUATED

    states = []
    for assignment in _latest_assignment_per_unit(assignments).values():
        state, _ = _display_state(session, assignment)
        states.append(state)

    if any(state == "failed" for state in states):
        return OVERALL_FAILED
    if any(state in ("not_complete", "stale") for state in states):
        return OVERALL_NOT_COMPLETE
    if any(state == "pending_evidence" for state in states):
        return OVERALL_IN_PROGRESS
    return OVERALL_PASSED


def overview(session: Session, project_id: uuid.UUID) -> dict:
    assignments = list(
        session.scalars(
            select(ProductValidationAssignment).where(
                ProductValidationAssignment.project_id == project_id
            ).order_by(ProductValidationAssignment.created_at)
        )
    )
    rows = []
    for assignment in assignments:
        state, staleness = _display_state(session, assignment)
        current_evidence = session.scalars(
            select(ProductValidationEvidence).where(
                ProductValidationEvidence.assignment_id == assignment.id,
                ProductValidationEvidence.status == "current",
            )
        ).first()
        rows.append(
            {
                "id": str(assignment.id),
                "unit_key": assignment.unit_key,
                "dataset_revision": assignment.dataset_revision,
                "brief_version_id": str(assignment.brief_version_id),
                "blueprint_version_id": str(assignment.blueprint_version_id),
                "rubric_revision": assignment.rubric_revision,
                "state": state,
                "staleness": staleness,
                "not_complete_reason": assignment.not_complete_reason,
                "outcome": current_evidence.outcome if current_evidence else None,
                "outcome_detail": (
                    json.loads(current_evidence.outcome_json) if current_evidence else None
                ),
                "created_at": assignment.created_at.isoformat(),
                "concluded_at": (
                    assignment.concluded_at.isoformat() if assignment.concluded_at else None
                ),
            }
        )
    return {
        "rubric_revision": rubric.RUBRIC_REVISION,
        "overall_status": derive_overall_status(session, project_id),
        "bounded_conclusion": (
            "产品验证基于一位外部高中英语教师的有限评审证据，不可推广到其他教师、学校或地区。"
        ),
        "assignments": rows,
    }


def detail(session: Session, project_id: uuid.UUID, assignment_id: uuid.UUID) -> dict:
    assignment = _get_assignment(session, project_id, assignment_id)
    state, staleness = _display_state(session, assignment)
    evidence_rows = list(
        session.scalars(
            select(ProductValidationEvidence).where(
                ProductValidationEvidence.assignment_id == assignment.id
            ).order_by(ProductValidationEvidence.created_at)
        )
    )
    history = []
    for row in evidence_rows:
        history.append(
            {
                "id": str(row.id),
                "evidence_revision": row.evidence_revision,
                "status": row.status,
                "capture_channel": row.capture_channel,
                "outcome": row.outcome,
                "outcome_detail": json.loads(row.outcome_json),
                "evidence": json.loads(row.evidence_json),
                "document": {
                    "filename": row.document_filename,
                    "content_type": row.document_content_type,
                    "size_bytes": row.document_size_bytes,
                    "checksum": row.document_checksum,
                    "downloadable": row.document_object_key is not None,
                },
                "created_at": row.created_at.isoformat(),
                "superseded_by_evidence_id": (
                    str(row.superseded_by_evidence_id)
                    if row.superseded_by_evidence_id
                    else None
                ),
            }
        )
    return {
        "id": str(assignment.id),
        "unit_key": assignment.unit_key,
        "dataset_revision": assignment.dataset_revision,
        "brief_version_id": str(assignment.brief_version_id),
        "blueprint_version_id": str(assignment.blueprint_version_id),
        "rubric_revision": assignment.rubric_revision,
        "package": json.loads(assignment.package_json),
        "state": state,
        "staleness": staleness,
        "not_complete_reason": assignment.not_complete_reason,
        "created_at": assignment.created_at.isoformat(),
        "concluded_at": assignment.concluded_at.isoformat() if assignment.concluded_at else None,
        "evidence_history": history,
        "rubric_sheet": rubric.rubric_sheet(),
    }
