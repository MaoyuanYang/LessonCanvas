"""F007 impact matrix: classify a version-pair delta into affected scope.

Pure function of (old confirmed pair, new pair or drafts) per Spec D1. It is
explainable by construction — every verdict names its triggering field — and
conservative: any change the matrix cannot classify widens to the full scope
and sets the uncertainty flag instead of silently under-scoping.
"""

import json

BRIEF_UNIT_FIELDS = (
    "unit_theme",
    "teaching_objectives",
    "material_position",
    "student_context",
    "assessment_orientation",
    "output_language_mode",
)

BLUEPRINT_UNIT_FIELDS = ("title", "objectives", "assessment_intent")

BLUEPRINT_LESSON_FIELDS = (
    "title",
    "objective_ids",
    "assessment_intent",
    "period_count",
    "activity_outline",
    "material_notes",
)

# Grounding metadata attached by the planning layer, not teacher intent: a
# revision draft never carries it, so it must not widen scope.
IGNORED_FIELDS = ("index", "citations")

ALL_FAMILIES = ("lesson_plan", "slide_deck", "exercise")


def _brief_value(fields_json: str | None, field: str):
    if not fields_json:
        return None
    fields = json.loads(fields_json)
    entry = fields.get(field) or {}
    return entry.get("value")


def _lesson_map(payload_json: str | None) -> dict[int, dict]:
    if not payload_json:
        return {}
    payload = json.loads(payload_json)
    return {int(lesson.get("index") or 0): lesson for lesson in payload.get("lessons", [])}


def compute_impact(
    old_brief_fields: str | None,
    new_brief_fields: str | None,
    old_blueprint_payload: str | None,
    new_blueprint_payload: str | None,
) -> dict:
    """Return the D1 verdict for the delta between two confirmed pairs.

    ``affected_lessons`` is None for the full-unit scope (all lessons × all
    families); otherwise a sorted list of lesson indexes. ``reasons`` carries
    one entry per triggering change. ``uncertain`` marks widened scope.
    """

    reasons: list[dict] = []
    uncertain = False
    full_scope = False
    affected: set[int] = set()

    # --- Brief deltas -----------------------------------------------------
    if old_brief_fields != new_brief_fields:
        old = json.loads(old_brief_fields) if old_brief_fields else {}
        new = json.loads(new_brief_fields) if new_brief_fields else {}
        all_fields = sorted(set(old) | set(new))
        for field in all_fields:
            old_value = (old.get(field) or {}).get("value")
            new_value = (new.get(field) or {}).get("value")
            if old_value == new_value:
                continue
            if field in BRIEF_UNIT_FIELDS:
                full_scope = True
                reasons.append(
                    {"field": f"brief.{field}", "scope": "unit", "detail": "简报单元级字段变更"}
                )
            elif field == "lesson_count":
                reasons.append(
                    {"field": "brief.lesson_count", "scope": "structural", "detail": "课时数变更"}
                )
            else:
                # Unclassifiable brief change: widen with visible uncertainty.
                full_scope = True
                uncertain = True
                reasons.append(
                    {
                        "field": f"brief.{field}",
                        "scope": "unit",
                        "detail": "无法分类的简报变更，保守扩大范围",
                    }
                )

    # --- Blueprint deltas -------------------------------------------------
    old_lessons = _lesson_map(old_blueprint_payload)
    new_lessons = _lesson_map(new_blueprint_payload)
    old_unit = (
        (json.loads(old_blueprint_payload) or {}).get("unit", {}) if old_blueprint_payload else {}
    )
    new_unit = (
        (json.loads(new_blueprint_payload) or {}).get("unit", {}) if new_blueprint_payload else {}
    )

    for field in BLUEPRINT_UNIT_FIELDS:
        if old_unit.get(field) != new_unit.get(field):
            full_scope = True
            reasons.append(
                {"field": f"blueprint.unit.{field}", "scope": "unit", "detail": "蓝图单元层变更"}
            )
    unknown_unit_fields = sorted(
        (set(old_unit) | set(new_unit)) - set(BLUEPRINT_UNIT_FIELDS) - set(IGNORED_FIELDS)
    )
    for field in unknown_unit_fields:
        if old_unit.get(field) != new_unit.get(field):
            full_scope = True
            uncertain = True
            reasons.append(
                {
                    "field": f"blueprint.unit.{field}",
                    "scope": "unit",
                    "detail": "无法分类的蓝图单元层变更，保守扩大范围",
                }
            )

    added = sorted(set(new_lessons) - set(old_lessons))
    removed = sorted(set(old_lessons) - set(new_lessons))
    if added or removed:
        reasons.append(
            {
                "field": "blueprint.lessons",
                "scope": "structural",
                "detail": f"课时集合变更：新增 {added or []}，移除 {removed or []}",
            }
        )

    for index in sorted(set(old_lessons) & set(new_lessons)):
        old_lesson, new_lesson = old_lessons[index], new_lessons[index]
        changed, unknown = [], []
        for field in sorted(set(old_lesson) | set(new_lesson)):
            if old_lesson.get(field) == new_lesson.get(field):
                continue
            if field in BLUEPRINT_LESSON_FIELDS:
                changed.append(field)
            elif field not in IGNORED_FIELDS:
                unknown.append(field)
        if changed:
            affected.add(index)
            reasons.append(
                {
                    "field": f"blueprint.lesson[{index}].{'+'.join(changed)}",
                    "scope": f"lesson:{index}",
                    "detail": "蓝图课时层字段变更",
                }
            )
        if unknown:
            # Unclassifiable lesson change widens to the full scope.
            full_scope = True
            uncertain = True
            reasons.append(
                {
                    "field": f"blueprint.lesson[{index}].{'+'.join(unknown)}",
                    "scope": "unit",
                    "detail": "无法分类的课时字段变更，保守扩大范围",
                }
            )

    affected_lessons = None if full_scope else sorted(affected | set(added))
    no_delta = not reasons
    return {
        "affected_lessons": affected_lessons,
        "affected_families": [] if no_delta else list(ALL_FAMILIES),
        "reasons": reasons,
        "structural": {"added": added, "removed": removed},
        "uncertain": uncertain,
        "no_delta": no_delta,
    }


def family_affected_lessons(impact: dict, family: str) -> list[int] | None:
    """Affected lessons for one family under the matrix: decks and exercises
    follow plans transitively (Spec D1), so the lesson set is family-equal."""

    if impact["no_delta"]:
        return []
    return impact["affected_lessons"]
