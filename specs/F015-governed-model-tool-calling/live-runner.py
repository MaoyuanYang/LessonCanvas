"""F015 T7 live evidence runner (owner-authorized 2026-09-03).

Runs against the REAL DeepSeek adapter (TS-021) plus the D6 compatibility
probe (response_format json_object combined with tools). Data isolation: the
throwaway `lessoncanvas_test` database; tables truncated after the run, so no
state survives besides this script's JSON evidence.

Usage (from apps/backend, credentials via environment):
  DEEPSEEK_KEY=... DB_URL=... uv run python ../../specs/F015-governed-model-tool-calling/live-runner.py
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

EVIDENCE_PATH = Path(__file__).parent / "live-evidence.json"
UNIT_JSON = (
    Path(__file__).parents[2]
    / "apps/backend/src/lessoncanvas/evaluation_datasets/units/travelling-around/unit.json"
)
INTENT_SOURCE = (
    Path(__file__).parents[2]
    / "apps/backend/src/lessoncanvas/evaluation_datasets/units/travelling-around/"
    "sources/02-teacher-intent.txt"
)

os.environ["LESSONCANVAS_MODEL_ADAPTER"] = "deepseek"
os.environ["LESSONCANVAS_TASKS_EAGER"] = "true"
os.environ["LESSONCANVAS_CHECKPOINT_BACKEND"] = "memory"
if os.environ.get("DB_URL"):
    os.environ["LESSONCANVAS_DATABASE_URL"] = os.environ["DB_URL"]
if os.environ.get("DEEPSEEK_KEY"):
    os.environ["LESSONCANVAS_DEEPSEEK_API_KEY"] = os.environ["DEEPSEEK_KEY"]

sys.path.insert(0, str(Path(__file__).parents[2] / "apps/backend/src"))

import httpx  # noqa: E402

from lessoncanvas.adapters.model import DeepSeekAdapter, provider_tool_definitions  # noqa: E402
from lessoncanvas.db import SessionLocal  # noqa: E402
from lessoncanvas.models import Project, Workspace  # noqa: E402
from lessoncanvas.modules.discovery_planning.planning import (  # noqa: E402
    PLANNING_DRAFT_TOOL_SYSTEM,
)
from lessoncanvas.modules.discovery_planning.tool_loop import run_tool_loop  # noqa: E402
from lessoncanvas.modules.sources_grounding.standards import (  # noqa: E402
    STANDARDS_TOOL_DEFINITION,
    execute_tool,
)
from lessoncanvas.modules.discovery_planning.graph import record_trace  # noqa: E402
from lessoncanvas.models import DiscoveryRun  # noqa: E402
from lessoncanvas.settings import get_settings  # noqa: E402


def d6_probe(api_key: str) -> dict:
    """Record provider behavior when response_format json_object is combined
    with tools (Spec D6). The adapter itself omits response_format on tool
    rounds (plain function-calling mode) — this probe documents whether the
    combined mode would also work, for the record."""

    base = get_settings().deepseek_base_url
    request = {
        "model": get_settings().deepseek_model,
        "messages": [
            {"role": "system", "content": "You are a test probe."},
            {"role": "user", "content": "Search the standards for reading comprehension."},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "tools": provider_tool_definitions([STANDARDS_TOOL_DEFINITION]),
    }
    started = time.monotonic()
    try:
        response = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=request,
            timeout=60,
        )
        elapsed = int((time.monotonic() - started) * 1000)
        body = response.json() if response.status_code < 500 else {"raw": response.text[:300]}
        message = (body.get("choices") or [{}])[0].get("message", {})
        return {
            "request_mode": "tools + response_format json_object",
            "http_status": response.status_code,
            "latency_ms": elapsed,
            "finish_reason": (body.get("choices") or [{}])[0].get("finish_reason"),
            "has_tool_calls": bool(message.get("tool_calls")),
            "content_preview": str(message.get("content") or "")[:200],
            "usage": body.get("usage"),
        }
    except Exception as error:  # noqa: BLE001 - probe records the failure honestly
        return {"request_mode": "tools + response_format json_object", "error": repr(error)}


def main() -> None:
    api_key = get_settings().deepseek_api_key
    if not api_key:
        raise SystemExit("DEEPSEEK key not configured")

    unit = json.loads(UNIT_JSON.read_text(encoding="utf-8"))
    answers = unit["discovery_answers"]
    corpus_excerpt = INTENT_SOURCE.read_text(encoding="utf-8")[:1200]

    evidence: dict = {
        "feature": "F015",
        "scenario": "TS-021 live self-requested tool round + D6 probe",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "adapter": "deepseek",
        "model": get_settings().deepseek_model,
        "unit_key": unit["unit_key"],
        "environment": "isolated lessoncanvas_test database; truncated after run",
        "d6_probe": d6_probe(api_key),
        "attempts": [],
    }

    payload = {
        "kind": "planning_build_draft",
        "brief": answers,
        "known": unit["planning_answers"],
        "corpus_excerpt": corpus_excerpt,
        "retrieved_sources": [{"source_id": "synthetic", "filename": "02-teacher-intent.txt"}],
        "grounding_state": "retrieved",
    }
    user = json.dumps(payload, ensure_ascii=False)

    session = SessionLocal()
    try:
        for attempt in range(1, 4):
            workspace = Workspace(subject=f"f015-live-{uuid.uuid4().hex}")
            session.add(workspace)
            session.flush()
            project = Project(workspace_id=workspace.id, name="F015 live evidence")
            session.add(project)
            session.flush()
            run = DiscoveryRun(
                project_id=project.id, workspace_id=workspace.id, kind="planning"
            )
            session.add(run)
            session.commit()

            started = time.monotonic()
            result = run_tool_loop(
                session=session,
                run=run,
                system=PLANNING_DRAFT_TOOL_SYSTEM,
                user=user,
                tools=[STANDARDS_TOOL_DEFINITION],
                dispatch=execute_tool,
                record_trace_fn=record_trace,
                run_id=str(run.id),
            )
            elapsed = int((time.monotonic() - started) * 1000)
            blueprint = (result.data or {}).get("blueprint") or {}
            contract_ok = bool(
                blueprint.get("unit", {}).get("objectives") and blueprint.get("lessons")
            )
            dispatched = [r for r in result.rounds if r.get("outcome") == "dispatched"]
            attempt_record = {
                "attempt": attempt,
                "elapsed_ms": elapsed,
                "model_calls": run.model_calls,
                "rounds": result.rounds,
                "refused_count": result.refused_count,
                "self_requested_rounds": len(dispatched),
                "dispatched_tool": dispatched[0]["name"] if dispatched else None,
                "final_contract_ok": contract_ok,
                "fallback_reason": result.fallback_reason,
                "dropped_tool_calls": result.dropped_tool_calls,
                "tool_results_count": sum(
                    len(v) for v in result.tool_results.values()
                ),
            }
            evidence["attempts"].append(attempt_record)
            if dispatched and contract_ok:
                evidence["ts021"] = {
                    "outcome": "pass",
                    "attempt": attempt,
                    "summary": "planning drafting specialist self-requested a real "
                    "search_curriculum_standards round and produced the unchanged "
                    "blueprint contract",
                }
                break
        else:
            evidence["ts021"] = {
                "outcome": "fail",
                "summary": "no attempt combined a self-requested dispatched round with "
                "a contract-valid final blueprint; every attempt recorded honestly above",
            }
    finally:
        from sqlalchemy import text

        session.execute(
            text(
                "TRUNCATE TABLE trace_events, interaction_messages, discovery_runs, "
                "projects, workspaces CASCADE"
            )
        )
        session.commit()
        session.close()

    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence["ts021"], ensure_ascii=False))
    print(f"evidence written: {EVIDENCE_PATH}")


if __name__ == "__main__":
    main()
