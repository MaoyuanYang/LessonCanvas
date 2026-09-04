import uuid

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.models import (
    AccountDeletionEvent,
    AlignmentOverride,
    AuditEvent,
    BlueprintDraft,
    BlueprintVersion,
    BriefDraft,
    BriefVersion,
    DeletionResidual,
    DeliveryExport,
    DiscoveryRun,
    ExerciseArtifact,
    GenerationRun,
    InteractionMessage,
    LessonPlanArtifact,
    MemoryPass,
    MemoryProjectOverride,
    MemoryProposal,
    MemoryRecord,
    ProductValidationAssignment,
    ProductValidationEvidence,
    Project,
    RateWindowCounter,
    RetainedSecurityEvent,
    RunEvent,
    SlideDeckArtifact,
    Source,
    SourceAnalysis,
    SourceChunk,
    TechnicalEvaluation,
    TechnicalEvaluationResult,
    TraceEvent,
    Workspace,
)
from lessoncanvas.settings import get_settings


class DeletionFailedError(Exception):
    pass


# F011 D5 completeness verification: every table that can still reference the
# deleted project must read zero after the cascade. The projects row itself is
# excluded: it is deleted right after verification on success, and on failure
# its `deleting` status is the visible repair marker, not a residual.
PROJECT_SCOPED_TABLES = (
    Source,
    SourceAnalysis,
    GenerationRun,
    DeliveryExport,
    AlignmentOverride,
    TechnicalEvaluation,
    ProductValidationAssignment,
    BlueprintDraft,
    BlueprintVersion,
    DiscoveryRun,
    BriefDraft,
    BriefVersion,
    MemoryProjectOverride,
)

CHECKPOINT_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")


def _artifact_storage() -> StorageAdapter:
    return StorageAdapter(bucket=get_settings().s3_bucket_artifacts)


def _storage_for(store: str) -> StorageAdapter:
    if store == "artifacts":
        return _artifact_storage()
    return StorageAdapter()


def _repair_residuals(session: Session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> None:
    """F011 D5 repair step: converge objects a prior failed pass left behind.

    Residual rows are dropped when their object is verifiably gone (repaired
    now or earlier); table residuals are dropped because the fresh verification
    below re-records anything still present. Unrepairable objects keep their
    rows so the deletion stays visibly incomplete.
    """
    residuals = session.scalars(
        select(DeletionResidual).where(DeletionResidual.project_id == project_id)
    ).all()
    for residual in residuals:
        if residual.object_key:
            store = _storage_for(residual.store)
            try:
                store.delete(residual.object_key)
            except Exception:
                if store.exists(residual.object_key):
                    continue  # still failing; keep the residual row
        session.delete(residual)
    _ = workspace_id
    session.flush()


def _record_residual(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    store: str,
    object_key: str | None = None,
    table_name: str | None = None,
) -> None:
    session.add(
        DeletionResidual(
            workspace_id=workspace_id,
            project_id=project_id,
            store=store,
            object_key=object_key,
            table_name=table_name,
        )
    )


def _delete_checkpoint_rows(session: Session, thread_ids: list[str]) -> None:
    """LangGraph checkpoint rows are keyed by thread_id = discovery run id.

    The tables are created lazily by PostgresSaver.setup(); when the tables do
    not exist (memory backend, fresh environment) there is nothing to delete.
    """
    if not thread_ids:
        return
    for table in CHECKPOINT_TABLES:
        registered = session.execute(
            text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}
        ).scalar()
        if not registered:
            continue
        session.execute(
            text(f"DELETE FROM {table} WHERE thread_id = ANY(:ids)"),  # noqa: S608
            {"ids": thread_ids},
        )


