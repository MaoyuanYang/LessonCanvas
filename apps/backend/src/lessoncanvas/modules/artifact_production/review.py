"""F016 D2/D3: the quality-review specialist stage (all three artifact families).

One review round runs between the writer draft and rendering; only severe
findings trigger exactly one revise round (writer revision + re-review). A
second severe round settles the draft failed-after-revise with the failure
naming the review stage. Review never skips deterministic structural
validation, never alters confirmed intent, and its findings are untrusted
model output normalized server-side.
"""

import json
import time

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter, parse_model_json
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.run_orchestration import service as run_service

MAX_FINDINGS = 10
MAX_FINDING_MESSAGE_CHARS = 300

PLANS_DIMENSIONS = ("objective_coverage", "grounding", "consistency")
FAMILY_DIMENSIONS = ("plan_coverage", "grounding", "consistency")

FAMILY_NOUNS = {"lesson": "教案", "deck": "课件", "exercises": "练习"}

PASSED = "passed"
PASSED_AFTER_REVISE = "passed_after_revise"
FAILED_AFTER_REVISE = "failed_after_revise"
UNPARSEABLE = "unparseable"


def review_system_prompt(family: str) -> str:
    noun = FAMILY_NOUNS.get(family, family)
    if family == "lesson":
        anchor = "the lesson's confirmed blueprint objectives"
    else:
        anchor = "the prerequisite confirmed lesson plan"
    return (
        f"You are a quality-review specialist for senior-high English teaching materials. "
        f"Review the drafted {noun} against {anchor}, the cited source chunks, and its own "
        "internal consistency. Respond with a JSON object only, shaped like "
        '{"review": {"findings": [{"dimension": "grounding", "severity": "severe", '
        '"message": "...", "reference": null}]}}; dimension must be one of the listed '
        "dimensions; severity must be severe or minor; return {\"review\": "
        "{\"findings\": []}} when nothing is wrong; never rewrite the draft; no prose."
    )


def revise_system_prompt(family: str) -> str:
    noun = FAMILY_NOUNS.get(family, family)
    return (
        f"You are the {noun} writer revising a reviewed draft. Address every severe "
        "finding while keeping the confirmed objectives, structure, and language mode. "
        "Respond with a JSON object only in the same shape as the original draft; "
        "never repeat the input payload."
    )


def normalize_findings(raw: dict, dimensions: tuple[str, ...]) -> list[dict]:
    findings: list[dict] = []
    for finding in (raw.get("findings") or [])[:MAX_FINDINGS]:
        if not isinstance(finding, dict):
            continue
        dimension = finding.get("dimension")
        severity = finding.get("severity")
        message = finding.get("message")
        if dimension not in dimensions or severity not in ("severe", "minor"):
            continue
        if not isinstance(message, str) or not message.strip():
            continue
        reference = finding.get("reference")
        entry = {
            "dimension": dimension,
            "severity": severity,
            "message": message.strip()[:MAX_FINDING_MESSAGE_CHARS],
        }
        if isinstance(reference, str) and reference.strip():
            entry["reference"] = reference.strip()[:80]
        findings.append(entry)
    return findings


def has_severe(findings: list[dict]) -> bool:
    return any(finding["severity"] == "severe" for finding in findings)


def _review_call(
    session,
    run,
    artifact,
    *,
    family: str,
    user_payload: dict,
    round_index: int,
) -> tuple[str, list[dict]]:
    """One review model call; returns (text, normalized findings) or raises
    ValueError when the response carries no JSON object (never a silent pass)."""

    adapter = get_model_adapter()
    if not run_service.reserve_model_call(session, run.id):
        from lessoncanvas.modules.run_orchestration.caps import CapExhaustedError

        raise CapExhaustedError("model call cap reached")
    session.commit()
    artifact.status = "reviewing"
    session.commit()
    run_service.append_event(
        session,
        run.id,
        "lesson",
        {"lesson_index": artifact.lesson_index, "status": "reviewing"},
    )
    session.commit()

    dimensions = PLANS_DIMENSIONS if family == "lesson" else FAMILY_DIMENSIONS
    started = time.monotonic()
    payload = {**user_payload, "round": round_index, "dimensions": list(dimensions)}
    try:
        response = adapter.complete(
            review_system_prompt(family), json.dumps(payload, ensure_ascii=False)
        )
    except ModelProviderError:
        session.rollback()
        raise
    latency = int((time.monotonic() - started) * 1000)
    data: dict | None = None
    try:
        data = parse_model_json(response.text)
        findings = normalize_findings(data.get("review") or {}, dimensions)
        parse_failed = False
    except ValueError:
        findings = []
        parse_failed = True
    record_trace(
        session,
        run.id,
        f"model.generation_review_{family}",
        {
            "prompt": payload,
            "response": data if not parse_failed else response.text[:2000],
            "round": round_index,
            "severe_count": sum(1 for f in findings if f["severity"] == "severe"),
            "minor_count": sum(1 for f in findings if f["severity"] == "minor"),
            "parse_failed": parse_failed,
        },
        latency,
        usage=response,
    )
    session.commit()
    if parse_failed:
        raise ValueError("unparseable review output")
    return response.text, findings


