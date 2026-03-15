"""EmailClient for sending emails via Gmail API with retry logic and Jinja2 templates."""

import os
import asyncio
import json
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime
import base64
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader, select_autoescape
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from emy.core.database import EMyDatabase

logger = logging.getLogger(__name__)


class EmailClient:
    """Gmail API client for sending emails with retry logic and template rendering."""

    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    RETRY_ATTEMPTS = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s

    def __init__(self):
        """Initialize Gmail API client and Jinja2 environment."""
        self._service = None
        self._db = EMyDatabase()
        self._jinja_env = None
        self._initialize_service()
        self._initialize_templates()

    def _initialize_service(self):
        """Initialize Gmail API service with OAuth credentials."""
        try:
            creds_json = os.getenv('GMAIL_CREDENTIALS_JSON')
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=self.SCOPES
                )
                self._service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
            else:
                logger.warning("GMAIL_CREDENTIALS_JSON not set, Gmail features will be unavailable")
        except Exception as e:
            logger.error(f"Gmail service initialization failed: {e}")
            self._service = None

    def _initialize_templates(self):
        """Initialize Jinja2 template environment."""
        try:
            # Get the directory where this file is located
            tools_dir = Path(__file__).parent.parent
            templates_dir = tools_dir / 'templates'

            self._jinja_env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except Exception as e:
            logger.error(f"Jinja2 environment initialization failed: {e}")
            self._jinja_env = None

    async def render_template(self, template_name: str, context: dict) -> str:
        """
        Render Jinja2 template with provided context.

        Args:
            template_name: Name of template file (e.g., 'emails/feasibility_assessment.jinja2')
            context: Dictionary of variables to render in template

        Returns:
            Rendered HTML string
        """
        if not self._jinja_env:
            return ""

        try:
            template = self._jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering failed for '{template_name}': {e}")
            raise

    async def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = True,
        email_id: Optional[str] = None
    ) -> bool:
        """
        Send email via Gmail API with 3-attempt retry logic.

        Retry backoff: 1s → 2s → 4s (exponential backoff)

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            html: Whether body is HTML (default: True)
            email_id: Optional email ID for logging (auto-generated if not provided)

        Returns:
            True if sent successfully, False if all retries failed
        """
        if not self._service:
            return False

        if not email_id:
            email_id = f"emy_{datetime.now().timestamp()}"

        # Create MIME message
        message = MIMEText(body, 'html' if html else 'plain')
        message['to'] = to
        message['subject'] = subject

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Try sending with retry logic
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                result = self._service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

                # Success - log and return
                await self._log_success(email_id, to, subject)
                return True

            except (HttpError, Exception) as e:
                error_msg = str(e)

                if attempt < self.RETRY_ATTEMPTS - 1:
                    # Wait before retry
                    delay = self.RETRY_DELAYS[attempt]
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed - log failure
                    await self._log_failure(email_id, to, subject, error_msg, attempt + 1)
                    return False

        return False

    async def _log_success(self, email_id: str, recipient: str, subject: str):
        """Log successful email send."""
        try:
            self._db.log_email(
                email_id=email_id,
                direction='outbound',
                recipient=recipient,
                subject=subject,
                status='sent',
                attempt_count=1
            )
        except Exception as e:
            logger.error(f"Failed to log successful email send: {e}")

    async def _log_failure(self, email_id: str, recipient: str, subject: str,
                           error_msg: str, attempt_count: int):
        """Log failed email send and alert."""
        try:
            self._db.log_email(
                email_id=email_id,
                direction='outbound',
                recipient=recipient,
                subject=subject,
                status='failed',
                attempt_count=attempt_count,
                error_message=error_msg
            )

            # Alert user after max retries
            await self._alert_after_failure(email_id, recipient, subject, error_msg)

        except Exception as e:
            logger.error(f"Failed to log email failure: {e}")

    async def _alert_after_failure(self, email_id: str, recipient: str,
                                   subject: str, error_msg: str):
        """Create alert notification after 3 failed send attempts."""
        try:
            alert_title = f"Email Send Failed: {subject}"
            alert_message = f"Failed to send email to {recipient} after 3 attempts. Error: {error_msg}"

            self._db.log_alert(
                alert_type='email_send_failed',
                title=alert_title,
                message=alert_message,
                priority=1  # High priority
            )

        except Exception as e:
            logger.error(f"Failed to create alert notification: {e}")
