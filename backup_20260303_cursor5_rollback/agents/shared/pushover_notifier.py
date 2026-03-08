"""
Pushover notification integration.

Sends Pushover alerts for:
- Agent workflow events
- Approval decisions
- Errors and warnings
"""

import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class PushoverNotifier:
    """Sends notifications via Pushover API."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        user_key: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize Pushover notifier.

        Args:
            api_token: Pushover app token (from env or parameter)
            user_key: Pushover user key (from env or parameter)
            enabled: Whether notifications are enabled
        """
        self.api_token = api_token or os.getenv("PUSHOVER_API_TOKEN", "")
        self.user_key = user_key or os.getenv("PUSHOVER_USER_KEY", "")
        self.enabled = enabled and bool(self.api_token and self.user_key)
        self.api_url = "https://api.pushover.net/1/messages.json"

    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.enabled

    def send(
        self,
        title: str,
        message: str,
        priority: int = 0,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        sound: Optional[str] = None
    ) -> bool:
        """
        Send Pushover notification.

        Args:
            title: Notification title
            message: Notification message
            priority: Priority level (-2 to 2, where 2 requires acknowledgment)
            url: Optional URL to include
            url_title: Optional URL title
            sound: Optional sound (pushover, bike, bugle, cashregister, etc.)

        Returns:
            Success flag
        """
        if not self.enabled:
            return False

        try:
            payload = {
                "token": self.api_token,
                "user": self.user_key,
                "title": title[:255],  # Max 255 chars
                "message": message[:1024],  # Max 1024 chars
                "priority": priority,
                "timestamp": int(datetime.utcnow().timestamp())
            }

            if url:
                payload["url"] = url
            if url_title:
                payload["url_title"] = url_title
            if sound:
                payload["sound"] = sound

            response = requests.post(self.api_url, data=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️  Pushover notification failed: {e}")
            return False

    def notify_workflow_started(self, cycle_number: int) -> bool:
        """Notify workflow started."""
        return self.send(
            title="🚀 Agent Workflow Started",
            message=f"Cycle {cycle_number}: Analyst → Expert → Coder → Approval",
            priority=0
        )

    def notify_analysis_complete(self, cycle_number: int, trades_reviewed: int) -> bool:
        """Notify analysis completed."""
        return self.send(
            title="📊 Analysis Complete",
            message=f"Cycle {cycle_number}: Reviewed {trades_reviewed} trades",
            priority=0
        )

    def notify_approval_pending(
        self,
        cycle_number: int,
        test_coverage: float,
        risk_assessment: str,
        approval_url: Optional[str] = None
    ) -> bool:
        """Notify user approval needed."""
        coverage_pct = int(test_coverage * 100)
        title = f"⏳ Cycle {cycle_number}: Approval Needed"
        message = f"Coverage: {coverage_pct}% | Risk: {risk_assessment}\n\nReview and approve implementation"

        return self.send(
            title=title,
            message=message,
            priority=1,  # High priority
            url=approval_url,
            url_title="Approve / Reject"
        )

    def notify_auto_approved(self, cycle_number: int, test_coverage: float) -> bool:
        """Notify auto-approval."""
        coverage_pct = int(test_coverage * 100)
        return self.send(
            title=f"✅ Cycle {cycle_number}: Auto-Approved",
            message=f"Test Coverage: {coverage_pct}% (>95% threshold)\nReady for deployment",
            priority=0
        )

    def notify_user_approved(self, cycle_number: int, user_comment: Optional[str] = None) -> bool:
        """Notify user approval."""
        message = f"Cycle {cycle_number}: Approved by you"
        if user_comment:
            message += f"\n\nYour comment: {user_comment[:100]}"

        return self.send(
            title="✅ Implementation Approved",
            message=message,
            priority=0
        )

    def notify_rejected(self, cycle_number: int, reason: str) -> bool:
        """Notify rejection."""
        return self.send(
            title=f"❌ Cycle {cycle_number}: Rejected",
            message=f"Reason: {reason[:200]}",
            priority=0
        )

    def notify_deployment_started(self, cycle_number: int, environment: str) -> bool:
        """Notify deployment started."""
        return self.send(
            title=f"🚢 Deploying Cycle {cycle_number}",
            message=f"Deploying to {environment} environment",
            priority=0
        )

    def notify_deployment_complete(self, cycle_number: int) -> bool:
        """Notify deployment complete."""
        return self.send(
            title=f"✅ Cycle {cycle_number}: Deployed",
            message="Changes deployed to production. Monitoring for 48 hours.",
            priority=0
        )

    def notify_error(self, cycle_number: int, agent: str, error_message: str) -> bool:
        """Notify error."""
        return self.send(
            title=f"❌ Error: {agent}",
            message=f"Cycle {cycle_number}: {error_message[:200]}",
            priority=2  # Emergency - requires acknowledgment
        )

    def notify_workflow_complete(
        self,
        cycle_number: int,
        duration_minutes: float,
        status: str
    ) -> bool:
        """Notify workflow completion."""
        status_emoji = "✅" if status == "SUCCESS" else "⚠️"
        return self.send(
            title=f"{status_emoji} Cycle {cycle_number}: Workflow Complete",
            message=f"Duration: {duration_minutes:.1f} minutes | Status: {status}",
            priority=0
        )

    def notify_rollback(self, cycle_number: int, reason: str) -> bool:
        """Notify rollback."""
        return self.send(
            title=f"⏮️ Rollback: Cycle {cycle_number}",
            message=f"Reason: {reason[:200]}",
            priority=1  # High priority
        )

    def test_connection(self) -> bool:
        """Test Pushover connection."""
        return self.send(
            title="🔧 Test Notification",
            message="Pushover integration is working correctly",
            priority=0
        )


# Global notifier instance
_notifier_instance: Optional[PushoverNotifier] = None


def get_pushover_notifier(
    api_token: Optional[str] = None,
    user_key: Optional[str] = None
) -> PushoverNotifier:
    """Get or create global Pushover notifier instance."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = PushoverNotifier(api_token, user_key)
    return _notifier_instance
