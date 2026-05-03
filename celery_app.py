"""Celery application instance.

Broker and result backend are Redis (different databases).
Tasks are auto-discovered from the ``tasks/`` package.

Start the worker:
    celery -A celery_app worker --loglevel=info

Start Celery Beat (periodic tasks):
    celery -A celery_app beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab

from config import get_settings

settings = get_settings()

celery = Celery(
    "packagego",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_hijack_root_logger=False,
)

# Auto-discover tasks in the `tasks` package
celery.autodiscover_tasks(["tasks"])

# ---------------------------------------------------------------------------
# Celery Beat schedule – periodic tasks
# ---------------------------------------------------------------------------

celery.conf.beat_schedule = {
    "delivery-digest-every-hour": {
        "task": "tasks.digest_tasks.delivery_digest",
        "schedule": crontab(minute=0),  # every hour at minute 0
    },
}