def _verify_project_removed(
    session: Session,
    storage: StorageAdapter,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    discovery_run_ids: list[uuid.UUID],
    generation_run_ids: list[uuid.UUID],
    artifact_keys: list[str],
) -> list[dict]:
    """Post-cascade completeness check; returns structured residual findings.

    Findings are store/table/key identifiers only — never content (Spec D5).
    """
    residuals: list[dict] = []
    for model in PROJECT_SCOPED_TABLES:
        count = (
            session.execute(
                select(func.count()).select_from(model).where(model.project_id == project_id)
            ).scalar_one()
            or 0
        )
        if count:
            residuals.append({"store": "postgres", "table_name": model.__tablename__})
    if discovery_run_ids:
        for model in (TraceEvent, InteractionMessage):
            count = (
                session.execute(
                    select(func.count())
                    .select_from(model)
                    .where(model.run_id.in_(discovery_run_ids))
                ).scalar_one()
                or 0
            )
            if count:
                residuals.append({"store": "postgres", "table_name": model.__tablename__})
    if generation_run_ids:
        for model in (TraceEvent, RunEvent):
            count = (
                session.execute(
                    select(func.count())
                    .select_from(model)
                    .where(model.run_id.in_(generation_run_ids))
                ).scalar_one()
                or 0
            )
            if count:
                residuals.append({"store": "postgres", "table_name": model.__tablename__})
    for table in CHECKPOINT_TABLES:
        registered = session.execute(
            text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}
        ).scalar()
        if not registered:
            continue
        count = session.execute(
            text(f"SELECT count(*) FROM {table} WHERE thread_id = ANY(:ids)"),  # noqa: S608
            {"ids": [str(run_id) for run_id in discovery_run_ids]},
        ).scalar()
        if count:
            residuals.append({"store": "postgres", "table_name": table})
    for key in storage.list_prefix(f"{workspace_id}/{project_id}/"):
        residuals.append({"store": "sources", "object_key": key})
    artifact_storage = _artifact_storage()
    for key in artifact_keys:
        if artifact_storage.exists(key):
            residuals.append({"store": "artifacts", "object_key": key})
    return residuals


def _residual_label(residual: dict) -> str:
    if residual.get("object_key"):
        return f"object:{residual['object_key']}"
    return f"table:{residual.get('table_name')}"


