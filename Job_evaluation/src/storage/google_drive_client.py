import os
import logging
import json
from typing import Optional, Dict, List
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO, StringIO
from src.config import Config

class GoogleDriveClient:
    SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata'
]
    
    def __init__(self):
        self.config = Config()
        self.service = None
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        try:
            creds = None
            token_path = os.path.join(os.path.dirname(self.config.DRIVE_CREDENTIALS), 'drive_token.json')
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.DRIVE_CREDENTIALS, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('drive', 'v3', credentials=creds)
            self.logger.info("Google Drive API authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Google Drive authentication failed: {str(e)}")
            return False
    
    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> Optional[str]:
        """Create a folder in Google Drive"""
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id,name'
            ).execute()
            
            folder_id = folder.get('id')
            self.logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as error:
            self.logger.error(f"Error creating folder '{folder_name}': {error}")
            return None
    
    def upload_file(self, file_content: str, file_name: str, folder_id: str = None, 
                   mime_type: str = 'text/plain') -> Optional[str]:
        """Upload file content to Google Drive"""
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            # Create file metadata
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create media upload
            if isinstance(file_content, str):
                media = MediaIoBaseUpload(
                    BytesIO(file_content.encode('utf-8')),
                    mimetype=mime_type,
                    resumable=True
                )
            else:
                media = MediaIoBaseUpload(
                    BytesIO(file_content),
                    mimetype=mime_type,
                    resumable=True
                )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            file_id = file.get('id')
            self.logger.info(f"Uploaded file '{file_name}' with ID: {file_id}")
            return file_id
            
        except HttpError as error:
            self.logger.error(f"Error uploading file '{file_name}': {error}")
            return None
    
    def upload_raw_email(self, email_data: Dict, folder_id: str = None) -> Optional[str]:
        """Upload raw email data to Google Drive"""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sender_name = email_data.get('sender', {}).get('name', 'unknown')
            file_name = f"email_{timestamp}_{sender_name}_{email_data.get('id', 'unknown')}.json"
            
            # Convert email data to JSON
            email_json = json.dumps(email_data, indent=2, default=str)
            
            # Upload to Drive
            file_id = self.upload_file(
                file_content=email_json,
                file_name=file_name,
                folder_id=folder_id,
                mime_type='application/json'
            )
            
            return file_id
            
        except Exception as e:
            self.logger.error(f"Error uploading raw email: {str(e)}")
            return None
    
    def upload_job_data(self, jobs: List[Dict], folder_id: str = None) -> Optional[str]:
        """Upload extracted job data to Google Drive"""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"extracted_jobs_{timestamp}.json"
            
            # Prepare job data
            job_data = {
                'extraction_time': datetime.now().isoformat(),
                'total_jobs': len(jobs),
                'jobs': jobs
            }
            
            # Convert to JSON
            jobs_json = json.dumps(job_data, indent=2, default=str)
            
            # Upload to Drive
            file_id = self.upload_file(
                file_content=jobs_json,
                file_name=file_name,
                folder_id=folder_id,
                mime_type='application/json'
            )
            
            return file_id
            
        except Exception as e:
            self.logger.error(f"Error uploading job data: {str(e)}")
            return None
    
    def get_or_create_alerts_folder(self) -> Optional[str]:
        """Get or create the Alerts folder in Google Drive"""
        try:
            # Check if alerts folder ID is configured
            if self.config.ALERTS_FOLDER_ID and self.config.ALERTS_FOLDER_ID != 'google_drive_alerts_folder_id':
                return self.config.ALERTS_FOLDER_ID
            
            # Search for existing Alerts folder
            folder_id = self.find_folder_by_name('Alerts')
            if folder_id:
                self.logger.info(f"Found existing Alerts folder: {folder_id}")
                return folder_id
            
            # Create new Alerts folder
            folder_id = self.create_folder('Alerts')
            if folder_id:
                self.logger.info(f"Created new Alerts folder: {folder_id}")
                # TODO: Update .env file with new folder ID
            
            return folder_id
            
        except Exception as e:
            self.logger.error(f"Error getting/creating Alerts folder: {str(e)}")
            return None
    
    def get_or_create_results_folder(self) -> Optional[str]:
        """Get or create the Results folder under Job_evaluation"""
        try:
            # Check if results folder ID is configured
            if self.config.RESULTS_FOLDER_ID and self.config.RESULTS_FOLDER_ID != 'google_drive_results_folder_id':
                return self.config.RESULTS_FOLDER_ID
            
            # Search for Job_evaluation folder first
            job_eval_folder = self.find_folder_by_name('Job_evaluation')
            if not job_eval_folder:
                job_eval_folder = self.create_folder('Job_evaluation')
            
            if job_eval_folder:
                # Search for Results folder inside Job_evaluation
                results_folder = self.find_folder_by_name('Result', job_eval_folder)
                if not results_folder:
                    results_folder = self.create_folder('Result', job_eval_folder)
                
                return results_folder
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting/creating Results folder: {str(e)}")
            return None
    
    def get_or_create_reports_folder(self) -> Optional[str]:
        """Get or create the Reports folder under Job_evaluation"""
        try:
            # Check if reports folder ID is configured
            if self.config.REPORTS_FOLDER_ID and self.config.REPORTS_FOLDER_ID != 'google_drive_reports_folder_id':
                return self.config.REPORTS_FOLDER_ID
            
            # Search for Job_evaluation folder first
            job_eval_folder = self.find_folder_by_name('Job_evaluation')
            if not job_eval_folder:
                job_eval_folder = self.create_folder('Job_evaluation')
            
            if job_eval_folder:
                # Search for Reports folder inside Job_evaluation
                reports_folder = self.find_folder_by_name('Reports', job_eval_folder)
                if not reports_folder:
                    reports_folder = self.create_folder('Reports', job_eval_folder)
                
                return reports_folder
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting/creating Reports folder: {str(e)}")
            return None
    
    def find_folder_by_name(self, folder_name: str, parent_folder_id: str = None) -> Optional[str]:
        """Find folder by name in Google Drive"""
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            
            return None
            
        except HttpError as error:
            self.logger.error(f"Error finding folder '{folder_name}': {error}")
            return None
    
    def download_file(self, file_id: str) -> Optional[str]:
        """Download file content from Google Drive"""
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            file = self.service.files().get_media(fileId=file_id).execute()
            return file.decode('utf-8')
            
        except HttpError as error:
            self.logger.error(f"Error downloading file {file_id}: {error}")
            return None
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """List files in a specific folder"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            query = f"'{folder_id}' in parents"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, createdTime, modifiedTime)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as error:
            self.logger.error(f"Error listing files in folder {folder_id}: {error}")
            return []