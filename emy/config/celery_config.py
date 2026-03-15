from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery app
celery_app = Celery(
    'emy',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Celery Beat schedule - check inbox every 10 minutes
celery_app.conf.beat_schedule = {
    'check-inbox-every-10-minutes': {
        'task': 'emy.tasks.email_polling_task.check_inbox_periodically',
        'schedule': 10.0 * 60,  # 10 minutes in seconds
        'options': {'queue': 'default', 'priority': 5}
    },
}

# Task routing and rate limiting
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,
)

# Rate limiting per IP/worker
celery_app.conf.task_rate_limit = {
    'emy.tasks.email_polling_task.check_inbox_periodically': '10/h',  # Max 10 times per hour
}
