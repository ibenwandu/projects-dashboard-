from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery app with SQLAlchemy database-backed broker
# Broker: SQLAlchemy (converts DATABASE_URL to sqla+postgresql://)
# Backend: Database (task results stored in DB)
database_url = os.getenv('DATABASE_URL', 'sqlite:///emy.db')

# Convert DATABASE_URL to SQLAlchemy broker format
if database_url.startswith('postgresql://'):
    broker_url = database_url.replace('postgresql://', 'sqla+postgresql://', 1)
else:
    broker_url = f'sqla+{database_url}'

celery_app = Celery(
    'emy',
    broker=broker_url,
    backend=broker_url
)

# Celery Beat schedule - monitoring tasks and email polling
celery_app.conf.beat_schedule = {
    # Email polling task
    'check-inbox-every-10-minutes': {
        'task': 'emy.tasks.email_polling_task.check_inbox_periodically',
        'schedule': 10.0 * 60,  # 10 minutes in seconds
        'options': {'queue': 'default', 'priority': 5}
    },

    # TradingHoursMonitorAgent tasks
    'trading_hours_enforcement_friday': {
        'task': 'emy.tasks.monitoring_tasks.trading_hours_enforcement',
        'schedule': crontab(hour=21, minute=30, day_of_week=4),  # Friday 21:30 UTC
        'args': ('21:30 Friday',),
        'options': {'queue': 'monitoring', 'priority': 8}
    },
    'trading_hours_enforcement_weekday': {
        'task': 'emy.tasks.monitoring_tasks.trading_hours_enforcement',
        'schedule': crontab(hour=23, minute=0, day_of_week='1-4'),  # Mon-Thu 23:00 UTC
        'args': ('23:00 Mon-Thu',),
        'options': {'queue': 'monitoring', 'priority': 8}
    },
    'trading_hours_monitoring': {
        'task': 'emy.tasks.monitoring_tasks.trading_hours_monitoring',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours: 00:00, 06:00, 12:00, 18:00 UTC
        'options': {'queue': 'monitoring', 'priority': 5}
    },

    # LogAnalysisAgent task
    'log_analysis_daily': {
        'task': 'emy.tasks.monitoring_tasks.log_analysis_daily',
        'schedule': crontab(hour=23, minute=0),  # Daily 23:00 UTC
        'options': {'queue': 'monitoring', 'priority': 6}
    },

    # ProfitabilityAgent task
    'profitability_analysis_weekly': {
        'task': 'emy.tasks.monitoring_tasks.profitability_analysis_weekly',
        'schedule': crontab(hour=22, minute=0, day_of_week=6),  # Sunday 22:00 UTC
        'options': {'queue': 'monitoring', 'priority': 7}
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
