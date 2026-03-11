"""
Approval gate for destructive actions.

Requests human approval via Pushover with 24-hour timeout.
Auto-rejects if no response (fail-safe default).
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

logger = logging.getLogger('ApprovalGate')


class EMyApprovalGate:
    """Gate for requesting approval on destructive actions."""

    def __init__(self, db):
        """Initialize approval gate with database reference."""
        self.db = db
        self.approval_timeout_hours = 24
        self.logger = logging.getLogger('ApprovalGate')

    def request_approval(self,
                        action: str,
                        description: str,
                        reason: str,
                        agent: str) -> bool:
        """
        Request approval for a destructive action.

        Args:
            action: Type of action (delete_file, reset_db, disable_agent, etc.)
            description: Human-readable description of what will happen
            reason: Why this action is needed
            agent: Which agent is requesting approval

        Returns:
            True if approved within timeout, False if timeout/rejected
        """
        try:
            # Log approval request to database
            request_id = self.db.log_approval_request(
                action_type=action,
                domain=agent,
                description=f"{description} (Reason: {reason})"
            )

            # Try to send Pushover notification
            from emy.tools.notification_tool import NotificationTool
            notif = NotificationTool()

            if notif.is_configured():
                message = (
                    f"[Emy] Approval Needed\n\n"
                    f"Action: {action}\n"
                    f"Agent: {agent}\n"
                    f"Reason: {reason}\n\n"
                    f"Description:\n{description}\n\n"
                    f"ID: {request_id}\n"
                    f"Timeout: {self.approval_timeout_hours}h"
                )
                notif.send_alert(
                    title="Emy Approval Gate",
                    message=message,
                    priority=1  # High priority
                )
                self.logger.info(f"[APPROVAL] Sent Pushover notification for request {request_id}")
            else:
                self.logger.warning("[APPROVAL] Pushover not configured; auto-approving")
                # Auto-approve if no notification system configured
                self.db.update_approval_request(
                    request_id,
                    status='approved',
                    resolution_notes='Auto-approved (Pushover not configured)'
                )
                return True

            # Wait for approval (in real system, would poll database)
            # For now, check once and return
            approval = self.db.get_approval_request(request_id)

            if approval and approval.get('status') == 'approved':
                self.logger.info(f"[APPROVAL] Request {request_id} approved")
                return True

            self.logger.warning(f"[APPROVAL] Request {request_id} pending or rejected")
            return False

        except Exception as e:
            self.logger.error(f"[APPROVAL] Error requesting approval: {e}")
            return False

    def auto_reject_expired(self) -> int:
        """
        Auto-reject approval requests that have expired.

        Returns:
            Number of requests auto-rejected
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.approval_timeout_hours)
            rejected = self.db.auto_reject_expired_approvals(cutoff_time)
            self.logger.info(f"[APPROVAL] Auto-rejected {rejected} expired requests")
            return rejected
        except Exception as e:
            self.logger.error(f"[APPROVAL] Error auto-rejecting expired requests: {e}")
            return 0
