"""Notification service for sending Pushover alerts"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class PushoverNotifier:
    """Send notifications via Pushover API"""

    PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
    TIMEOUT_SECONDS = 5
    THROTTLE_WINDOW = 60  # seconds

    def __init__(self):
        """Initialize PushoverNotifier with credentials from environment"""
        self.user_key = os.getenv('PUSHOVER_USER_KEY', '').strip()
        self.api_token = os.getenv('PUSHOVER_API_TOKEN', '').strip()

        # Check if alerts are enabled
        alert_enabled = os.getenv('PUSHOVER_ALERT_ENABLED', 'false').lower()
        self.enabled = alert_enabled == 'true' and bool(self.user_key and self.api_token)

        if not self.enabled:
            if alert_enabled == 'true':
                logger.warning("Pushover alerts enabled but credentials missing")
            else:
                logger.info("Pushover alerts disabled (PUSHOVER_ALERT_ENABLED=false)")

    def send_alert(
        self,
        title: str,
        message: str,
        priority: int = 0,
        retry: int = 300,
        expire: int = 3600
    ) -> bool:
        """
        Send alert via Pushover API

        Args:
            title: Alert title
            message: Alert message
            priority: 0=Normal, 1=High, 2=Emergency
            retry: Retry interval for emergency alerts (seconds)
            expire: Expiration time for emergency alerts (seconds)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Build payload
            payload = {
                'user': self.user_key,
                'token': self.api_token,
                'title': title,
                'message': message,
                'priority': priority,
            }

            # For emergency priority, add retry/expire
            if priority == 2:
                payload['retry'] = retry
                payload['expire'] = expire

            # Send request with timeout
            response = requests.post(
                self.PUSHOVER_API_URL,
                data=payload,
                timeout=self.TIMEOUT_SECONDS
            )

            # Check response status
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 1:
                    logger.info(f"Pushover alert sent: {title}")
                    return True
                else:
                    error_msg = result.get('errors', ['Unknown error'])[0]
                    logger.error(f"Pushover API error: {error_msg}")
                    return False
            else:
                logger.error(f"Pushover API returned {response.status_code}: {response.text}")
                return False

        except requests.Timeout:
            logger.warning("Pushover API timeout (>5 seconds), alert not sent")
            return False
        except requests.ConnectionError as e:
            logger.warning(f"Network error connecting to Pushover: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Pushover alert: {e}")
            return False


# Alias for compatibility
NotificationTool = PushoverNotifier
