"""F012 TS-002/TS-006 (seeding half): the seed script creates the synthetic
sample once (deterministic fake adapter, zero model spend) and a re-run is a
no-op; the seeded sample is then readable through the sample-read rule.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import make_token


def _run_seed() -> dict:
    env = dict(os.environ)
    env["LESSONCANVAS_MODEL_ADAPTER"] = "fake"
    env["LESSONCANVAS_TASKS_EAGER"] = "true"
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "scripts" / "seed_sample.py")],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_seed_creates_once_then_idempotent(client, db_session):
    first = _run_seed()
    assert first["seeded"] is True
    project_id = first["project_id"]

    second = _run_seed()
    assert second == {
        "seeded": False,
        "already_present": True,
        "project_id": project_id,
        "name": first["name"],
    }

    # The seeded sample is inspectable by an unrelated authenticated reviewer
    # through the default demo-owner designation (no monkeypatching needed).
    reviewer = {"Authorization": f"Bearer {make_token('seed_reviewer')}"}
    detail = client.get(f"/projects/{project_id}", headers=reviewer)
    assert detail.status_code == 200
    sources = client.get(f"/projects/{project_id}/sources", headers=reviewer)
    assert sources.status_code == 200
    assert len(sources.json()) > 0
