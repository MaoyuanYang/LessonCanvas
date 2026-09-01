from celery import Celery

from lessoncanvas.settings import get_settings

settings = get_settings()

celery_app = Celery("lessoncanvas", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True


@celery_app.task(name="lessoncanvas.health_check")
def health_check() -> str:
    return "ok"


@celery_app.task(name="lessoncanvas.generate_unit", max_retries=2)
def generate_unit(run_id: str) -> str:
    """Execute one generation run to a settled status.

    Bounded retries resume the same run from per-lesson checkpoints (F003 D2/D5);
    cap exhaustion and supersession are settled inside the workflow itself.
    """

    from lessoncanvas.modules.artifact_production.graph import (
        execute_generation,
        mark_provider_exhausted,
    )

    try:
        return execute_generation(run_id)
    except Exception as error:
        if generate_unit.request.retries >= generate_unit.max_retries:
            return mark_provider_exhausted(run_id)
        raise generate_unit.retry(exc=error) from error


@celery_app.task(name="lessoncanvas.generate_decks", max_retries=2)
def generate_decks(run_id: str) -> str:
    """Execute one slide-deck generation run to a settled status (F004).

    Same recovery contract as generate_unit: bounded retries resume the same
    run from per-deck checkpoints; cap exhaustion and supersession settle
    inside the workflow.
    """

    from lessoncanvas.modules.artifact_production.deck_graph import (
        execute_deck_generation,
        mark_deck_provider_exhausted,
    )

    try:
        return execute_deck_generation(run_id)
    except Exception as error:
        if generate_decks.request.retries >= generate_decks.max_retries:
            return mark_deck_provider_exhausted(run_id)
        raise generate_decks.retry(exc=error) from error


@celery_app.task(name="lessoncanvas.generate_exercises", max_retries=2)
def generate_exercises(run_id: str) -> str:
    """Execute one exercise/answer generation run to a settled status (F005).

    Same recovery contract as generate_unit: bounded retries resume the same
    run from per-pair checkpoints; cap exhaustion and supersession settle
    inside the workflow.
    """

    from lessoncanvas.modules.artifact_production.exercise_graph import (
        execute_exercise_generation,
        mark_exercise_provider_exhausted,
    )

    try:
        return execute_exercise_generation(run_id)
    except Exception as error:
        if generate_exercises.request.retries >= generate_exercises.max_retries:
            return mark_exercise_provider_exhausted(run_id)
        raise generate_exercises.retry(exc=error) from error


@celery_app.task(name="lessoncanvas.run_technical_evaluation", max_retries=1)
def run_technical_evaluation(evaluation_id: str) -> str:
    """Execute one F009 technical-evaluation pass to a settled status.

    The scripted harness re-verification and criteria computation are
    deterministic; provider unavailability in live mode settles the explicit
    provider_unavailable state with partial evidence retained (Spec D4/D7).
    """

    import uuid

    from lessoncanvas.modules.technical_evaluation.service import execute_evaluation

    return execute_evaluation(uuid.UUID(evaluation_id))
