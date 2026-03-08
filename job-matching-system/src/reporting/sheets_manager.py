"""
Google Sheets manager for job data and resume tracking.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

logger = logging.getLogger(__name__)

class SheetsManager:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, spreadsheet_id: str, credentials_path: str, 
                 token_path: str = 'config/credentials/sheets_token.json'):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        creds = None
        
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets API authenticated successfully")
    
    def create_headers_if_needed(self, sheet_name: str = 'Jobs'):
        """Create column headers if they don't exist."""
        headers = [
            'Score', 'Job Title', 'Company', 'Location', 'Application Link', 
            'Match Reasoning', 'Apply', 'Resume Status', 'Generated Date', 'Resume Link'
        ]
        
        try:
            # Check if headers exist
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A1:J1'
            ).execute()
            
            existing_headers = result.get('values', [[]])
            
            if not existing_headers or len(existing_headers[0]) < len(headers):
                # Add headers
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A1:J1',
                    valueInputOption='RAW',
                    body={'values': [headers]}
                ).execute()
                logger.info(f"Headers created in sheet '{sheet_name}'")
                
        except HttpError as error:
            logger.error(f"Error creating headers: {error}")
    
    def add_job_data(self, job_data: List[Dict[str, Any]], sheet_name: str = 'Jobs'):
        """Add job data to the spreadsheet."""
        try:
            self.create_headers_if_needed(sheet_name)
            
            # Convert job data to rows
            rows = []
            for job in job_data:
                row = [
                    job.get('score', ''),
                    job.get('title', ''),
                    job.get('company', ''),
                    job.get('location', ''),
                    job.get('application_link', ''),
                    job.get('match_reasoning', ''),
                    False,  # Apply checkbox
                    '',     # Resume Status
                    '',     # Generated Date
                    ''      # Resume Link
                ]
                rows.append(row)
            
            if rows:
                # Find next empty row
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A:A'
                ).execute()
                
                values = result.get('values', [])
                next_row = len(values) + 1
                
                # Add data
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A{next_row}:J{next_row + len(rows) - 1}',
                    valueInputOption='RAW',
                    body={'values': rows}
                ).execute()
                
                logger.info(f"Added {len(rows)} jobs to sheet '{sheet_name}'")
                
        except HttpError as error:
            logger.error(f"Error adding job data: {error}")
    
    def get_jobs_to_apply(self, sheet_name: str = 'Jobs') -> List[Dict[str, Any]]:
        """Get jobs where Apply checkbox is checked but Resume Status is empty."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:J'
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return []
            
            headers = values[0]
            jobs_to_apply = []
            
            for i, row in enumerate(values[1:], start=2):
                if len(row) >= 7:  # Ensure we have enough columns
                    apply_checked = row[6] if len(row) > 6 else False
                    resume_status = row[7] if len(row) > 7 else ''
                    
                    # Check if Apply is checked and Resume Status is empty
                    if str(apply_checked).lower() in ['true', '1', 'yes'] and not resume_status:
                        job_data = {
                            'row_number': i,
                            'score': row[0] if len(row) > 0 else '',
                            'title': row[1] if len(row) > 1 else '',
                            'company': row[2] if len(row) > 2 else '',
                            'location': row[3] if len(row) > 3 else '',
                            'application_link': row[4] if len(row) > 4 else '',
                            'match_reasoning': row[5] if len(row) > 5 else ''
                        }
                        jobs_to_apply.append(job_data)
            
            return jobs_to_apply
            
        except HttpError as error:
            logger.error(f"Error getting jobs to apply: {error}")
            return []
    
    def update_resume_status(self, row_number: int, status: str, 
                           generated_date: str = '', resume_link: str = '', 
                           sheet_name: str = 'Jobs'):
        """Update resume generation status for a specific job."""
        try:
            updates = []
            
            # Resume Status (column H)
            updates.append({
                'range': f'{sheet_name}!H{row_number}',
                'values': [[status]]
            })
            
            # Generated Date (column I)
            if generated_date:
                updates.append({
                    'range': f'{sheet_name}!I{row_number}',
                    'values': [[generated_date]]
                })
            
            # Resume Link (column J)
            if resume_link:
                updates.append({
                    'range': f'{sheet_name}!J{row_number}',
                    'values': [[resume_link]]
                })
            
            # Batch update
            body = {
                'valueInputOption': 'RAW',
                'data': updates
            }
            
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"Updated resume status for row {row_number}: {status}")
            
        except HttpError as error:
            logger.error(f"Error updating resume status: {error}")
    
    def check_job_exists(self, job_title: str, company: str, sheet_name: str = 'Jobs') -> bool:
        """Check if a job already exists in the sheet."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!B:C'  # Job Title and Company columns
            ).execute()
            
            values = result.get('values', [])
            
            for row in values[1:]:  # Skip header row
                if len(row) >= 2:
                    existing_title = row[0].strip().lower()
                    existing_company = row[1].strip().lower()
                    
                    if (job_title.strip().lower() == existing_title and 
                        company.strip().lower() == existing_company):
                        return True
            
            return False
            
        except HttpError as error:
            logger.error(f"Error checking job existence: {error}")
            return False