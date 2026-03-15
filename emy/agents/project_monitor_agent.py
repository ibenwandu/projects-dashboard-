"""
ProjectMonitorAgent - monitors all Render services.

Checks health of Trade-Alerts, Scalp-Engine, and other services running on Render.
Sends alerts on downtime or anomalies.
"""

import logging
from typing import Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger('ProjectMonitor')


class ProjectMonitorAgent:
    """Agent for monitoring Render services and project health."""

    def __init__(self):
        """Initialize project monitor agent."""
        self.logger = logging.getLogger('ProjectMonitor')
        self.services = [
            'trade-alerts',
            'scalp-engine',
            'job-search-api',
        ]
        from emy.tools.email_tool import EmailClient
        self.email_client = EmailClient()

    def run(self, task_id: int = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Monitor all project services.

        Args:
            task_id: Associated task ID in database

        Returns:
            (success, results) tuple
        """
        try:
            self.logger.info("[RUN] ProjectMonitorAgent starting")

            # Check disable guard
            from emy.core.disable_guard import EMyDisableGuard
            disable_guard = EMyDisableGuard()
            if disable_guard.is_disabled():
                return False, {'error': 'Emy disabled'}

            results = {
                'timestamp': self._get_timestamp(),
                'services_checked': len(self.services),
                'services': {},
                'all_healthy': True,
                'alerts_sent': 0
            }

            # Check each service
            for service_name in self.services:
                service_status = self._check_service(service_name)
                results['services'][service_name] = service_status

                if not service_status.get('healthy'):
                    results['all_healthy'] = False
                    self._send_alert(service_name, service_status)
                    results['alerts_sent'] += 1

            self.logger.info(f"[RUN] ProjectMonitorAgent completed: all_healthy={results['all_healthy']}")
            return True, results

        except Exception as e:
            self.logger.error(f"[RUN] ProjectMonitorAgent error: {e}")
            return False, {'error': str(e)}

    def _check_service(self, service_name: str) -> Dict[str, Any]:
        """Check health of a Render service."""
        try:
            from emy.tools.api_client import RenderClient

            client = RenderClient()
            status = client.get_service_status(service_name)

            if status is None:
                return {
                    'name': service_name,
                    'healthy': False,
                    'status': 'unknown',
                    'reason': 'Failed to query Render API'
                }

            return {
                'name': service_name,
                'healthy': status.get('status') == 'live',
                'status': status.get('status'),
                'region': status.get('region'),
                'last_updated': status.get('lastDeployAt')
            }

        except Exception as e:
            self.logger.error(f"[CHECK] Error checking {service_name}: {e}")
            return {
                'name': service_name,
                'healthy': False,
                'status': 'error',
                'reason': str(e)
            }

    def _send_alert(self, service_name: str, status: Dict[str, Any]):
        """Send Pushover alert for service downtime."""
        try:
            from emy.tools.notification_tool import NotificationTool

            notif = NotificationTool()
            if not notif.is_configured():
                self.logger.warning("[ALERT] Pushover not configured")
                return

            message = (
                f"Service Down: {service_name}\n"
                f"Status: {status.get('status', 'unknown')}\n"
                f"Reason: {status.get('reason', 'Unknown')}"
            )

            notif.send_alert(
                title='Emy: Service Alert',
                message=message,
                priority=1
            )
            self.logger.info(f"[ALERT] Sent alert for {service_name}")

        except Exception as e:
            self.logger.error(f"[ALERT] Error sending alert: {e}")

    async def send_daily_status_digest(self, recipient_email: str, recipient_name: str, projects: list) -> bool:
        """Send daily project status digest.

        Args:
            recipient_email: Email recipient address
            recipient_name: Name of recipient
            projects: List of projects with status

        Returns:
            True if send succeeded, False otherwise
        """
        context = {
            'recipient_name': recipient_name,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'summary': self._generate_summary(projects),
            'metrics': self._extract_metrics(projects),
            'actions_required': self._identify_actions(projects),
            'upcoming_milestones': self._get_milestones(projects)
        }

        html_body = await self.email_client.render_template('emails/daily_digest.jinja2', context)

        result = await self.email_client.send(
            to=recipient_email,
            subject=f"Daily Project Status Digest - {datetime.now().strftime('%Y-%m-%d')}",
            body=html_body,
            html=True
        )

        return result

    def _generate_summary(self, projects: list) -> str:
        """Generate summary of project status."""
        on_track = sum(1 for p in projects if p.get('status') == 'On Track')
        return f"{on_track}/{len(projects)} projects on track"

    def _extract_metrics(self, projects: list) -> list:
        """Extract metrics from projects."""
        return [
            {'name': p.get('name', 'Project'), 'value': f"{p.get('progress', 0)}% complete"}
            for p in projects
        ]

    def _identify_actions(self, projects: list) -> list:
        """Identify required actions based on project status."""
        actions = []
        for p in projects:
            if p.get('status') != 'On Track':
                actions.append(f"Review {p.get('name')} - Status: {p.get('status')}")
        return actions

    def _get_milestones(self, projects: list) -> list:
        """Get upcoming milestones."""
        return [
            {'date': '2026-03-20', 'description': 'Weekly checkpoint'},
            {'date': '2026-03-31', 'description': 'Monthly review'}
        ]

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
