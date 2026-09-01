import uuid

from sqlalchemy import delete as sql_delete
from sqlalchemy import select

from lessoncanvas.models import (
    AccountDeletionEvent,
    AlignmentOverride,
    AuditEvent,
    BlueprintDraft,
    BlueprintVersion,
    BriefDraft,
    BriefVersion,
    DeliveryExport,
    DiscoveryRun,
    ExerciseArtifact,
    GenerationRun,
    InteractionMessage,
    LessonPlanArtifact,
    ProductValidationAssignment,
    ProductValidationEvidence,
    Project,
    RunEvent,
    SlideDeckArtifact,
    Source,
    SourceChunk,
    TechnicalEvaluation,
    TechnicalEvaluationResult,
    TraceEvent,
    Workspace,
)


class DeletionFailedError(Exception):
    pass


def delete_project_cascade(
    session, storage, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> None:
    project = session.get(Project, project_id)
    if project is None:
        return
    failures: list[str] = []

    sources = session.scalars(select(Source).where(Source.project_id == project_id)).all()
    for source in sources:
        if source.object_key:
            try:
                storage.delete(source.object_key)
            except Exception:
                failures.append(f"object:{source.object_key}")
    session.execute(
        sql_delete(SourceChunk).where(
            SourceChunk.source_id.in_([s.id for s in sources] or [uuid.uuid4()])
        )
    )
    session.execute(sql_delete(Source).where(Source.project_id == project_id))

    run_ids = [
        r.id
        for r in session.scalars(select(DiscoveryRun).where(DiscoveryRun.project_id == project_id))
    ]
    if run_ids:
        session.execute(sql_delete(TraceEvent).where(TraceEvent.run_id.in_(run_ids)))
        session.execute(
            sql_delete(InteractionMessage).where(InteractionMessage.run_id.in_(run_ids))
        )

    generation_runs = session.scalars(
        select(GenerationRun).where(GenerationRun.project_id == project_id)
    ).all()
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
        from lessoncanvas.adapters.storage import StorageAdapter
        from lessoncanvas.settings import get_settings

        artifact_storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
        for key in artifact_keys:
            try:
                artifact_storage.delete(key)
            except Exception:
                failures.append(f"object:{key}")
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
    if export_keys:
        from lessoncanvas.adapters.storage import StorageAdapter
        from lessoncanvas.settings import get_settings

        export_storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
        for key in export_keys:
            try:
                export_storage.delete(key)
            except Exception:
                failures.append(f"object:{key}")

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
            from lessoncanvas.adapters.storage import StorageAdapter
            from lessoncanvas.settings import get_settings

            evidence_storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
            for key in evidence_document_keys:
                try:
                    evidence_storage.delete(key)
                except Exception:
                    failures.append(f"object:{key}")
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
    session.execute(sql_delete(AuditEvent).where(AuditEvent.workspace_id == workspace.id))
    session.execute(sql_delete(Workspace).where(Workspace.id == workspace.id))
    session.flush()


def record_account_deletion(session, clerk_user_id: str, status: str, detail: str | None) -> None:
    session.add(AccountDeletionEvent(clerk_user_id=clerk_user_id, status=status, detail=detail))
    session.flush()
