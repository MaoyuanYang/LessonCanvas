from celery import Celery

from lessoncanvas.settings import get_settings

settings = get_settings()

celery_app = Celery("lessoncanvas", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True


@celery_app.task(name="lessoncanvas.health_check")
def health_check() -> str:
    return "ok"
