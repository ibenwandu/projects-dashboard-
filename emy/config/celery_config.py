from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery app with in-memory broker (no external dependencies)
# Tasks execute synchronously in the same process (emy-brain)
# No separate worker service needed
celery_app = Celery('emy')

# In-memory broker for local task scheduling
celery_app.conf.broker_url = 'memory://'
celery_app.conf.result_backend = 'cache+memory://'
celery_app.conf.task_always_eager = True  # Execute tasks immediately, synchronously
celery_app.conf.task_eager_propagates = True  # Propagate exceptions

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

# Import task modules AFTER app configuration to register @shared_task decorators
# This must happen after celery_app is fully configured to avoid circular imports
def _register_tasks():
    """Late import of task modules to register @shared_task decorated functions."""
    try:
        # Import monitoring tasks - these register with @shared_task decorators
        from emy.tasks import monitoring_tasks as _  # noqa: F401
        # Import email polling task
        from emy.tasks import email_polling_task as _  # noqa: F401
    except ImportError as e:
        import logging
        logging.warning(f"Could not import task modules: {e}")

# Call task registration function
_register_tasks()
