from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

celery_app = Celery(
    "ticketing_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "src.core.tasks.sla_tasks",
        "src.core.tasks.assignment_tasks",   # ← NEW
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "detect-sla-breaches": {
        "task": "tasks.detect_sla_breaches",
        "schedule": crontab(minute="*/5"),
    },
    "detect-escalations": {
        "task": "tasks.detect_escalations",
        "schedule": crontab(minute="*/5"),
    },
    "auto-close-resolved-tickets": {
        "task": "tasks.auto_close_resolved_tickets",
        "schedule": crontab(minute="0"),
    },
}