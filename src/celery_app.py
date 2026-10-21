from celery import Celery
from celery.schedules import crontab

from src.core.config import config

celery_app = Celery(
    "worker",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=[
        "src.tasks.aggregation",
        "src.tasks.reports",
        "src.tasks.scheduler",
        "src.tasks.webhooks",
    ],
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "auto-close-expired-batches": {
            "task": "src.tasks.scheduler.auto_close_expired_batches",
            "schedule": crontab(hour=1, minute=0),
        },
        "cleanup-old-files": {
            "task": "src.tasks.scheduler.cleanup_old_files",
            "schedule": crontab(hour=2, minute=0),
        },
        "update-statistics": {
            "task": "src.tasks.scheduler.update_cached_statistics",
            "schedule": crontab(minute="*/5"),
        },
        "retry-failed-webhooks": {
            "task": "src.tasks.scheduler.retry_failed_webhooks",
            "schedule": crontab(minute="*/15"),
        },
    },
)

celery_app.autodiscover_tasks(["src.tasks"])
