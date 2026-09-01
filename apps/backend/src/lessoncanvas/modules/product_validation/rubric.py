"""F010 fixed external-teacher review rubric (Spec D1, revision `rubric-r1`).

Pure validation and outcome computation — zero model calls. The rubric is
fixed before any review; every imported evidence payload must satisfy this
schema exactly, and the unit outcome derives deterministically from it:
passed requires zero severe findings, a core-rubric mean of at least 4.0,
and no required structural rework.
"""

from __future__ import annotations

import datetime as dt
import re

RUBRIC_REVISION = "rubric-r1"
CORE_MEAN_THRESHOLD = 4.0
SEVERE_FINDING_CLASSES = (
    "knowledge_error",
    "language_error",
    "answer_error",
    "objective_alignment_error",
)

DIMENSIONS = (
    {
        "key": "knowledge_correctness",
        "label": "知识准确性",
        "description": "学科知识无误，不出现会误导教师或学生的事实性错误",
    },
    {
        "key": "language_quality",
        "label": "语言质量",
        "description": "英语语言使用正确、得体，不示范错误英语",
    },
    {
        "key": "exercise_answer_correctness",
        "label": "练习与答案正确性",
        "description": "练习设计合理，参考答案正确且与题目匹配",
    },
    {
        "key": "objective_alignment",
        "label": "目标对齐",
        "description": "教案、课件、练习与确认的教学目标一致支撑",
    },
    {
        "key": "teaching_usability",
        "label": "教学可用性",
        "description": "结构清晰可直接用于备课与课堂，无需结构性返工",
    },
)
DIMENSION_KEYS = tuple(dim["key"] for dim in DIMENSIONS)

SEVERE_CLASS_LABELS = {
    "knowledge_error": "知识错误",
    "language_error": "语言错误",
    "answer_error": "答案错误",
    "objective_alignment_error": "目标对齐错误",
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_evidence(payload: dict) -> list[str]:
    """Validate an imported rubric-evidence payload against `rubric-r1`.

    Returns every violation as a stable ``field: reason`` string; an empty
    list means the payload satisfies the schema. Nothing is persisted by
    this function.
    """
    violations: list[str] = []
    if not isinstance(payload, dict):
        return ["evidence: must be a JSON object"]

    scores = payload.get("scores")
    if not isinstance(scores, dict):
        violations.append("scores: required object missing")
        scores = {}
    for dim in DIMENSIONS:
        entry = scores.get(dim["key"])
        if not isinstance(entry, dict):
            violations.append(f"scores.{dim['key']}: required score entry missing")
            continue
        score = entry.get("score")
        if not _is_integer(score) or not 1 <= score <= 5:
            violations.append(f"scores.{dim['key']}.score: must be an integer 1-5")
        if not _nonempty_str(entry.get("note")):
            violations.append(f"scores.{dim['key']}.note: required evidence note missing")
    for key in scores:
        if key not in DIMENSION_KEYS:
            violations.append(f"scores.{key}: unknown dimension")

    findings = payload.get("severe_findings")
    if not isinstance(findings, list):
        violations.append("severe_findings: required list missing")
        findings = []
    for index, finding in enumerate(findings):
        prefix = f"severe_findings[{index}]"
        if not isinstance(finding, dict):
            violations.append(f"{prefix}: must be an object")
            continue
        if finding.get("class") not in SEVERE_FINDING_CLASSES:
            violations.append(f"{prefix}.class: must be one of {', '.join(SEVERE_FINDING_CLASSES)}")
        reference = finding.get("lesson_reference")
        if _is_integer(reference):
            reference_ok = reference >= 1
        else:
            reference_ok = _nonempty_str(reference)
        if not reference_ok:
            violations.append(f"{prefix}.lesson_reference: required lesson reference missing")
        if not _nonempty_str(finding.get("evidence")):
            violations.append(f"{prefix}.evidence: required evidence text missing")

    rework = payload.get("structural_rework_required")
    if not isinstance(rework, bool):
        violations.append("structural_rework_required: required boolean missing")
    elif rework and not _nonempty_str(payload.get("structural_rework_reason")):
        violations.append("structural_rework_reason: required when structural rework is true")

    attestation = payload.get("attestation")
    if not isinstance(attestation, dict):
        violations.append("attestation: required object missing")
    else:
        if not _nonempty_str(attestation.get("evaluator_reference")):
            violations.append(
                "attestation.evaluator_reference: required pseudonymous reference missing"
            )
        completed = attestation.get("completed_date")
        if not _nonempty_str(completed) or not _DATE_RE.match(completed):
            violations.append("attestation.completed_date: required YYYY-MM-DD date missing")
        else:
            try:
                dt.date.fromisoformat(completed)
            except ValueError:
                violations.append("attestation.completed_date: not a valid calendar date")

    return violations


def core_mean(payload: dict) -> float:
    """Arithmetic mean of the five dimension scores (caller validates first)."""
    total = sum(int(payload["scores"][key]["score"]) for key in DIMENSION_KEYS)
    return total / len(DIMENSION_KEYS)


def compute_outcome(payload: dict) -> dict:
    """Deterministically compute the unit outcome from validated evidence.

    Identical evidence always yields the identical outcome; no model call,
    no mutation of evaluated content.
    """
    violations = validate_evidence(payload)
    if violations:
        raise ValueError("evidence does not satisfy the rubric schema; validate first")

    violated_rules: list[str] = []
    if payload["severe_findings"]:
        violated_rules.append("severe_finding_present")
    mean = core_mean(payload)
    if mean < CORE_MEAN_THRESHOLD:
        violated_rules.append("core_mean_below_threshold")
    if payload["structural_rework_required"]:
        violated_rules.append("structural_rework_required")

    return {
        "outcome": "failed" if violated_rules else "passed",
        "core_mean": round(mean, 2),
        "core_mean_threshold": CORE_MEAN_THRESHOLD,
        "severe_finding_count": len(payload["severe_findings"]),
        "structural_rework_required": payload["structural_rework_required"],
        "violated_rules": violated_rules,
    }


def rubric_sheet() -> dict:
    """Data for the printable zh-Hans rubric hand-out sheet (fixed schema
    order; the evaluator completes exactly this sheet offline)."""
    return {
        "rubric_revision": RUBRIC_REVISION,
        "title": "LessonCanvas 单元教学包外部教师评审量表",
        "scale": "每项 1–5 分（5 为最高），并填写必要的证据说明",
        "dimensions": [dict(dim) for dim in DIMENSIONS],
        "severe_finding_classes": [
            {"class": key, "label": SEVERE_CLASS_LABELS[key]} for key in SEVERE_FINDING_CLASSES
        ],
        "severe_finding_rule": (
            "凡会误导教师或学生、或需结构性返工才能使用的知识、语言、答案或"
            "目标对齐错误，均须逐条登记为严重问题（注明课时与证据）；"
            "普通改进建议只影响评分，不作为严重问题。"
        ),
        "structural_rework_question": (
            "该单元包是否需要结构性返工才能用于课堂？（是/否；选“是”须说明原因）"
        ),
        "thresholds": {
            "core_mean_min": CORE_MEAN_THRESHOLD,
            "severe_findings_max": 0,
            "structural_rework": "不允许",
        },
        "attestation_fields": ["评审者标识（伪匿名）", "完成日期（YYYY-MM-DD）"],
    }
