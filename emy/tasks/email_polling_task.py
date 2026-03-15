import asyncio
import logging
import os
from datetime import datetime
from celery import shared_task
from emy.tools.email_parser import EmailParser
from emy.core.database import EMyDatabase
from emy.config.celery_config import celery_app

logger = logging.getLogger(__name__)

# Try to import redis, but don't fail if not available
redis_client = None
try:
    import redis
    try:
        redis_client = redis.Redis.from_url(
            os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2
        )
        redis_client.ping()
    except Exception as e:
        redis_client = None
        logger.warning(f"Redis connection failed - rate limiting disabled: {e}")
except ImportError:
    logger.warning("Redis not installed - rate limiting disabled")

async def log_polling_event(status: str, email_count: int, error_message: str = None):
    """Log polling event to database"""
    db = EMyDatabase()
    try:
        db.execute(
            """
            INSERT INTO polling_log (status, email_count, error_message, timestamp)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (status, email_count, error_message)
        )
        logger.info(f"Polling event logged: status={status}, count={email_count}")
    except Exception as e:
        logger.error(f"Failed to log polling event: {e}")

@celery_app.task(bind=True, max_retries=3)
def check_inbox_periodically(self):
    """
    Periodic task: Check inbox for new emails every 10 minutes.

    Triggered by Celery Beat scheduler.
    Calls EmailParser.check_inbox() and processes any new emails.
    """
    try:
        # Rate limiting: max 10 checks per hour (if Redis available)
        if redis_client:
            rate_key = f"email_polling:{datetime.now().strftime('%Y%m%d%H')}"
            check_count = redis_client.incr(rate_key)
            redis_client.expire(rate_key, 3600)  # 1 hour expiry

            if check_count > 10:
                logger.warning(f"Rate limit exceeded for inbox polling ({check_count}/hour)")
                asyncio.run(log_polling_event('rate_limited', 0))
                return {'status': 'rate_limited', 'processed': 0}

        # Run async email parsing
        email_parser = EmailParser()
        emails = asyncio.run(email_parser.check_inbox())

        logger.info(f"Polling task: Found {len(emails)} new emails")
        asyncio.run(log_polling_event('success', len(emails)))

        return {
            'status': 'success',
            'processed': len(emails),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"Polling task failed: {exc}")
        asyncio.run(log_polling_event('error', 0, str(exc)))

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@shared_task
def trigger_email_processing(email_ids: list):
    """
    Trigger processing of specific emails.
    Called by polling task when new emails detected.

    Args:
        email_ids: List of Gmail message IDs to process
    """
    logger.info(f"Triggering processing for {len(email_ids)} emails")
    # This will be implemented in Task 2
    pass
