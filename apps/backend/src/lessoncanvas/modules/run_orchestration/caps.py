"""F016 formula-based per-run model-call caps (Spec D5).

Caps are computed once at run creation from the lesson count so the added
specialist stages stay bounded exactly as tightly as the stage set they
implement: plans design+write+review(+revise+re-review) = 5 per lesson;
decks and exercises write+review(+revise+re-review) = 4. The pre-F016 flat
caps remain the floor, so no run ever gets a smaller budget than before.
"""

from lessoncanvas.settings import get_settings

_FAMILIES = ("plans", "decks", "exercises")


class CapExhaustedError(Exception):
    """Per-run model-call cap reached; no further model work may begin.

    Shared by the three generation graphs and the F016 specialist stages so
    every catch site sees one class regardless of which stage raised it.
    """


def compute_model_call_cap(family: str, lesson_count: int) -> int:
    if family not in _FAMILIES:
        raise ValueError(f"unknown artifact family: {family}")
    settings = get_settings()
    per_lesson = {
        "plans": settings.model_call_cap_plans_per_lesson,
        "decks": settings.model_call_cap_decks_per_lesson,
        "exercises": settings.model_call_cap_exercises_per_lesson,
    }[family]
    floor = {
        "plans": settings.max_model_calls_per_run,
        "decks": settings.max_model_calls_per_deck_run,
        "exercises": settings.max_model_calls_per_exercise_run,
    }[family]
    formula = per_lesson * max(1, lesson_count) + settings.model_call_cap_slack
    return max(floor, formula)
