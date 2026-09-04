"""F016 T8 live evidence runner (owner-authorized 2026-09-04, "全部授权").

Runs against the REAL DeepSeek adapter with the real fastembed embedding
runtime: one live specialist journey (source analysis -> confirmed pair ->
plans generation through design/write/review, revising only if the reviewer
actually finds severe issues) plus the full F009 live re-baseline (all three
representative units x two passes under the new stage set). Data isolation:
the throwaway `lessoncanvas_test` database, truncated before and after.

Usage (from apps/backend, credentials via environment):
  DB_URL=... S3_KEY=... S3_SECRET=... S3_ENDPOINT=... DEEPSEEK_KEY=... \
  uv run python ../../specs/F016-specialist-role-expansion/live-runner.py
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

EVIDENCE_PATH = Path(__file__).parent / "live-evidence.json"
BACKEND_SRC = Path(__file__).parents[2] / "apps/backend/src"

os.environ["LESSONCANVAS_MODEL_ADAPTER"] = "deepseek"
os.environ["LESSONCANVAS_TASKS_EAGER"] = "true"
os.environ["LESSONCANVAS_CHECKPOINT_BACKEND"] = "memory"
os.environ.setdefault("LESSONCANVAS_EMBEDDING_ADAPTER", "fastembed")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
if os.environ.get("DB_URL"):
    os.environ["LESSONCANVAS_DATABASE_URL"] = os.environ["DB_URL"]
if os.environ.get("DEEPSEEK_KEY"):
    os.environ["LESSONCANVAS_DEEPSEEK_API_KEY"] = os.environ["DEEPSEEK_KEY"]
if os.environ.get("S3_KEY"):
    os.environ["LESSONCANVAS_S3_ACCESS_KEY"] = os.environ["S3_KEY"]
if os.environ.get("S3_SECRET"):
    os.environ["LESSONCANVAS_S3_SECRET_KEY"] = os.environ["S3_SECRET"]
if os.environ.get("S3_ENDPOINT"):
    os.environ["LESSONCANVAS_S3_ENDPOINT_URL"] = os.environ["S3_ENDPOINT"]

sys.path.insert(0, str(BACKEND_SRC))

from lessoncanvas.modules.technical_evaluation.dataset import cached_dataset  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from lessoncanvas.db import SessionLocal  # noqa: E402
from lessoncanvas.models import (  # noqa: E402
    Project,
    SourceAnalysis,
    TraceEvent,
    Workspace,
)
from lessoncanvas.modules.artifact_production.graph import execute_generation  # noqa: E402
from lessoncanvas.modules.run_orchestration import service as run_service  # noqa: E402
from lessoncanvas.modules.technical_evaluation import harness  # noqa: E402
from lessoncanvas.modules.technical_evaluation.service import (  # noqa: E402
    create_evaluation,
    execute_evaluation,
)
from lessoncanvas.settings import get_settings  # noqa: E402

TABLES = (
    "product_validation_evidence, product_validation_assignments, "
    "technical_evaluation_results, technical_evaluations, "
    "memory_project_overrides, memory_proposals, memory_records, memory_passes, "
    "retained_security_events, deletion_residuals, rate_window_counters, "
    "run_events, exercise_artifacts, slide_deck_artifacts, lesson_plan_artifacts, "
    "generation_runs, delivery_exports, alignment_overrides, trace_events, "
    "interaction_messages, discovery_runs, "
    "blueprint_drafts, blueprint_versions, source_chunks, source_analyses, "
    "sources, brief_versions, brief_drafts, audit_events, quota_counters, "
    "projects, workspaces, account_deletion_events"
)


def truncate(session) -> None:
    session.execute(text(f"TRUNCATE TABLE {TABLES}"))
    session.commit()


def stage_summary(run_id) -> dict:
    """Aggregate the specialist-stage traces of one run (honest observation)."""

    session = SessionLocal()
    try:
        events = (
            session.scalars(
                select(TraceEvent).where(TraceEvent.run_id == run_id)
            ).all()
        )
        stages: dict[str, dict] = {}
        for event in events:
            if not event.event_type.startswith("model.generation_"):
                continue
            entry = stages.setdefault(
                event.event_type,
                {"count": 0, "latency_ms_total": 0, "cost_usd_total": 0.0, "tokens_recorded": 0},
            )
            entry["count"] += 1
            entry["latency_ms_total"] += event.latency_ms or 0
            entry["cost_usd_total"] += event.cost_usd or 0.0
            if event.prompt_tokens is not None:
                entry["tokens_recorded"] += 1
        return stages
    finally:
        session.close()


def live_journey(unit) -> dict:
    session = SessionLocal()
    try:
        workspace = Workspace(subject=f"f016-live-{uuid.uuid4().hex}")
        session.add(workspace)
        session.flush()
        project = Project(workspace_id=workspace.id, name="F016 live specialist journey")
        session.add(project)
        session.commit()

        from lessoncanvas.adapters.storage import StorageAdapter

        uploaded = harness.upload_unit_sources(
            session, StorageAdapter(), workspace.id, project.id, unit
        )
        session.commit()

        analyses = session.scalars(
            select(SourceAnalysis).where(SourceAnalysis.project_id == project.id)
        ).all()
        analysis_records = [
            {
                "source": str(row.source_id)[:8],
                "status": row.status,
                "model": row.model,
                "latency_ms": row.latency_ms,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "cost_usd": row.cost_usd,
                "topics": (json.loads(row.payload_json or "{}").get("topics") or [])[:3],
                "key_passages": len(
                    json.loads(row.payload_json or "{}").get("key_passages") or []
                ),
            }
            for row in analyses
        ]

        started = time.monotonic()
        brief_id, blueprint_id, interview_ids = harness.reach_confirmed_pair(
            session, StorageAdapter(), workspace.id, project.id, unit
        )
        run, _created = run_service.start_generation(session, workspace.id, project.id)
        session.commit()
        status = execute_generation(str(run.id))
        elapsed = int((time.monotonic() - started) * 1000)
        session.expire_all()

        artifacts = run_service.artifacts_of(session, run.id)
        artifact_records = [
            {
                "lesson_index": a.lesson_index,
                "status": a.status,
                "design_status": a.design_status,
                "design_objectives": len(
                    json.loads(a.design_json or "{}").get("objective_ids") or []
                ),
                "design_activities": len(
                    json.loads(a.design_json or "{}").get("activities") or []
                ),
                "review_rounds": a.review_rounds,
                "review_outcome": a.review_outcome,
                "review_findings": len(json.loads(a.review_findings_json or "[]")),
                "failure_reason": a.failure_reason,
            }
            for a in artifacts
        ]
        return {
            "unit_key": unit.unit_key,
            "elapsed_ms": elapsed,
            "sources_uploaded": len(uploaded),
            "source_analyses": analysis_records,
            "run_status": status,
            "model_calls": run.model_calls,
            "model_call_cap": run.model_call_cap,
            "artifacts": artifact_records,
            "stage_traces": stage_summary(run.id),
        }
    finally:
        session.close()


def f009_rebaseline() -> list[dict]:
    bundle = cached_dataset()
    records: list[dict] = []
    session = SessionLocal()
    try:
        workspace = Workspace(subject=f"f016-f009-live-{uuid.uuid4().hex}")
        session.add(workspace)
        session.flush()
        project = Project(workspace_id=workspace.id, name="F016 F009 live re-baseline")
        session.add(project)
        session.commit()
    finally:
        session.close()

    for unit_key in bundle.units:
        for pass_index in (1, 2):
            session = SessionLocal()
            try:
                evaluation, _created = create_evaluation(
                    session,
                    session.get(Workspace, workspace.id),
                    project.id,
                    unit_key,
                    pass_index,
                    "live",
                    "full_pipeline",
                )
                session.commit()
                evaluation_id = evaluation.id
            finally:
                session.close()

            started = time.monotonic()
            status = execute_evaluation(evaluation_id)
            elapsed = int((time.monotonic() - started) * 1000)

            session = SessionLocal()
            try:
                from lessoncanvas.models import TechnicalEvaluation

                evaluation = session.get(TechnicalEvaluation, evaluation_id)
                from lessoncanvas.models import TechnicalEvaluationResult
                from lessoncanvas.modules.technical_evaluation import criteria as crit

                results = (
                    session.scalars(
                        select(TechnicalEvaluationResult).where(
                            TechnicalEvaluationResult.evaluation_id == evaluation_id
                        )
                    ).all()
                )
                records.append(
                    {
                        "unit_key": unit_key,
                        "pass_index": pass_index,
                        "status": status,
                        "overall_outcome": evaluation.overall_outcome,
                        "elapsed_ms": elapsed,
                        "model_config": json.loads(evaluation.model_config_json),
                        "source_analysis_state": json.loads(
                            evaluation.source_analysis_state_json or "{}"
                        ),
                        "criteria": [
                            {
                                "key": r.criterion_key,
                                "outcome": r.outcome,
                            }
                            for r in results
                            if r.classification == crit.BLOCKING
                        ],
                    }
                )
            finally:
                session.close()
    return records


def main() -> int:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise SystemExit("DEEPSEEK key not configured")

    session = SessionLocal()
    truncate(session)
    session.close()

    bundle = cached_dataset()
    evidence: dict = {
        "feature": "F016",
        "scenario": "TS-022 live specialist journey + full F009 live re-baseline",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "adapter": "deepseek",
        "model": settings.deepseek_model,
        "embedding_adapter": settings.embedding_adapter,
        "environment": "isolated lessoncanvas_test database; truncated after run",
        "units": sorted(bundle.units.keys()),
    }

    print("[1/2] live specialist journey (travelling-around)...", flush=True)
    evidence["journey"] = live_journey(bundle.units["travelling-around"])

    print("[2/2] F009 live re-baseline (3 units x 2 passes)...", flush=True)
    evidence["f009_rebaseline"] = f009_rebaseline()

    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"evidence written: {EVIDENCE_PATH}")

    session = SessionLocal()
    truncate(session)
    session.close()
    print("lessoncanvas_test truncated after run", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
