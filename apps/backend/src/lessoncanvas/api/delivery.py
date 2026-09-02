"""F008 delivery API: owner-authorized, idempotent export creation (draft or
validated), export history, authorized ZIP download, and the printable-report
snapshot (Spec D4/D8)."""

import json
import uuid

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select

from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import (
    NotFoundError,
    ProviderTransientError,
    RequirementError,
)
from lessoncanvas.models import BlueprintVersion, BriefVersion, DeliveryExport
from lessoncanvas.modules.alignment_evaluation import delivery
from lessoncanvas.modules.alignment_evaluation.service import MissingPairError
from lessoncanvas.modules.identity_workspace import service as iw_service
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import get_owned_project
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/projects/{project_id}/delivery", tags=["delivery"])


class ExportIn(BaseModel):
    label: str


class ExportOut(BaseModel):
    id: str
    label: str
    status: str
    brief_version: int
    blueprint_version: int
    manifest_digest: str
    failure_reason: str | None = None
    created_at: str
    ready_at: str | None = None
    download_available: bool


def _owned(session, workspace, project_id, *, sample_read: bool = False) -> None:
    try:
        get_owned_project(session, workspace, project_id, allow_sample_read=sample_read)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


def _export_out(session, export: DeliveryExport) -> ExportOut:
    brief_version = session.get(BriefVersion, export.brief_version_id)
    blueprint_version = session.get(BlueprintVersion, export.blueprint_version_id)
    return ExportOut(
        id=str(export.id),
        label=export.label,
        status=export.status,
        brief_version=brief_version.version if brief_version else 0,
        blueprint_version=blueprint_version.version if blueprint_version else 0,
        manifest_digest=export.manifest_digest,
        failure_reason=export.failure_reason,
        created_at=export.created_at.isoformat(),
        ready_at=export.ready_at.isoformat() if export.ready_at else None,
        download_available=export.status == "ready",
    )


def _export_or_404(session, workspace, project_id, export_id) -> DeliveryExport:
    _owned(session, workspace, project_id)
    export = session.scalar(
        select(DeliveryExport).where(
            DeliveryExport.id == export_id, DeliveryExport.project_id == project_id
        )
    )
    if export is None:
        raise NotFoundError("export not found")
    return export


@router.post("/exports", response_model=ExportOut, status_code=201)
def create_export(
    project_id: uuid.UUID,
    payload: ExportIn,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    _owned(session, workspace, project_id)
    if payload.label not in ("draft", "validated"):
        raise RequirementError(
            "label must be draft or validated", {"label": payload.label}
        )
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
    try:
        export = delivery.create_export(
            session, storage, workspace.id, project_id, payload.label, workspace.subject
        )
    except MissingPairError as err:
        raise RequirementError(
            "confirmed brief and blueprint versions are required before export",
            {"gate": "confirmed_pair"},
        ) from err
    except delivery.ExportBlockedError as err:
        raise RequirementError(
            "validated export is blocked until severe findings are corrected or overridden",
            {"blocking_findings": err.blocking_findings},
        ) from err
    except delivery.ExportBuildError as err:
        raise ProviderTransientError(
            f"package build failed: {err}", {"reason": str(err)}
        ) from err
    return _export_out(session, export)


@router.get("/exports", response_model=list[ExportOut])
def list_exports(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    _owned(session, workspace, project_id, sample_read=True)
    exports = list(
        session.scalars(
            select(DeliveryExport)
            .where(DeliveryExport.project_id == project_id)
            .order_by(DeliveryExport.created_at.desc())
        )
    )
    return [_export_out(session, export) for export in exports]


@router.get("/exports/{export_id}/download")
def download(
    project_id: uuid.UUID,
    export_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    export = _export_or_404(session, workspace, project_id, export_id)
    if export.status != "ready" or not export.package_object_key:
        raise NotFoundError("export package not found")
    try:
        content = StorageAdapter(bucket=get_settings().s3_bucket_artifacts).get(
            export.package_object_key
        )
    except Exception as err:  # noqa: BLE001 - storage miss must not fake success
        raise NotFoundError("export package not found") from err
    iw_service.audit_download(
        session, workspace.id, workspace.subject, "delivery_export", export.id
    )
    session.commit()
    filename = f"lessoncanvas-{export.label}-export-{str(export.id)[:8]}.zip"
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports/{export_id}/report")
def export_report(
    project_id: uuid.UUID,
    export_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    export = _export_or_404(session, workspace, project_id, export_id)
    if export.status != "ready" or not export.report_object_key:
        raise NotFoundError("export report not found")
    try:
        content = StorageAdapter(bucket=get_settings().s3_bucket_artifacts).get(
            export.report_object_key
        )
    except Exception as err:  # noqa: BLE001 - storage miss must not fake success
        raise NotFoundError("export report not found") from err
    return json.loads(content)
