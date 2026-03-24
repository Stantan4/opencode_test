"""
Celery Application Configuration
"""
from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "account_risk_system",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.alert_tasks",
        "app.tasks.model_tasks",
        "app.tasks.statistics_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "model-training-weekly": {
        "task": "app.tasks.model_tasks.train_model",
        "schedule": 7 * 24 * 60 * 60,  # weekly
    },
    "statistics-daily": {
        "task": "app.tasks.statistics_tasks.generate_daily_stats",
        "schedule": 24 * 60 * 60,  # daily
    },
}
