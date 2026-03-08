#!/usr/bin/env python3
"""
Gmail Inbox Summarizer
Fetches emails from the past 24 hours and creates an AI-powered summary.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

import openai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_summarizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GmailSummarizer:
    def __init__(self):
        self.service = None
        self.openai_client = None
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'sender_email': os.getenv('SENDER_EMAIL'),
            'sender_password': os.getenv('SENDER_PASSWORD'),
            'recipient_email': os.getenv('RECIPIENT_EMAIL'),
            'credentials_file': os.getenv('GMAIL_CREDENTIALS', 'credentials.json'),
            'token_file': os.getenv('GMAIL_TOKEN', 'token.json')
        }
    
    def authenticate_gmail(self):
        """Authenticate with Gmail API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.config['token_file']):
            creds = Credentials.from_authorized_user_file(self.config['token_file'], SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config['credentials_file'], SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.config['token_file'], 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API authenticated successfully")
    
    def fetch_recent_emails(self) -> List[Dict[str, Any]]:
        """Fetch emails from the past 24 hours."""
        try:
            # Calculate 24 hours ago
            yesterday = datetime.now() - timedelta(days=1)
            query = f'in:inbox newer_than:1d'
            
            # Search for emails
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=100).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} emails from the past 24 hours")
            
            emails = []
            for message in messages[:50]:  # Limit to 50 most recent
                try:
                    msg = self.service.users().messages().get(
                        userId='me', id=message['id'], format='full').execute()
                    
                    email_data = self._extract_email_data(msg)
                    if email_data:
                        emails.append(email_data)
                        
                except HttpError as e:
                    logger.error(f"Error fetching message {message['id']}: {e}")
            
            return emails
            
        except HttpError as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _extract_email_data(self, message: Dict) -> Dict[str, Any]:
        """Extract relevant data from Gmail message."""
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Extract body
        body = self._extract_body(message['payload'])
        
        # Get snippet
        snippet = message.get('snippet', '')
        
        return {
            'sender': sender,
            'subject': subject,
            'date': date,
            'body': body[:1000] if body else snippet,  # Limit body length
            'snippet': snippet,
            'message_id': message['id']
        }
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload.get('body', {}).get('data')
                if data:
                    import base64
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    def generate_summary(self, emails: List[Dict[str, Any]]) -> str:
        """Generate AI-powered summary of emails."""
        if not emails:
            return "No emails found in the past 24 hours."
        
        # Initialize OpenAI client
        openai.api_key = self.config['openai_api_key']
        
        # Prepare email data for summarization
        email_texts = []
        for email in emails:
            email_text = f"From: {email['sender']}\nSubject: {email['subject']}\nContent: {email['body'][:500]}\n---"
            email_texts.append(email_text)
        
        combined_emails = "\n\n".join(email_texts)
        
        # Create summary prompt
        prompt = f"""
        Please create a concise summary of the following {len(emails)} emails from the past 24 hours.
        Organize the summary by:
        1. Important/urgent emails that need attention
        2. Regular emails grouped by topic or sender
        3. Overall statistics (total emails, top senders)
        
        Keep the summary professional and actionable.
        
        Emails:
        {combined_emails}
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            logger.info("Email summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self._create_fallback_summary(emails)
    
    def _create_fallback_summary(self, emails: List[Dict[str, Any]]) -> str:
        """Create a basic summary without AI."""
        if not emails:
            return "No emails found in the past 24 hours."
        
        senders = {}
        subjects = []
        
        for email in emails:
            sender = email['sender'].split('<')[0].strip()
            senders[sender] = senders.get(sender, 0) + 1
            subjects.append(email['subject'])
        
        top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]
        
        summary = f"""📧 Gmail Inbox Summary - Past 24 Hours
        
📊 Statistics:
• Total emails: {len(emails)}
• Unique senders: {len(senders)}

👥 Top Senders:
"""
        for sender, count in top_senders:
            summary += f"• {sender}: {count} emails\n"
        
        summary += f"\n📝 Recent Subjects:\n"
        for subject in subjects[:10]:
            summary += f"• {subject}\n"
        
        return summary
    
    def send_summary(self, summary: str):
        """Send the summary via email."""
        try:
            msg = MimeMultipart()
            msg['From'] = self.config['sender_email']
            msg['To'] = self.config['recipient_email']
            msg['Subject'] = f"📧 Daily Gmail Summary - {datetime.now().strftime('%Y-%m-%d')}"
            
            msg.attach(MimeText(summary, 'plain'))
            
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['sender_email'], self.config['sender_password'])
            
            text = msg.as_string()
            server.sendmail(self.config['sender_email'], self.config['recipient_email'], text)
            server.quit()
            
            logger.info("Summary email sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    def run(self):
        """Main execution method."""
        try:
            logger.info("Starting Gmail summarization process")
            
            # Authenticate with Gmail
            self.authenticate_gmail()
            
            # Fetch recent emails
            emails = self.fetch_recent_emails()
            
            # Generate summary
            summary = self.generate_summary(emails)
            
            # Send summary
            self.send_summary(summary)
            
            logger.info("Gmail summarization completed successfully")
            
        except Exception as e:
            logger.error(f"Error in main execution: {e}")


if __name__ == "__main__":
    summarizer = GmailSummarizer()
    summarizer.run()