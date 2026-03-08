import os
import pickle
import base64
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.config import Config

class GmailClient:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self):
        self.config = Config()
        self.service = None
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        try:
            creds = None
            token_path = os.path.join(os.path.dirname(self.config.GMAIL_CREDENTIALS), 'gmail_token.json')
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.GMAIL_CREDENTIALS, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=creds)
            self.logger.info("Gmail API authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Gmail authentication failed: {str(e)}")
            return False
    
    def get_recent_emails(self, days: int = None) -> List[Dict]:
        """Retrieve emails from the last N days"""
        if not self.service:
            if not self.authenticate():
                return []
        
        days = days or self.config.GMAIL_SEARCH_DAYS
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for Gmail search query
            start_str = start_date.strftime('%Y/%m/%d')
            end_str = end_date.strftime('%Y/%m/%d')
            
            # Build search query
            query = f'after:{start_str} before:{end_str}'
            
            # Add keyword filters
            keyword_query = ' OR '.join([f'subject:{keyword}' for keyword in self.config.JOB_ALERT_KEYWORDS])
            query += f' ({keyword_query})'
            
            self.logger.info(f"Searching emails with query: {query}")
            
            # Search emails
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            ).execute()
            
            messages = result.get('messages', [])
            self.logger.info(f"Found {len(messages)} emails matching criteria")
            
            # Get full message details
            emails = []
            for message in messages:
                email_data = self._get_email_details(message['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            self.logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            self.logger.error(f"Error retrieving emails: {str(e)}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed information for a specific email"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            header_dict = {header['name'].lower(): header['value'] for header in headers}
            
            # Extract body
            body = self._extract_email_body(message['payload'])
            
            # Get snippet
            snippet = message.get('snippet', '')
            
            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'subject': header_dict.get('subject', ''),
                'sender': header_dict.get('from', ''),
                'date': header_dict.get('date', ''),
                'body': body,
                'snippet': snippet,
                'labels': message.get('labelIds', []),
                'internal_date': message.get('internalDate', ''),
                'raw_message': message
            }
            
            return email_data
            
        except Exception as e:
            self.logger.error(f"Error getting email details for {message_id}: {str(e)}")
            return None
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        else:
            if payload['mimeType'] == 'text/html' and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body
    
    def is_job_alert(self, email: Dict) -> bool:
        """Check if an email is a job alert"""
        subject = email.get('subject', '').lower()
        sender = email.get('sender', '').lower()
        body = email.get('body', '').lower()
        snippet = email.get('snippet', '').lower()
        
        # Common job alert senders
        job_senders = [
            'linkedin', 'indeed', 'glassdoor', 'monster', 'ziprecruiter',
            'jobleads', 'workopolis', 'careerbuilder', 'simplyhired'
        ]
        
        # Check sender
        for job_sender in job_senders:
            if job_sender in sender:
                return True
        
        # Check subject and content for job-related keywords
        job_keywords = [
            'job alert', 'new jobs', 'job notification', 'job opportunity',
            'position available', 'hiring', 'career opportunity', 'job match',
            'recommended jobs', 'jobs for you'
        ]
        
        content_to_check = f"{subject} {snippet} {body[:500]}"
        
        for keyword in job_keywords:
            if keyword in content_to_check:
                return True
        
        return False