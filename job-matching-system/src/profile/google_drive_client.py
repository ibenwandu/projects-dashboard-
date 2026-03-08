"""
Google Drive client for fetching profile documents.
"""
import os
import io
import logging
from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import PyPDF2

logger = logging.getLogger(__name__)

class GoogleDriveClient:
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, credentials_path: str, token_path: str = 'config/credentials/drive_token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API."""
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
        
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive API authenticated successfully")
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file content by ID."""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            
            import googleapiclient.http
            downloader = googleapiclient.http.MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return file_content.getvalue()
            
        except HttpError as error:
            logger.error(f"Error downloading file {file_id}: {error}")
            return None
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata."""
        try:
            file_info = self.service.files().get(fileId=file_id).execute()
            return file_info
        except HttpError as error:
            logger.error(f"Error getting file info {file_id}: {error}")
            return None
    
    def extract_pdf_text(self, file_id: str) -> Optional[str]:
        """Extract text from PDF file."""
        try:
            file_content = self.download_file(file_id)
            if not file_content:
                return None
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as error:
            logger.error(f"Error extracting PDF text from {file_id}: {error}")
            return None
    
    def download_text_file(self, file_id: str) -> Optional[str]:
        """Download and decode text file."""
        try:
            file_content = self.download_file(file_id)
            if not file_content:
                return None
            
            return file_content.decode('utf-8')
            
        except Exception as error:
            logger.error(f"Error downloading text file {file_id}: {error}")
            return None