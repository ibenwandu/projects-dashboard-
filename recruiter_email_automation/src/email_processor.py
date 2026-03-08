"""Gmail API integration for fetching emails"""

import os
import base64
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class EmailProcessor:
    """Handle Gmail API operations"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        """Initialize Gmail service"""
        # Get project root directory (parent of src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Make paths absolute if relative
        if not os.path.isabs(credentials_path):
            credentials_path = os.path.join(project_root, credentials_path)
        if not os.path.isabs(token_path):
            token_path = os.path.join(project_root, token_path)
        
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {self.credentials_path}. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for future runs
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def get_emails_last_24h(self) -> List[Dict[str, Any]]:
        """Retrieve emails from the last 24 hours"""
        try:
            # Search for emails newer than 24 hours
            query = 'newer_than:1d in:inbox'
            
            # Get message IDs
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # Get detailed email data
            emails = []
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me', id=message['id'], format='full'
                    ).execute()
                    
                    email_data = self._parse_email(msg)
                    if email_data:
                        emails.append(email_data)
                except HttpError as e:
                    print(f"Error fetching message {message['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return []
    
    def _parse_email(self, message: Dict) -> Dict[str, Any]:
        """Parse email message and extract relevant information"""
        try:
            payload = message['payload']
            headers = payload.get('headers', [])
            
            # Extract headers
            email_data = {
                'id': message['id'],
                'thread_id': message.get('threadId', ''),
                'date_received': '',
                'sender_name': '',
                'sender_email': '',
                'subject': '',
                'body': '',
                'snippet': message.get('snippet', '')
            }
            
            # Parse headers
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'from':
                    # Parse sender name and email
                    match = re.match(r'^(.*?)\s*<(.+?)>$', value)
                    if match:
                        email_data['sender_name'] = match.group(1).strip().strip('"')
                        email_data['sender_email'] = match.group(2).strip()
                    else:
                        email_data['sender_email'] = value.strip()
                        email_data['sender_name'] = value.split('@')[0]
                
                elif name == 'subject':
                    email_data['subject'] = value
                
                elif name == 'date':
                    email_data['date_received'] = value
            
            # Extract body
            body = self._extract_body(payload)
            email_data['body'] = body
            
            return email_data
            
        except Exception as e:
            print(f"Error parsing email: {e}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html':
                    # Fallback to HTML if plain text not available
                    if not body:
                        data = part['body'].get('data', '')
                        if data:
                            html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            # Simple HTML tag removal
                            body = re.sub(r'<[^>]+>', '', html_body)
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif payload['mimeType'] == 'text/html':
                data = payload['body'].get('data', '')
                if data:
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    body = re.sub(r'<[^>]+>', '', html_body)
        
        # Clean up the body
        body = re.sub(r'\r\n|\n|\r', ' ', body)
        body = re.sub(r'\s+', ' ', body)
        return body.strip()

