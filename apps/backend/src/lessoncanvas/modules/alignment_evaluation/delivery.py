"""F008 delivery: version-bound export records with byte-identical artifacts,
labelled metadata, a printable-report snapshot, and idempotent creation
(Spec D4/D8). Exports never re-render or re-bill artifacts."""

import hashlib
import io
import json
import uuid
import zipfile

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lessoncanvas.models import AuditEvent, DeliveryExport, utcnow
from lessoncanvas.modules.alignment_evaluation import service as alignment_service
from lessoncanvas.modules.run_orchestration import service as run_service

LABELS = ("draft", "validated")

FILE_LAYOUT = {
    "lesson_plan": "lesson-plans/lesson-{index:02d}.docx",
    "slide_deck": "slide-decks/lesson-{index:02d}.pptx",
}


class ExportBlockedError(Exception):
    def __init__(self, blocking_findings: list[dict]) -> None:
        super().__init__("validated export is blocked by unresolved severe findings")
        self.blocking_findings = blocking_findings


class ExportBuildError(Exception):
    pass


def _manifest(alignment: dict) -> dict:
    """Exportable members: complete members plus overridden disputed members
    with downloadable files. Excluded members are listed as gaps."""

    findings = {finding["key"]: finding for finding in alignment["findings"]}
    entries: list[dict] = []
    gaps: list[dict] = []
    for lesson in alignment["lessons"]:
        index = lesson["lesson_index"]
        for family in alignment_service.FAMILIES:
            member = lesson["members"][family]
            if member["state"] == "complete":
                include = True
            elif member["state"] == "failed" and member.get("files"):
                finding = findings.get(f"conflict:{family}:{index}:validation_failed")
                include = bool(finding and finding.get("resolved"))
            else:
                include = False
            if not include:
                gaps.append(
                    {
                        "family": family,
                        "lesson_index": index,
                        "reason": member["state"],
                    }
                )
                continue
            files = []
            for file_info in member["files"]:
                if family == "exercise":
                    path = (
                        f"exercises/lesson-{index:02d}-{file_info['role']}.docx"
                    )
                else:
                    path = FILE_LAYOUT[family].format(index=index)
                files.append(
                    {
                        "path": path,
                        "object_key": file_info["object_key"],
                        "checksum": file_info["checksum"],
                    }
                )
            entries.append(
                {
                    "family": family,
                    "lesson_index": index,
                    "provenance": member["provenance"],
                    "artifact_id": member.get("artifact_id"),
                    "files": files,
                }
            )
    return {"entries": entries, "gaps": gaps}


def manifest_digest(manifest: dict) -> str:
    return hashlib.sha256(
        json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def create_export(
    session: Session,
    storage,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    label: str,
    actor: str,
) -> DeliveryExport:
    if label not in LABELS:
        raise ValueError(f"unknown export label: {label}")

    alignment = alignment_service.compute_alignment(session, project_id)
    if label == "validated" and alignment["technical_status"] != "validated":
        blocking = [
            {"key": f["key"], "title": f["title"], "recovery_action": f["recovery_action"]}
            for f in alignment["findings"]
            if f["severity"] == "severe" and not f["resolved"]
        ]
        raise ExportBlockedError(blocking)

    brief_version_id = uuid.UUID(alignment["brief_version_id"])
    blueprint_version_id = uuid.UUID(alignment["blueprint_version_id"])
    manifest = _manifest(alignment)
    digest = manifest_digest(manifest)

    def _find_existing() -> DeliveryExport | None:
        return session.scalar(
            select(DeliveryExport).where(
                DeliveryExport.project_id == project_id,
                DeliveryExport.brief_version_id == brief_version_id,
                DeliveryExport.blueprint_version_id == blueprint_version_id,
                DeliveryExport.label == label,
                DeliveryExport.manifest_digest == digest,
            )
        )

    existing = _find_existing()
    if existing is not None and existing.status in ("building", "ready"):
        return existing

    if existing is not None:
        # A failed export with an unchanged manifest is retried in place:
        # identity stays one row per (pair, label, manifest) (Spec D8).
        export = existing
        export.status = "building"
        export.failure_reason = None
        export.created_by = actor
        session.commit()
    else:
        export = DeliveryExport(
            project_id=project_id,
            workspace_id=workspace_id,
            brief_version_id=brief_version_id,
            blueprint_version_id=blueprint_version_id,
            label=label,
            manifest_json=json.dumps(manifest, ensure_ascii=False),
            manifest_digest=digest,
            status="building",
            created_by=actor,
        )
        session.add(export)
        try:
            session.commit()
        except IntegrityError:
            # Concurrent duplicate create converged on one record (Spec D8).
            session.rollback()
            existing = _find_existing()
            if existing is not None and existing.status in ("building", "ready"):
                return existing
            if existing is not None:
                export = existing
                export.status = "building"
                export.failure_reason = None
                export.created_by = actor
                session.commit()
            else:
                raise

    try:
        package = _build_package(storage, manifest, alignment, label)
        package_key = f"exports/{export.id}/package.zip"
        storage.put(package_key, package)

        report = dict(alignment)
        report["export"] = {
            "id": str(export.id),
            "label": label,
            "created_at": export.created_at.isoformat(),
            "manifest": manifest,
        }
        report_key = f"exports/{export.id}/report.json"
        storage.put(report_key, json.dumps(report, ensure_ascii=False).encode())

        # A version switch during the build must not deliver a mixed package.
        current_brief = run_service.current_brief_version(session, project_id)
        current_blueprint = run_service.current_blueprint_version(session, project_id)
        if (
            current_brief is None
            or current_brief.id != brief_version_id
            or current_blueprint is None
            or current_blueprint.id != blueprint_version_id
        ):
            export.status = "failed"
            export.failure_reason = "confirmed version pair changed during export"
            session.commit()
            raise ExportBuildError(export.failure_reason)

        export.package_object_key = package_key
        export.report_object_key = report_key
        export.status = "ready"
        export.ready_at = utcnow()
        session.add(
            AuditEvent(
                workspace_id=workspace_id,
                actor=actor,
                action="delivery.export.created",
                target_type="delivery_export",
                target_id=str(export.id),
            )
        )
        session.commit()
    except ExportBuildError:
        raise
    except Exception as err:  # noqa: BLE001 - a partial package must never pass
        session.rollback()
        export = session.get(DeliveryExport, export.id)
        export.status = "failed"
        export.failure_reason = f"package build failed: {err}"[:500]
        session.commit()
        raise ExportBuildError(export.failure_reason) from err
    return export


def _build_package(storage, manifest: dict, alignment: dict, label: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in manifest["entries"]:
            for file_info in entry["files"]:
                content = storage.get(file_info["object_key"])
                if file_info["checksum"]:
                    actual = hashlib.sha256(content).hexdigest()
                    if actual != file_info["checksum"]:
                        raise ExportBuildError(
                            f"checksum mismatch for {file_info['path']}"
                        )
                archive.writestr(file_info["path"], content)
        metadata = {
            "label": label,
            "brief_version": alignment["brief_version"],
            "blueprint_version": alignment["blueprint_version"],
            "technical_status": alignment["technical_status"],
            "product_validation_status": alignment["product_validation_status"],
            "gaps": manifest["gaps"],
            "manifest": manifest,
            "overrides": alignment["overrides"],
        }
        archive.writestr(
            "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2)
        )
    return buffer.getvalue()
