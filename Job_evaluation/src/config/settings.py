import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # AI API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
    
    # Google API Configuration
    GMAIL_CREDENTIALS = os.getenv('GMAIL_CREDENTIALS', 'config/credentials/gmail_credentials.json')
    DRIVE_CREDENTIALS = os.getenv('DRIVE_CREDENTIALS', 'config/credentials/drive_credentials.json')
    SHEETS_CREDENTIALS = os.getenv('SHEETS_CREDENTIALS', 'config/credentials/gmail_credentials.json')
    GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
    
    # Gmail Configuration
    GMAIL_SEARCH_DAYS = int(os.getenv('GMAIL_SEARCH_DAYS', 7))
    JOB_ALERT_KEYWORDS = os.getenv('JOB_ALERT_KEYWORDS', 'job,position,opportunity,hiring,career').split(',')
    
    # Google Drive Folders
    ALERTS_FOLDER_ID = os.getenv('ALERTS_FOLDER_ID')
    RESULTS_FOLDER_ID = os.getenv('RESULTS_FOLDER_ID')
    REPORTS_FOLDER_ID = os.getenv('REPORTS_FOLDER_ID')
    
    # Profile Configuration
    LINKEDIN_PDF_ID = os.getenv('LINKEDIN_PDF_ID')
    SUMMARY_TXT_ID = os.getenv('SUMMARY_TXT_ID')
    
    # Scoring Configuration
    MIN_MATCH_SCORE = int(os.getenv('MIN_MATCH_SCORE', 85))
    
    # Email Notifications
    NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration variables are set"""
        required_vars = [
            'OPENAI_API_KEY', 'CLAUDE_API_KEY', 'GOOGLE_SHEETS_ID',
            'LINKEDIN_PDF_ID', 'SUMMARY_TXT_ID', 'NOTIFICATION_EMAIL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True