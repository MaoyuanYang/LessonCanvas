"""F014 TS-026 live re-baseline runner (owner-authorized 2026-09-03).

Runs inside the deployed api container: one fresh eval workspace/project per
pass, live DeepSeek + fastembed via the deployed worker, sequential passes.
Prints one JSON evidence document to stdout.
"""

import json
import sys
import time
import uuid

from sqlalchemy import select

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import Project, TechnicalEvaluation, TraceEvent, Workspace
from lessoncanvas.modules.technical_evaluation import service as te_service

UNITS = ["cultural-heritage", "natural-disasters", "travelling-around"]
PASSES = [1, 2]
PER_PASS_TIMEOUT = 40 * 60


def retrieval_samples(session, evaluation) -> list[dict]:
    try:
        run_ids = [uuid.UUID(value) for value in json.loads(evaluation.run_ids_json or "[]")]
    except ValueError:
        return []
    samples = []
    for run_id in run_ids:
        events = session.scalars(
            select(TraceEvent)
            .where(TraceEvent.run_id == run_id, TraceEvent.event_type == "retrieval.semantic_search")
            .order_by(TraceEvent.created_at)
        ).all()
        for event in events:
            payload = json.loads(event.payload_json)
            samples.append(
                {
                    "family": payload.get("family"),
                    "purpose": payload.get("purpose"),
                    "lesson_index": payload.get("lesson_index"),
                    "query": payload.get("query"),
                    "hit_count": payload.get("hit_count"),
                    "excluded_count": payload.get("excluded_count"),
                    "grounding_state": payload.get("grounding_state"),
                    "top_hits": [
                        {"filename": hit.get("filename"), "position": hit.get("position"),
                         "similarity": hit.get("similarity")}
                        for hit in payload.get("hits", [])[:3]
                    ],
                }
            )
    return samples[:24]


def run_pass(session, unit: str, pass_index: int) -> dict:
    workspace = Workspace(subject=f"lessoncanvas-eval-f014-{unit}-p{pass_index}-{uuid.uuid4().hex[:8]}")
    session.add(workspace)
    session.flush()
    project = Project(workspace_id=workspace.id, name=f"F014 重基线 {unit} p{pass_index}")
    session.add(project)
    session.commit()
    evaluation, created = te_service.create_evaluation(
        session, workspace, project.id, unit, pass_index, "live", "full_pipeline"
    )
    session.commit()
    entry = {
        "unit_key": unit,
        "pass_index": pass_index,
        "evaluation_id": str(evaluation.id),
        "created": created,
        "model_config": json.loads(evaluation.model_config_json),
        "memory_state": json.loads(evaluation.memory_state_json or "null"),
    }
    deadline = time.monotonic() + PER_PASS_TIMEOUT
    while time.monotonic() < deadline:
        session.expire_all()
        evaluation = session.get(TechnicalEvaluation, evaluation.id)
        if evaluation.status in ("completed", "provider_unavailable", "failed"):
            break
        time.sleep(15)
    evaluation = session.get(TechnicalEvaluation, evaluation.id)
    entry["status"] = evaluation.status
    entry["overall_outcome"] = evaluation.overall_outcome
    entry["failure_reason"] = evaluation.failure_reason
    results = te_service._results_of(session, evaluation.id)
    entry["blocking_failures"] = [
        {"criterion": row.criterion_key, "outcome": row.outcome}
        for row in results
        if row.classification == "blocking" and row.outcome not in ("pass", None)
    ]
    entry["criteria"] = [
        {"criterion": row.criterion_key, "classification": row.classification, "outcome": row.outcome}
        for row in results
    ]
    if evaluation.status == "completed":
        entry["retrieval_samples"] = retrieval_samples(session, evaluation)
    return entry


def main() -> int:
    session = SessionLocal()
    evidence = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "passes": []}
    try:
        for unit in UNITS:
            for pass_index in PASSES:
                sys.stderr.write(f"running {unit} p{pass_index}\n")
                sys.stderr.flush()
                evidence["passes"].append(run_pass(session, unit, pass_index))
    finally:
        session.close()
    evidence["summary"] = [
        {
            "unit_key": item["unit_key"],
            "pass_index": item["pass_index"],
            "status": item["status"],
            "outcome": item["overall_outcome"],
            "blocking": [failure["criterion"] for failure in item["blocking_failures"]],
        }
        for item in evidence["passes"]
    ]
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