def delete_project_cascade(
    session, storage, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> None:
    project = session.get(Project, project_id)
    if project is None:
        return
    failures: list[str] = []

    # F011 D5: converge residuals recorded by a prior failed pass first.
    _repair_residuals(session, workspace_id, project_id)

    # F011 D5: capture identities before any delete; they drive checkpoint
    # cleanup and the post-cascade completeness verification.
    discovery_run_ids = [
        row.id
        for row in session.scalars(
            select(DiscoveryRun).where(DiscoveryRun.project_id == project_id)
        )
    ]
    generation_runs = session.scalars(
        select(GenerationRun).where(GenerationRun.project_id == project_id)
    ).all()
    generation_run_ids = [run.id for run in generation_runs]
    artifact_bucket_keys: list[str] = []

    sources = session.scalars(select(Source).where(Source.project_id == project_id)).all()
    for source in sources:
        if source.object_key:
            try:
                storage.delete(source.object_key)
            except Exception:
                failures.append(f"object:{source.object_key}")
                _record_residual(
                    session, workspace_id, project_id, "sources", object_key=source.object_key
                )
    session.execute(
        sql_delete(SourceAnalysis).where(
            SourceAnalysis.source_id.in_([s.id for s in sources] or [uuid.uuid4()])
        )
    )
    session.execute(
        sql_delete(SourceChunk).where(
            SourceChunk.source_id.in_([s.id for s in sources] or [uuid.uuid4()])
        )
    )
    session.execute(sql_delete(Source).where(Source.project_id == project_id))

    run_ids = discovery_run_ids
    if run_ids:
        session.execute(sql_delete(TraceEvent).where(TraceEvent.run_id.in_(run_ids)))
        session.execute(
            sql_delete(InteractionMessage).where(InteractionMessage.run_id.in_(run_ids))
        )

    if generation_runs:
        generation_run_ids = [run.id for run in generation_runs]
        artifact_keys = [
            key
            for (key,) in session.execute(
                select(LessonPlanArtifact.object_key).where(
                    LessonPlanArtifact.run_id.in_(generation_run_ids),
                    LessonPlanArtifact.object_key.is_not(None),
                )
            )
        ]
        artifact_keys += [
            key
            for (key,) in session.execute(
                select(SlideDeckArtifact.object_key).where(
                    SlideDeckArtifact.run_id.in_(generation_run_ids),
                    SlideDeckArtifact.object_key.is_not(None),
                )
            )
        ]
        artifact_keys += [
            key
            for (key,) in session.execute(
                select(ExerciseArtifact.exercise_object_key).where(
                    ExerciseArtifact.run_id.in_(generation_run_ids),
                    ExerciseArtifact.exercise_object_key.is_not(None),
                )
            )
        ]
        artifact_keys += [
            key
            for (key,) in session.execute(
                select(ExerciseArtifact.answer_object_key).where(
                    ExerciseArtifact.run_id.in_(generation_run_ids),
                    ExerciseArtifact.answer_object_key.is_not(None),
                )
            )
        ]
        artifact_bucket_keys += artifact_keys
        artifact_storage = _artifact_storage()
        for key in artifact_keys:
            try:
                artifact_storage.delete(key)
            except Exception:
                failures.append(f"object:{key}")
                _record_residual(
                    session, workspace_id, project_id, "artifacts", object_key=key
                )
        session.execute(sql_delete(TraceEvent).where(TraceEvent.run_id.in_(generation_run_ids)))
        session.execute(sql_delete(RunEvent).where(RunEvent.run_id.in_(generation_run_ids)))
        session.execute(
            sql_delete(SlideDeckArtifact).where(
                SlideDeckArtifact.run_id.in_(generation_run_ids)
            )
        )
        session.execute(
            sql_delete(ExerciseArtifact).where(
                ExerciseArtifact.run_id.in_(generation_run_ids)
            )
        )
        session.execute(
            sql_delete(LessonPlanArtifact).where(LessonPlanArtifact.run_id.in_(generation_run_ids))
        )
        session.execute(sql_delete(GenerationRun).where(GenerationRun.id.in_(generation_run_ids)))

    export_keys = [
        key
        for (key,) in session.execute(
            select(DeliveryExport.package_object_key).where(
                DeliveryExport.project_id == project_id,
                DeliveryExport.package_object_key.is_not(None),
            )
        )
    ]
    export_keys += [
        key
        for (key,) in session.execute(
            select(DeliveryExport.report_object_key).where(
                DeliveryExport.project_id == project_id,
                DeliveryExport.report_object_key.is_not(None),
            )
        )
    ]
    artifact_bucket_keys += export_keys
    if export_keys:
        export_storage = _artifact_storage()
        for key in export_keys:
            try:
                export_storage.delete(key)
            except Exception:
                failures.append(f"object:{key}")
                _record_residual(session, workspace_id, project_id, "artifacts", object_key=key)

    session.execute(
        sql_delete(DeliveryExport).where(DeliveryExport.project_id == project_id)
    )
    session.execute(
        sql_delete(AlignmentOverride).where(AlignmentOverride.project_id == project_id)
    )

    evaluation_ids = session.scalars(
        select(TechnicalEvaluation.id).where(TechnicalEvaluation.project_id == project_id)
    ).all()
    if evaluation_ids:
        session.execute(
            sql_delete(TechnicalEvaluationResult).where(
                TechnicalEvaluationResult.evaluation_id.in_(evaluation_ids)
            )
        )
    session.execute(
        sql_delete(TechnicalEvaluation).where(TechnicalEvaluation.project_id == project_id)
    )

    assignment_ids = session.scalars(
        select(ProductValidationAssignment.id).where(
            ProductValidationAssignment.project_id == project_id
        )
    ).all()
    if assignment_ids:
        evidence_document_keys = [
            key
            for (key,) in session.execute(
                select(ProductValidationEvidence.document_object_key).where(
                    ProductValidationEvidence.assignment_id.in_(assignment_ids),
                    ProductValidationEvidence.document_object_key.is_not(None),
                )
            )
        ]
        if evidence_document_keys:
            evidence_storage = _artifact_storage()
            for key in evidence_document_keys:
                try:
                    evidence_storage.delete(key)
                except Exception:
                    failures.append(f"object:{key}")
                    _record_residual(
                        session, workspace_id, project_id, "artifacts", object_key=key
                    )
            artifact_bucket_keys += evidence_document_keys
        session.execute(
            sql_delete(ProductValidationEvidence).where(
                ProductValidationEvidence.assignment_id.in_(assignment_ids)
            )
        )
    session.execute(
        sql_delete(ProductValidationAssignment).where(
            ProductValidationAssignment.project_id == project_id
        )
    )

    session.execute(sql_delete(BlueprintDraft).where(BlueprintDraft.project_id == project_id))
    session.execute(sql_delete(BlueprintVersion).where(BlueprintVersion.project_id == project_id))
    session.execute(sql_delete(DiscoveryRun).where(DiscoveryRun.project_id == project_id))
    session.execute(sql_delete(BriefDraft).where(BriefDraft.project_id == project_id))
    session.execute(sql_delete(BriefVersion).where(BriefVersion.project_id == project_id))
    # F013: project deletion removes this project's applicability overrides;
    # workspace memory records survive (workspace-scoped, Spec D2) with their
    # evidence references nulled by the SET NULL foreign keys above.
    session.execute(
        sql_delete(MemoryProjectOverride).where(MemoryProjectOverride.project_id == project_id)
    )

    # F011 D5: checkpoint rows share the project's deletion boundary, and the
    # cascade is not complete while any governed store still holds owned data.
    _delete_checkpoint_rows(session, [str(run_id) for run_id in discovery_run_ids])
    for residual in _verify_project_removed(
        session,
        storage,
        workspace_id,
        project_id,
        discovery_run_ids,
        generation_run_ids,
        artifact_bucket_keys,
    ):
        failures.append(_residual_label(residual))
        _record_residual(
            session,
            workspace_id,
            project_id,
            residual["store"],
            object_key=residual.get("object_key"),
            table_name=residual.get("table_name"),
        )
    session.flush()

    if failures:
        project.status = "deleting"
        session.add(
            AuditEvent(
                workspace_id=workspace_id,
                actor="system",
                action="project.deletion_failed",
                target_type="project",
                target_id=str(project_id),
            )
        )
        session.flush()
        raise DeletionFailedError(",".join(failures))

    session.delete(project)
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor="system",
            action="project.deleted",
            target_type="project",
            target_id=str(project_id),
        )
    )
    # F011 D4(b): the content-free retained security ledger survives workspace
    # deletion; this row records the deletion itself, never content.
    session.add(
        RetainedSecurityEvent(
            workspace_id=workspace_id,
            action="project.deleted",
        )
    )
    # Complete deletion leaves no residual markers behind.
    session.execute(
        sql_delete(DeletionResidual).where(DeletionResidual.project_id == project_id)
    )
    session.flush()