def _revise_call(
    session,
    run,
    artifact,
    *,
    family: str,
    user_payload: dict,
    findings: list[dict],
) -> dict:
    """One revise model call carrying the findings back to the writer."""

    adapter = get_model_adapter()
    if not run_service.reserve_model_call(session, run.id):
        from lessoncanvas.modules.run_orchestration.caps import CapExhaustedError

        raise CapExhaustedError("model call cap reached")
    session.commit()
    artifact.status = "reviewing"  # the revise round stays within reviewing
    session.commit()
    run_service.append_event(
        session,
        run.id,
        "lesson",
        {"lesson_index": artifact.lesson_index, "status": "revising"},
    )
    session.commit()

    payload = {**user_payload, "kind": f"generation_revise_{family}", "findings": findings}
    payload.pop("round", None)
    payload.pop("dimensions", None)
    started = time.monotonic()
    try:
        response = adapter.complete(
            revise_system_prompt(family), json.dumps(payload, ensure_ascii=False)
        )
    except ModelProviderError:
        session.rollback()
        raise
    latency = int((time.monotonic() - started) * 1000)
    try:
        revised = parse_model_json(response.text)
    except ValueError:
        record_trace(
            session,
            run.id,
            f"model.generation_revise_{family}",
            {"prompt": payload, "response": response.text[:2000], "parse_failed": True},
            latency,
            usage=response,
        )
        session.commit()
        raise
    record_trace(
        session,
        run.id,
        f"model.generation_revise_{family}",
        {"prompt": payload, "response": revised},
        latency,
        usage=response,
    )
    session.commit()
    return revised


def _record_review_fields(artifact, findings: list[dict], rounds: int, outcome: str) -> None:
    artifact.review_findings_json = json.dumps(findings, ensure_ascii=False)
    artifact.review_rounds = rounds
    artifact.review_outcome = outcome


def review_stage(
    session,
    run,
    artifact,
    *,
    family: str,
    writer_payload: dict,
    draft: dict,
) -> tuple[str, dict]:
    """Run the severity-gated review with at most one revise round.

    `writer_payload` is the payload the family's writer call used (minus its
    kind); the review and revise calls derive their payloads from it so the
    reviewer sees the same anchors the writer saw. Returns (outcome, draft)
    where draft is the revised draft after a revise round. Outcomes: passed /
    passed_after_revise / failed_after_revise / unparseable (bounded-retryable
    by the caller's draft loop).
    """

    review_payload = dict(writer_payload)
    review_payload["kind"] = f"generation_review_{family}"
    review_payload["draft"] = draft

    try:
        _, findings = _review_call(
            session, run, artifact, family=family, user_payload=review_payload, round_index=1
        )
    except ValueError:
        _record_review_fields(artifact, [], 1, UNPARSEABLE)
        return UNPARSEABLE, draft

    if not has_severe(findings):
        _record_review_fields(artifact, findings, 1, PASSED)
        return PASSED, draft

    try:
        revised_raw = _revise_call(
            session, run, artifact, family=family, user_payload=review_payload, findings=findings
        )
    except ValueError:
        _record_review_fields(artifact, findings, 2, UNPARSEABLE)
        return UNPARSEABLE, draft
    revised = revised_raw.get(
        {"lesson": "lesson_plan", "deck": "slide_deck", "exercises": "exercise_set"}[family],
        {},
    )

    try:
        _, round2 = _review_call(
            session, run, artifact, family=family, user_payload=review_payload, round_index=2
        )
    except ValueError:
        _record_review_fields(artifact, [], 2, UNPARSEABLE)
        return UNPARSEABLE, draft

    if has_severe(round2):
        _record_review_fields(artifact, round2, 2, FAILED_AFTER_REVISE)
        return FAILED_AFTER_REVISE, revised
    _record_review_fields(artifact, round2, 2, PASSED_AFTER_REVISE)
    return PASSED_AFTER_REVISE, revised


def review_failure_reason(family: str) -> str:
    noun = FAMILY_NOUNS.get(family, family)
    return f"review stage: severe findings persisted on the {noun} draft after one revise round"
