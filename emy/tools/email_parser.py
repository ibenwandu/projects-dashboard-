"""Email parser for reading, parsing, and routing incoming emails from Gmail."""

import os
import base64
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from emy.core.database import EMyDatabase

logger = logging.getLogger(__name__)


class EmailParser:
    """Parse and route incoming emails from Gmail."""

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    # Intent keywords for classification
    INTENT_KEYWORDS = {
        'feedback': ['feedback', 'opinion', 'comment', 'suggestion', 'thoughts', 'consider'],
        'research': ['research', 'analyze', 'investigate', 'explore', 'examine', 'study'],
        'status': ['status', 'update', 'progress', 'report', 'summary', 'current'],
        'question': ['question', 'how', 'what', 'why', 'when', 'where', 'please explain']
    }

    # Agent routing rules
    AGENT_ROUTES = {
        'feedback': 'ResearchAgent',
        'research': 'KnowledgeAgent',
        'status': 'ProjectMonitorAgent',
        'question': 'KnowledgeAgent'
    }

    def __init__(self):
        """Initialize Gmail parser."""
        self._service = None
        self._db = EMyDatabase()
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Gmail API service with service account credentials."""
        try:
            creds_json = os.getenv('GMAIL_CREDENTIALS_JSON')
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=self.SCOPES
                )
                self._service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
                logger.info('Gmail parser service initialized successfully')
            else:
                logger.warning('GMAIL_CREDENTIALS_JSON not set, Gmail features will be unavailable')
                self._service = None
        except Exception as e:
            logger.error(f'Gmail parser initialization failed: {e}')
            self._service = None

    async def check_inbox(self) -> List[Dict[str, Any]]:
        """Poll Gmail inbox for new unread emails.

        Returns:
            List of email dicts with 'id' and 'threadId'
        """
        if not self._service:
            logger.warning('Gmail service not initialized')
            return []

        try:
            results = self._service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=10
            ).execute()

            messages = results.get('messages', [])
            logger.info(f'Found {len(messages)} unread emails')
            return messages
        except HttpError as e:
            logger.error(f'Error checking inbox: {e}')
            return []
        except Exception as e:
            logger.error(f'Unexpected error checking inbox: {e}')
            return []

    async def parse_email(self, email_id: str) -> Dict[str, Any]:
        """Extract sender, subject, body from email.

        Args:
            email_id: Gmail message ID

        Returns:
            Dict with 'sender', 'subject', 'body', 'email_id'
        """
        if not self._service:
            logger.warning('Gmail service not initialized')
            return {}

        try:
            message = self._service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()

            headers = message['payload'].get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')

            body = self._extract_body(message['payload'])

            return {
                'email_id': email_id,
                'sender': sender,
                'subject': subject,
                'body': body
            }
        except HttpError as e:
            logger.error(f'Error parsing email {email_id}: {e}')
            return {}
        except Exception as e:
            logger.error(f'Unexpected error parsing email {email_id}: {e}')
            return {}

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract body text from email payload.

        Handles both multipart and simple email formats.

        Args:
            payload: Email payload dict from Gmail API

        Returns:
            Email body text (decoded from base64)
        """
        try:
            # Handle multipart emails
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')

            # Handle simple text emails
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')

            return ''
        except Exception as e:
            logger.error(f'Error extracting body: {e}')
            return ''

    async def classify_intent(self, email: Dict[str, Any]) -> str:
        """Classify email intent based on subject and body keywords.

        Args:
            email: Parsed email dict with 'subject' and 'body'

        Returns:
            Intent type: 'feedback', 'research', 'status', 'question', or 'other'
        """
        try:
            text = (f"{email.get('subject', '')} {email.get('body', '')}").lower()

            # Count keyword matches for each intent
            scores = {}
            for intent, keywords in self.INTENT_KEYWORDS.items():
                score = sum(1 for kw in keywords if kw in text)
                scores[intent] = score

            # Return highest scoring intent, or 'other' if no matches
            max_score = max(scores.values(), default=0)
            if max_score > 0:
                return max(scores, key=scores.get)

            return 'other'
        except Exception as e:
            logger.error(f'Error classifying intent: {e}')
            return 'other'

    async def route_to_agent(self, email: Dict[str, Any]) -> str:
        """Route email to appropriate agent based on intent.

        Args:
            email: Parsed email dict with 'intent' key

        Returns:
            Agent name: 'ResearchAgent', 'ProjectMonitorAgent', or 'KnowledgeAgent'
        """
        try:
            intent = email.get('intent', 'other')
            agent = self.AGENT_ROUTES.get(intent, 'KnowledgeAgent')
            logger.info(f'Routing email with intent "{intent}" to {agent}')
            return agent
        except Exception as e:
            logger.error(f'Error routing to agent: {e}')
            return 'KnowledgeAgent'

    async def log_email(self, email: Dict[str, Any], status: str = 'received'):
        """Log received email in database.

        Args:
            email: Parsed email dict
            status: Email status ('received', 'processed')
        """
        try:
            self._db.execute("""
                INSERT INTO email_log
                (email_id, direction, sender, subject, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                email.get('email_id', ''),
                'inbound',
                email.get('sender', ''),
                email.get('subject', ''),
                status
            ))
            logger.info(f'Logged email {email.get("email_id")} with status {status}')
        except Exception as e:
            logger.error(f'Error logging email: {e}')
