"""
Celery Beat task definitions for autonomous monitoring agents.

This module defines shared tasks that wrap agent execution for Celery Beat scheduling.
Tasks are executed on configured schedules (crontab expressions) defined in celery_config.py.
"""

import asyncio
import logging
from celery import shared_task
from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent
from emy.agents.log_analysis_agent import LogAnalysisAgent
from emy.agents.profitability_agent import ProfitabilityAgent

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def trading_hours_enforcement(self, enforcement_time: str = "21:30 Friday"):
    """Enforce trading hours compliance by closing non-compliant trades.

    Scheduled: Friday 21:30 UTC, Mon-Thu 23:00 UTC

    Args:
        enforcement_time: Human-readable enforcement time (e.g., "21:30 Friday")

    Returns:
        dict: Result containing trades_closed count and violations list

    Raises:
        Exception: If enforcement fails (will retry with exponential backoff)
    """
    logger.info(f"[Task] Starting trading_hours_enforcement at {enforcement_time}")
    try:
        agent = TradingHoursMonitorAgent()
        # Run async method in sync context
        result = asyncio.run(agent._enforce_compliance(enforcement_time=enforcement_time))
        logger.info(
            f"[Task] Enforcement complete: {result.get('trades_closed', 0)} trades closed"
        )
        return result
    except Exception as exc:
        logger.error(f"[Task] Enforcement error: {exc}")
        # Retry with exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries), max_retries=3)


@shared_task(bind=True, max_retries=3)
def trading_hours_monitoring(self):
    """Monitor trading hours compliance without enforcement.

    Scheduled: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)

    Returns:
        dict: Result containing violations_detected count and details

    Raises:
        Exception: If monitoring fails (will retry with exponential backoff)
    """
    logger.info("[Task] Starting trading_hours_monitoring")
    try:
        agent = TradingHoursMonitorAgent()
        # Run async method in sync context
        result = asyncio.run(agent._monitor_compliance())
        logger.info(
            f"[Task] Monitoring complete: {result.get('violations_detected', 0)} violations"
        )
        return result
    except Exception as exc:
        logger.error(f"[Task] Monitoring error: {exc}")
        # Retry with exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries), max_retries=3)


@shared_task(bind=True, max_retries=3)
def log_analysis_daily(self):
    """Analyze trading logs for performance anomalies.

    Scheduled: Daily 23:00 UTC

    Returns:
        dict: Result containing anomalies count and analysis details

    Raises:
        Exception: If analysis fails (will retry with exponential backoff)
    """
    logger.info("[Task] Starting log_analysis_daily")
    try:
        agent = LogAnalysisAgent()
        # Run async method in sync context
        result = asyncio.run(agent.analyze())
        logger.info(f"[Task] Log analysis complete: {result.get('anomalies', 0)} anomalies")
        return result
    except Exception as exc:
        logger.error(f"[Task] Log analysis error: {exc}")
        # Retry with exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries), max_retries=3)


@shared_task(bind=True, max_retries=3)
def profitability_analysis_weekly(self):
    """Analyze profitability patterns and generate recommendations.

    Scheduled: Weekly Sunday 22:00 UTC

    Returns:
        dict: Result containing recommendations list and analysis details

    Raises:
        Exception: If analysis fails (will retry with exponential backoff)
    """
    logger.info("[Task] Starting profitability_analysis_weekly")
    try:
        agent = ProfitabilityAgent()
        # Run async method in sync context
        result = asyncio.run(agent.analyze())
        logger.info(
            f"[Task] Profitability analysis complete: "
            f"{len(result.get('recommendations', []))} recommendations"
        )
        return result
    except Exception as exc:
        logger.error(f"[Task] Profitability analysis error: {exc}")
        # Retry with exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries), max_retries=3)
