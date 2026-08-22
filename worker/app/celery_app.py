from celery import Celery

from worker.app.core.config import get_worker_settings


settings = get_worker_settings()
celery_app = Celery(
    settings.service_name,
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

# Import task registrations when the worker starts.
from worker.app import tasks as _tasks  # noqa: E402,F401