def delete_workspace_cascade(session, storage, workspace: Workspace) -> None:
    projects = session.scalars(select(Project).where(Project.workspace_id == workspace.id)).all()
    failures: list[str] = []
    for project in projects:
        try:
            delete_project_cascade(session, storage, workspace.id, project.id)
        except DeletionFailedError as error:
            failures.append(str(error))
    if failures:
        raise DeletionFailedError(",".join(failures))
    # Ephemeral rate-window counters are workspace-scoped quota data; they go
    # with the account. The content-free retained security ledger (F011 D4(b))
    # has no workspace foreign key and deliberately survives this delete.
    session.execute(
        sql_delete(RateWindowCounter).where(RateWindowCounter.workspace_id == workspace.id)
    )
    session.execute(sql_delete(AuditEvent).where(AuditEvent.workspace_id == workspace.id))
    # F013: teacher memory follows the workspace boundary (ADR-0005);
    # proposals reference passes, overrides reference records.
    session.execute(
        sql_delete(MemoryProjectOverride).where(MemoryProjectOverride.workspace_id == workspace.id)
    )
    session.execute(
        sql_delete(MemoryProposal).where(MemoryProposal.workspace_id == workspace.id)
    )
    session.execute(
        sql_delete(MemoryPass).where(MemoryPass.workspace_id == workspace.id)
    )
    session.execute(
        sql_delete(MemoryRecord).where(MemoryRecord.workspace_id == workspace.id)
    )
    session.add(RetainedSecurityEvent(workspace_id=workspace.id, action="workspace.purged"))
    session.execute(
        sql_delete(DeletionResidual).where(DeletionResidual.workspace_id == workspace.id)
    )
    session.execute(sql_delete(Workspace).where(Workspace.id == workspace.id))
    session.flush()


def record_account_deletion(session, subject: str, status: str, detail: str | None) -> None:
    session.add(AccountDeletionEvent(subject=subject, status=status, detail=detail))
    session.flush()
