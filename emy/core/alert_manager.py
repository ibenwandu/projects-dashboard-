"""
AlertManager - Centralized alert system with throttling and badge tracking.

Wraps PushoverNotifier with:
- Per-alert-type throttling
- Database persistence
- Unread badge tracking
"""

import time
from typing import Dict, Optional
from datetime import datetime
from emy.tools.notification_tool import PushoverNotifier
from emy.core.database import EMyDatabase


class AlertManager:
    """Centralized alert management with throttling and persistence."""

    def __init__(self, notifier: Optional[PushoverNotifier] = None,
                 db: Optional[EMyDatabase] = None):
        """
        Initialize AlertManager.

        Args:
            notifier: PushoverNotifier instance (or None to create default)
            db: EMyDatabase instance (or None to create default)
        """
        self.notifier = notifier or PushoverNotifier()
        self.db = db or EMyDatabase()
        self._throttle: Dict[str, float] = {}  # In-memory throttle tracking

    def send(self, alert_type: str, title: str, message: str,
             priority: int = 0, throttle_seconds: int = 60) -> bool:
        """
        Send alert if not throttled. Persist to database if sent.

        Args:
            alert_type: Type of alert (e.g., 'trade_opened', 'trade_closed')
            title: Alert title
            message: Alert message
            priority: 0=Normal, 1=High, 2=Emergency
            throttle_seconds: Throttle window in seconds

        Returns:
            True if alert was sent, False if throttled or send failed
        """
        if not self._should_send(alert_type, throttle_seconds):
            return False

        # Attempt to send via Pushover
        sent = self.notifier.send_alert(
            title=title,
            message=message,
            priority=priority
        )

        if sent:
            # Update in-memory throttle
            self._throttle[alert_type] = time.time()
            # Persist to database
            self.db.log_alert(alert_type, title, message, priority)

        return sent

    def get_unread_count(self, alert_type: Optional[str] = None) -> int:
        """
        Get count of unread alerts.

        Args:
            alert_type: Optional filter by alert type. None returns all unread.

        Returns:
            Count of unread alerts
        """
        alerts = self.db.get_unread_alerts(alert_type)
        return len(alerts)

    def mark_read(self, alert_type: Optional[str] = None) -> int:
        """
        Mark alerts as read.

        Args:
            alert_type: Optional filter by alert type. None marks all read.

        Returns:
            Count of alerts marked as read
        """
        return self.db.mark_alerts_read(alert_type)

    def _should_send(self, alert_type: str, throttle_seconds: int) -> bool:
        """
        Check if alert should be sent (not throttled).

        Args:
            alert_type: Type of alert
            throttle_seconds: Throttle window in seconds

        Returns:
            True if should send, False if throttled
        """
        last_send = self._throttle.get(alert_type)

        # No previous send = always send
        if last_send is None:
            return True

        # Check if throttle window has expired
        elapsed = time.time() - last_send
        return elapsed >= throttle_seconds
