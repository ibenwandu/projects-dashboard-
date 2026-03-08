"""
Agent 2: Resume Generation Agent
Monitors Google Sheets for jobs marked for application and generates custom resumes.
"""
import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv


from src.profile.google_drive_client import GoogleDriveClient
from src.profile.profile_manager import ProfileManager
from src.resume_generator.resume_builder import ResumeBuilder
from src.resume_generator.format_converter import FormatConverter
from src.reporting.sheets_manager import SheetsManager
from src.reporting.email_notifier import EmailNotifier
from src.monitoring.apply_column_monitor import ApplyColumnMonitor
from src.utils.id_extractor import extract_file_id_from_url, extract_sheet_id_from_url

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/resume_generation_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ResumeGenerationAgent:
    def __init__(self):
        self.config = self._load_config()
        self.profile_manager = None
        self.resume_builder = None
        self.format_converter = None
        self.sheets_manager = None
        self.email_notifier = None
        self.monitor = None
        
        self._initialize_components()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            # AI API keys
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'claude_api_key': os.getenv('CLAUDE_API_KEY'),
            
            # Google API settings
            'google_drive_credentials': os.getenv('GOOGLE_DRIVE_CREDENTIALS'),
            'google_sheets_id': extract_sheet_id_from_url(os.getenv('GOOGLE_SHEETS_ID')),
            
            # Profile files
            'linkedin_pdf_id': extract_file_id_from_url(os.getenv('LINKEDIN_PDF_ID')),
            'summary_txt_id': extract_file_id_from_url(os.getenv('SUMMARY_TXT_ID')),
            
            # Email settings
            'sender_email': os.getenv('SENDER_EMAIL'),
            'sender_password': os.getenv('SENDER_PASSWORD'),
            'recipient_email': os.getenv('RECIPIENT_EMAIL'),
            
            # Resume generation settings
            'resume_templates_folder': os.getenv('RESUME_TEMPLATES_FOLDER', 'templates/'),
            'generated_resumes_folder': os.getenv('GENERATED_RESUMES_FOLDER'),
            'default_resume_template': os.getenv('DEFAULT_RESUME_TEMPLATE', 'professional_template.docx'),
            
            # Monitoring settings
            'monitor_interval': int(os.getenv('MONITOR_INTERVAL', '300'))  # 5 minutes
        }
    
    def _initialize_components(self):
        """Initialize all required components."""
        try:
            # Google Drive client for profile management
            drive_client = GoogleDriveClient(
                credentials_path=self.config['google_drive_credentials']
            )
            
            # Profile manager
            self.profile_manager = ProfileManager(
                drive_client=drive_client,
                linkedin_pdf_id=self.config['linkedin_pdf_id'],
                summary_txt_id=self.config['summary_txt_id']
            )
            
            # Resume builder
            self.resume_builder = ResumeBuilder(
                openai_api_key=self.config['openai_api_key'],
                claude_api_key=self.config['claude_api_key']
            )
            
            # Format converter
            self.format_converter = FormatConverter()
            
            # Google Sheets manager
            self.sheets_manager = SheetsManager(
                spreadsheet_id=self.config['google_sheets_id'],
                credentials_path=self.config['google_drive_credentials']
            )
            
            # Email notifier
            self.email_notifier = EmailNotifier(
                sender_email=self.config['sender_email'],
                sender_password=self.config['sender_password'],
                recipient_email=self.config['recipient_email']
            )
            
            # Apply column monitor
            self.monitor = ApplyColumnMonitor(
                sheets_manager=self.sheets_manager,
                check_interval=self.config['monitor_interval']
            )
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def start_monitoring(self, max_iterations: int = None):
        """
        Start monitoring Google Sheets for jobs marked for application.
        
        Args:
            max_iterations: Maximum number of monitoring cycles (None for infinite)
        """
        logger.info("Starting resume generation monitoring")
        
        try:
            # Load profile once at startup
            logger.info("Loading user profile...")
            profile_summary = self.profile_manager.get_profile_summary()
            
            # Start monitoring with callback function
            self.monitor.start_monitoring(
                callback_function=lambda job_data: self._process_job_application(job_data, profile_summary),
                max_iterations=max_iterations
            )
            
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
            self._send_error_notification(str(e))
            raise
    
    def check_once(self):
        """Perform a single check for jobs marked for application."""
        logger.info("Performing single check for resume generation")
        
        try:
            # Load profile
            profile_summary = self.profile_manager.get_profile_summary()
            
            # Check for new jobs
            new_jobs = self.monitor.check_once()
            
            # Process each job
            for job_data in new_jobs:
                self._process_job_application(job_data, profile_summary)
            
            if not new_jobs:
                logger.info("No new jobs found for resume generation")
            
            return len(new_jobs)
            
        except Exception as e:
            logger.error(f"Error in single check: {e}")
            self._send_error_notification(str(e))
            return 0
    
    def _process_job_application(self, job_data: Dict[str, Any], profile_summary: str):
        """
        Process a single job application by generating a custom resume.
        
        Args:
            job_data: Job information from Google Sheets
            profile_summary: User profile summary
        """
        job_title = job_data.get('title', 'Unknown Position')
        company = job_data.get('company', 'Unknown Company')
        row_number = job_data.get('row_number', 0)
        
        logger.info(f"Processing job application: {job_title} at {company}")
        
        try:
            # Update status to "In Progress"
            self.sheets_manager.update_resume_status(
                row_number=row_number,
                status="In Progress",
                generated_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Generate custom resume
            logger.info("Generating custom resume...")
            resume_data = self.resume_builder.generate_custom_resume(
                profile_summary=profile_summary,
                job_data=job_data
            )
            
            # Convert to multiple formats
            logger.info("Converting resume to multiple formats...")
            file_paths = self.format_converter.convert_to_all_formats(resume_data)
            
            # Upload to Google Drive (if configured) and get shareable link
            resume_link = self._upload_resume_to_drive(file_paths, job_title, company)
            
            # Update Google Sheets with completion status
            self.sheets_manager.update_resume_status(
                row_number=row_number,
                status="Completed",
                generated_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                resume_link=resume_link or file_paths.get('pdf', '')
            )
            
            # Send notification email
            self.email_notifier.send_resume_notification(
                job_title=job_title,
                company=company,
                resume_link=resume_link or file_paths.get('pdf', '')
            )
            
            logger.info(f"Resume generation completed for {job_title} at {company}")
            
        except Exception as e:
            logger.error(f"Error processing job application: {e}")
            
            # Update status to "Error"
            try:
                self.sheets_manager.update_resume_status(
                    row_number=row_number,
                    status=f"Error: {str(e)[:100]}",
                    generated_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            except Exception as sheet_error:
                logger.error(f"Error updating sheet status: {sheet_error}")
            
            # Send error notification
            self._send_error_notification(f"Error generating resume for {job_title} at {company}: {str(e)}")
    
    def _upload_resume_to_drive(self, file_paths: Dict[str, str], job_title: str, company: str) -> Optional[str]:
        """
        Upload generated resume to Google Drive and return shareable link.
        
        Args:
            file_paths: Dictionary of generated file paths
            job_title: Job title for organization
            company: Company name for organization
            
        Returns:
            Shareable Google Drive link or None if upload fails
        """
        try:
            # For now, return the local file path
            # In a full implementation, you would upload to Google Drive using the Drive API
            # and return a shareable link
            
            pdf_path = file_paths.get('pdf', '')
            if pdf_path and os.path.exists(pdf_path):
                logger.info(f"Resume files generated locally: {pdf_path}")
                return pdf_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error uploading resume to Drive: {e}")
            return None
    
    def _send_error_notification(self, error_message: str):
        """Send error notification email."""
        try:
            self.email_notifier.send_error_notification(
                error_message=error_message,
                component="Resume Generation Agent"
            )
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the resume generation agent."""
        try:
            monitor_stats = self.monitor.get_monitoring_stats()
            
            return {
                'agent_name': 'Resume Generation Agent',
                'status': 'Running',
                'last_check': monitor_stats.get('last_check'),
                'processed_jobs_count': monitor_stats.get('processed_jobs_count'),
                'check_interval_seconds': monitor_stats.get('check_interval'),
                'config': {
                    'monitor_interval': self.config['monitor_interval'],
                    'sheets_id': self.config['google_sheets_id']
                }
            }
        except Exception as e:
            return {
                'agent_name': 'Resume Generation Agent',
                'status': 'Error',
                'error': str(e)
            }
    
    def stop_monitoring(self):
        """Stop the monitoring process gracefully."""
        logger.info("Stopping resume generation monitoring")
        # In a production environment, you would implement proper shutdown logic

def main():
    """Main entry point for the Resume Generation Agent."""
    try:
        agent = ResumeGenerationAgent()
        
        # Check command line arguments for mode
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == '--once':
            # Single check mode
            processed_count = agent.check_once()
            logger.info(f"Single check completed. Processed {processed_count} jobs.")
        else:
            # Continuous monitoring mode
            agent.start_monitoring()
            
    except KeyboardInterrupt:
        logger.info("Resume Generation Agent stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in Resume Generation Agent: {e}")
        raise

if __name__ == "__main__":
    main()