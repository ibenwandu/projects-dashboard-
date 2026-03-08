import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.config import Config
import os

class SheetsManager:
    """Manages Google Sheets operations for job data"""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self):
        self.config = Config()
        self.service = None
        self.logger = logging.getLogger(__name__)
        
        # Sheet structure with new sender column
        self.headers = [
            'Score', 'Job Title', 'Company', 'Location', 'Application Link', 
            'Sender', 'Match Reasoning', 'Apply', 'Resume Status', 
            'Generated Date', 'Resume Link', 'Email Date', 'Source Type'
        ]
    
    def authenticate(self) -> bool:
        """Authenticate with Google Sheets API"""
        try:
            creds = None
            token_path = os.path.join(os.path.dirname(self.config.SHEETS_CREDENTIALS), 'sheets_token.json')
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.SHEETS_CREDENTIALS, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('sheets', 'v4', credentials=creds)
            self.logger.info("Google Sheets API authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Google Sheets authentication failed: {str(e)}")
            return False
    
    def setup_sheet_headers(self) -> bool:
        """Setup or update sheet headers with sender column"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            # Check if sheet exists and get current headers
            current_headers = self.get_sheet_headers()
            
            if not current_headers or current_headers != self.headers:
                # Update headers
                self.logger.info("Updating sheet headers with sender column")
                
                body = {
                    'values': [self.headers]
                }
                
                result = self.service.spreadsheets().values().update(
                    spreadsheetId=self.config.GOOGLE_SHEETS_ID,
                    range='A1:M1',  # Extended range for new columns
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                self.logger.info(f"Updated {result.get('updatedCells')} header cells")
                
                # Format headers (make bold)
                self._format_headers()
            
            return True
            
        except HttpError as error:
            self.logger.error(f"Error setting up sheet headers: {error}")
            return False
    
    def get_sheet_headers(self) -> List[str]:
        """Get current sheet headers"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.config.GOOGLE_SHEETS_ID,
                range='A1:M1'
            ).execute()
            
            values = result.get('values', [])
            return values[0] if values else []
            
        except HttpError as error:
            self.logger.error(f"Error getting sheet headers: {error}")
            return []
    
    def add_jobs_to_sheet(self, evaluated_jobs: List[Dict]) -> Dict:
        """Add evaluated jobs to Google Sheets"""
        results = {
            'success': False,
            'added_count': 0,
            'skipped_count': 0,
            'errors': []
        }
        
        if not self.service:
            if not self.authenticate():
                results['errors'].append("Failed to authenticate with Google Sheets")
                return results
        
        try:
            # Setup headers first
            if not self.setup_sheet_headers():
                results['errors'].append("Failed to setup sheet headers")
                return results
            
            # Filter high-scoring jobs
            high_scoring_jobs = [
                job for job in evaluated_jobs 
                if job.get('match_score', 0) >= self.config.MIN_MATCH_SCORE
            ]
            
            if not high_scoring_jobs:
                self.logger.info("No high-scoring jobs to add to sheet")
                results['success'] = True
                return results
            
            # Get existing jobs to avoid duplicates
            existing_jobs = self.get_existing_jobs()
            existing_urls = {job.get('url', '') for job in existing_jobs}
            
            # Prepare new rows
            new_rows = []
            for job in high_scoring_jobs:
                job_url = job.get('url', '')
                
                # Skip if job already exists
                if job_url and job_url in existing_urls:
                    results['skipped_count'] += 1
                    continue
                
                # Prepare row data
                row = self._prepare_job_row(job)
                new_rows.append(row)
                results['added_count'] += 1
            
            if new_rows:
                # Add rows to sheet
                self._append_rows_to_sheet(new_rows)
                self.logger.info(f"Added {len(new_rows)} new jobs to Google Sheets")
            
            results['success'] = True
            
        except Exception as e:
            error_msg = f"Error adding jobs to sheet: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def _prepare_job_row(self, job: Dict) -> List[Any]:
        """Prepare a job data row for the sheet"""
        # Extract sender information
        sender_info = job.get('sender', {})
        if isinstance(sender_info, dict):
            sender_display = f"{sender_info.get('name', '')} ({sender_info.get('email', '')})"
        else:
            sender_display = str(sender_info)
        
        # Format email date
        email_date = job.get('email_date', '')
        if isinstance(email_date, datetime):
            email_date = email_date.strftime('%Y-%m-%d %H:%M')
        
        row = [
            job.get('match_score', 0),                    # Score
            job.get('title', ''),                         # Job Title
            job.get('company', ''),                       # Company
            job.get('location', ''),                      # Location
            job.get('url', ''),                          # Application Link
            sender_display,                               # Sender (NEW COLUMN)
            job.get('feedback', '')[:200] + '...' if len(job.get('feedback', '')) > 200 else job.get('feedback', ''),  # Match Reasoning (truncated)
            False,                                        # Apply (checkbox - will be formatted)
            '',                                          # Resume Status
            '',                                          # Generated Date
            '',                                          # Resume Link
            email_date,                                  # Email Date
            job.get('source_type', '')                   # Source Type
        ]
        
        return row
    
    def _append_rows_to_sheet(self, rows: List[List[Any]]) -> bool:
        """Append rows to the sheet"""
        try:
            body = {
                'values': rows
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.config.GOOGLE_SHEETS_ID,
                range='A:M',  # Extended range for new columns
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            self.logger.info(f"Appended {result.get('updates', {}).get('updatedRows', 0)} rows")
            return True
            
        except HttpError as error:
            self.logger.error(f"Error appending rows to sheet: {error}")
            return False
    
    def get_existing_jobs(self) -> List[Dict]:
        """Get existing jobs from the sheet"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.config.GOOGLE_SHEETS_ID,
                range='A2:M1000'  # Skip header row, extended range
            ).execute()
            
            values = result.get('values', [])
            
            jobs = []
            for row in values:
                if len(row) >= 5:  # Minimum required columns
                    job = {
                        'score': row[0] if len(row) > 0 else '',
                        'title': row[1] if len(row) > 1 else '',
                        'company': row[2] if len(row) > 2 else '',
                        'location': row[3] if len(row) > 3 else '',
                        'url': row[4] if len(row) > 4 else '',
                        'sender': row[5] if len(row) > 5 else '',
                        'reasoning': row[6] if len(row) > 6 else '',
                        'apply': row[7] if len(row) > 7 else False,
                        'resume_status': row[8] if len(row) > 8 else '',
                        'generated_date': row[9] if len(row) > 9 else '',
                        'resume_link': row[10] if len(row) > 10 else '',
                        'email_date': row[11] if len(row) > 11 else '',
                        'source_type': row[12] if len(row) > 12 else ''
                    }
                    jobs.append(job)
            
            return jobs
            
        except HttpError as error:
            self.logger.error(f"Error getting existing jobs: {error}")
            return []
    
    def get_jobs_marked_for_application(self) -> List[Dict]:
        """Get jobs where Apply column is checked"""
        existing_jobs = self.get_existing_jobs()
        
        # Filter for jobs marked for application
        marked_jobs = [
            job for job in existing_jobs 
            if str(job.get('apply', '')).lower() in ['true', 'yes', '1', 'x']
        ]
        
        self.logger.info(f"Found {len(marked_jobs)} jobs marked for application")
        return marked_jobs
    
    def update_resume_status(self, job_url: str, status: str, 
                           resume_link: str = '', generated_date: str = '') -> bool:
        """Update resume generation status for a specific job"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            # Find the row for this job
            existing_jobs = self.get_existing_jobs()
            
            for i, job in enumerate(existing_jobs):
                if job.get('url') == job_url:
                    row_number = i + 2  # +2 because sheets are 1-indexed and we skip header
                    
                    # Update the specific cells
                    updates = []
                    
                    if status:
                        updates.append({
                            'range': f'I{row_number}',  # Resume Status column
                            'values': [[status]]
                        })
                    
                    if generated_date:
                        updates.append({
                            'range': f'J{row_number}',  # Generated Date column
                            'values': [[generated_date]]
                        })
                    
                    if resume_link:
                        updates.append({
                            'range': f'K{row_number}',  # Resume Link column
                            'values': [[resume_link]]
                        })
                    
                    # Batch update
                    if updates:
                        body = {
                            'valueInputOption': 'USER_ENTERED',
                            'data': updates
                        }
                        
                        self.service.spreadsheets().values().batchUpdate(
                            spreadsheetId=self.config.GOOGLE_SHEETS_ID,
                            body=body
                        ).execute()
                        
                        self.logger.info(f"Updated resume status for job: {job.get('title', 'Unknown')}")
                        return True
            
            self.logger.warning(f"Job with URL {job_url} not found in sheet")
            return False
            
        except HttpError as error:
            self.logger.error(f"Error updating resume status: {error}")
            return False
    
    def _format_headers(self) -> bool:
        """Format header row (make bold)"""
        try:
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': len(self.headers)
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold'
                }
            }]
            
            body = {
                'requests': requests
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.config.GOOGLE_SHEETS_ID,
                body=body
            ).execute()
            
            return True
            
        except HttpError as error:
            self.logger.error(f"Error formatting headers: {error}")
            return False
    
    def get_sheet_stats(self) -> Dict:
        """Get statistics about the sheet"""
        try:
            existing_jobs = self.get_existing_jobs()
            marked_jobs = self.get_jobs_marked_for_application()
            
            stats = {
                'total_jobs': len(existing_jobs),
                'jobs_marked_for_application': len(marked_jobs),
                'pending_resumes': len([job for job in marked_jobs if not job.get('resume_status')]),
                'completed_resumes': len([job for job in marked_jobs if job.get('resume_status') == 'Completed']),
                'average_score': 0
            }
            
            if existing_jobs:
                scores = []
                for job in existing_jobs:
                    try:
                        score = float(job.get('score', 0))
                        scores.append(score)
                    except (ValueError, TypeError):
                        continue
                
                if scores:
                    stats['average_score'] = sum(scores) / len(scores)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting sheet stats: {str(e)}")
            return {}