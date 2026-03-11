"""
ReturnShield AI — Celery Configuration

Sets up the Celery app for background task processing.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "returnshield",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    "retrain-ml-models": {
        "task": "app.workers.tasks.retrain_models",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # Weekly, Monday 2 AM
    },
    "sync-prediction-outcomes": {
        "task": "app.workers.tasks.sync_prediction_outcomes",
        "schedule": crontab(hour=3, minute=0),  # Daily 3 AM
    },
}

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.workers"])
