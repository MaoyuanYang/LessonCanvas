"""F012 T5 (Spec D3/D10): seed the synthetic sample project.

Idempotent: the designated demo workspace keeps exactly one active sample
project; a re-run detects it and exits without re-billing or duplicating.

Must run with the deterministic fake adapter so seeding never spends model
budget and never depends on a live provider:
    LESSONCANVAS_MODEL_ADAPTER=fake LESSONCANVAS_TASKS_EAGER=true \
        uv run python scripts/seed_sample.py
"""

import json
import sys

from sqlalchemy import select

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import Project, Workspace
from lessoncanvas.modules.identity_workspace import service as iw_service
from lessoncanvas.modules.technical_evaluation import harness
from lessoncanvas.modules.technical_evaluation.dataset import cached_dataset
from lessoncanvas.settings import get_settings

SAMPLE_UNIT_KEY = "travelling-around"
SAMPLE_PROJECT_NAME = "作品集示例：Travelling Around"


def main() -> int:
    settings = get_settings()
    if settings.model_adapter != "fake" or not settings.tasks_eager:
        print(
            "ERROR: seeding requires LESSONCANVAS_MODEL_ADAPTER=fake and "
            "LESSONCANVAS_TASKS_EAGER=true (deterministic, zero model spend).",
            file=sys.stderr,
        )
        return 2

    bundle = cached_dataset()
    unit = bundle.units.get(SAMPLE_UNIT_KEY)
    if unit is None:
        print(f"ERROR: sample unit {SAMPLE_UNIT_KEY!r} missing from dataset.", file=sys.stderr)
        return 2

    session = SessionLocal()
    try:
        workspace = iw_service.resolve_workspace(session, settings.demo_owner_subject)
        existing = session.scalar(
            select(Project).where(
                Project.workspace_id == workspace.id, Project.status == "active"
            )
        )
        if existing is not None:
            print(
                json.dumps(
                    {
                        "seeded": False,
                        "already_present": True,
                        "project_id": str(existing.id),
                        "name": existing.name,
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        storage = _build_storage()
        project = iw_service.create_project(
            session, workspace, SAMPLE_PROJECT_NAME, "人教版必修一 Welcome Unit"
        )
        session.commit()
        result = harness.execute_full_pipeline(
            session, storage, workspace.id, project.id, unit
        )
        print(
            json.dumps(
                {
                    "seeded": True,
                    "project_id": str(project.id),
                    "workspace_subject": settings.demo_owner_subject,
                    "name": SAMPLE_PROJECT_NAME,
                    "unit": SAMPLE_UNIT_KEY,
                    "brief_version_id": result["brief_version_id"],
                    "blueprint_version_id": result["blueprint_version_id"],
                    "run_ids": result["run_ids"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        session.close()


def _build_storage():
    from lessoncanvas.adapters.storage import StorageAdapter

    return StorageAdapter()


if __name__ == "__main__":
    code = main()
    # The eager pipeline compiles LangGraph graphs whose PostgresSaver
    # ConnectionPool keeps a non-daemon thread alive; flush and hard-exit so
    # one-shot container runs (docker compose exec) terminate after seeding.
    sys.stdout.flush()
    sys.stderr.flush()
    raise SystemExit(code)
