"""
Agent 1: Job Matching Agent
Scrapes job sites, evaluates job fit, and populates Google Sheets with high-scoring jobs.
"""
import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv


from src.profile.google_drive_client import GoogleDriveClient
from src.profile.profile_manager import ProfileManager
from src.scrapers.linkedin_scraper import LinkedInScraper
from src.scrapers.indeed_scraper import IndeedScraper
from src.scrapers.jobleads_scraper import JobLeadsScraper
from src.ai.job_evaluator import JobEvaluator
from src.reporting.sheets_manager import SheetsManager
from src.reporting.email_notifier import EmailNotifier
from src.utils.id_extractor import extract_file_id_from_url, extract_sheet_id_from_url

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/job_matching_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class JobMatchingAgent:
    def __init__(self):
        self.config = self._load_config()
        self.profile_manager = None
        self.job_evaluator = None
        self.sheets_manager = None
        self.email_notifier = None
        self.scrapers = {}
        
        self._initialize_components()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        min_match_score = int(os.getenv('MIN_MATCH_SCORE', '50'))
        logger.info(f"Loaded min_match_score: {min_match_score}")
        return {
            # AI API keys
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'claude_api_key': os.getenv('CLAUDE_API_KEY'),
            
            # Google API settings
            'google_drive_credentials': os.getenv('GOOGLE_DRIVE_CREDENTIALS'),
            'google_sheets_id': extract_sheet_id_from_url(os.getenv('GOOGLE_SHEETS_ID')),
            'gmail_credentials': os.getenv('GMAIL_CREDENTIALS'),
            
            # Profile files
            'linkedin_pdf_id': extract_file_id_from_url(os.getenv('LINKEDIN_PDF_ID')),
            'summary_txt_id': extract_file_id_from_url(os.getenv('SUMMARY_TXT_ID')),
            
            # Job search settings
            'linkedin_email': os.getenv('LINKEDIN_EMAIL'),
            'linkedin_password': os.getenv('LINKEDIN_PASSWORD'),
            'search_locations': os.getenv('SEARCH_LOCATIONS', 'Toronto,ON;Remote;Ontario,Canada').split(';'),
            'min_match_score': min_match_score,
            
            # Email settings
            'sender_email': os.getenv('SENDER_EMAIL'),
            'sender_password': os.getenv('SENDER_PASSWORD'),
            'recipient_email': os.getenv('RECIPIENT_EMAIL'),
            
            # Scraping settings
            'user_agent': os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'scraping_delay': int(os.getenv('SCRAPING_DELAY', '2')),
            'max_retries': int(os.getenv('MAX_RETRIES', '3'))
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
            
            # AI job evaluator with rate limiting
            rate_limit_delay = float(os.getenv('AI_RATE_LIMIT_DELAY', '3.0'))  # 3-second default delay
            self.job_evaluator = JobEvaluator(
                openai_api_key=self.config['openai_api_key'],
                claude_api_key=self.config['claude_api_key'],
                rate_limit_delay=rate_limit_delay
            )
            
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
            
            # Initialize scrapers
            self.scrapers = {
                'linkedin': LinkedInScraper(
                    email=self.config['linkedin_email'],
                    password=self.config['linkedin_password'],
                    headless=True
                ),
                'indeed': IndeedScraper(
                    user_agent=self.config['user_agent']
                ),
                'jobleads': JobLeadsScraper(
                    user_agent=self.config['user_agent']
                )
            }
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def run_daily_job_search(self):
        """Main method to run the daily job search and evaluation."""
        logger.info("Starting daily job search process")
        
        try:
            # Step 1: Load user profile
            logger.info("Loading user profile...")
            profile = self.profile_manager.load_profile()
            profile_summary = self.profile_manager.get_profile_summary()
            
            # Step 2: Define search terms
            search_terms = [
                "Business Analyst",
                "Project Manager", 
                "Process Analyst",
                "Data Analyst",
                "Scrum Master",
                "Product Manager"
            ]
            
            # Step 3: Scrape jobs from all sources
            logger.info("Scraping jobs from all sources...")
            all_jobs = []
            
            for scraper_name, scraper in self.scrapers.items():
                try:
                    logger.info(f"Scraping jobs from {scraper_name}...")
                    
                    if scraper_name == 'linkedin':
                        # Setup and login for LinkedIn
                        scraper.setup_driver()
                        if scraper.login():
                            jobs = scraper.search_jobs(
                                search_terms=search_terms,
                                locations=self.config['search_locations'],
                                days_back=7
                            )
                            all_jobs.extend(jobs)
                        scraper.close()
                    
                    elif scraper_name == 'indeed':
                        jobs = scraper.search_jobs(
                            search_terms=search_terms,
                            locations=self.config['search_locations'],
                            days_back=7
                        )
                        all_jobs.extend(jobs)
                        scraper.close()
                    
                    elif scraper_name == 'jobleads':
                        # JobLeads scraper is placeholder - would need actual implementation
                        logger.info("JobLeads scraper is placeholder - skipping")
                        continue
                    
                except Exception as e:
                    logger.error(f"Error scraping from {scraper_name}: {e}")
                    continue
            
            logger.info(f"Total jobs scraped: {len(all_jobs)}")
            
            # Step 4: Filter out duplicate and existing jobs
            logger.info("Filtering jobs...")
            new_jobs = self._filter_new_jobs(all_jobs)
            logger.info(f"New jobs to evaluate: {len(new_jobs)}")
            
            # Step 5: Evaluate jobs using AI
            logger.info("Evaluating job fit with AI...")
            evaluated_jobs = []
            
            for job in new_jobs:
                try:
                    score, reasoning = self.job_evaluator.evaluate_job_fit(job, profile_summary)
                    
                    if score >= self.config['min_match_score']:
                        job_with_score = job.copy()
                        job_with_score.update({
                            'score': score,
                            'match_reasoning': reasoning
                        })
                        evaluated_jobs.append(job_with_score)
                        
                        logger.info(f"High-scoring job found: {job['title']} at {job['company']} (Score: {score})")
                
                except Exception as e:
                    logger.error(f"Error evaluating job: {e}")
                    continue
            
            logger.info(f"High-scoring jobs found: {len(evaluated_jobs)}")
            
            # Step 6: Add jobs to Google Sheets
            if evaluated_jobs:
                logger.info("Adding jobs to Google Sheets...")
                self.sheets_manager.add_job_data(evaluated_jobs)
            
            # Step 7: Send email notification
            logger.info("Sending email notification...")
            self._send_daily_summary(evaluated_jobs, len(all_jobs))
            
            logger.info("Daily job search completed successfully")
            
        except Exception as e:
            logger.error(f"Error in daily job search: {e}")
            self._send_error_notification(str(e))
    
    def _filter_new_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out jobs that already exist in the spreadsheet."""
        new_jobs = []
        
        for job in jobs:
            try:
                job_title = job.get('title', '')
                company = job.get('company', '')
                
                if not self.sheets_manager.check_job_exists(job_title, company):
                    new_jobs.append(job)
                else:
                    logger.debug(f"Job already exists: {job_title} at {company}")
                    
            except Exception as e:
                logger.warning(f"Error checking job existence: {e}")
                # Include the job if we can't check (better safe than sorry)
                new_jobs.append(job)
        
        return new_jobs
    
    def _send_daily_summary(self, high_scoring_jobs: List[Dict[str, Any]], total_jobs_scraped: int):
        """Send daily summary email."""
        try:
            subject = f"Daily Job Search Summary - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create email body
            body_parts = [
                f"Daily Job Search Summary for {datetime.now().strftime('%B %d, %Y')}",
                "=" * 50,
                "",
                f"📊 Summary Statistics:",
                f"• Total jobs scraped: {total_jobs_scraped}",
                f"• High-scoring jobs (85+): {len(high_scoring_jobs)}",
                f"• Jobs added to spreadsheet: {len(high_scoring_jobs)}",
                ""
            ]
            
            if high_scoring_jobs:
                body_parts.extend([
                    "🎯 High-Scoring Job Opportunities:",
                    ""
                ])
                
                for job in high_scoring_jobs[:10]:  # Top 10 jobs
                    body_parts.extend([
                        f"• {job.get('title', 'N/A')} at {job.get('company', 'N/A')}",
                        f"  Score: {job.get('score', 'N/A')}/100",
                        f"  Location: {job.get('location', 'N/A')}",
                        f"  Reasoning: {job.get('match_reasoning', 'N/A')[:100]}...",
                        ""
                    ])
            else:
                body_parts.extend([
                    "No high-scoring jobs found today.",
                    "Consider adjusting search terms or minimum score threshold.",
                    ""
                ])
            
            body_parts.extend([
                "",
                "💡 Next Steps:",
                "1. Review the jobs in your Google Sheets",
                "2. Check the 'Apply' checkbox for jobs you want custom resumes for",
                "3. The Resume Generator will automatically create tailored resumes",
                "",
                f"View your job spreadsheet: https://docs.google.com/spreadsheets/d/{self.config['google_sheets_id']}"
            ])
            
            body = "\n".join(body_parts)
            
            self.email_notifier.send_email(subject, body)
            logger.info("Daily summary email sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
    
    def _send_error_notification(self, error_message: str):
        """Send error notification email."""
        try:
            subject = f"Job Matching Agent Error - {datetime.now().strftime('%Y-%m-%d')}"
            body = f"""
Job Matching Agent encountered an error:

Error: {error_message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the logs for more details.
"""
            
            self.email_notifier.send_email(subject, body)
            logger.info("Error notification email sent")
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")

def main():
    """Main entry point for the Job Matching Agent."""
    try:
        agent = JobMatchingAgent()
        agent.run_daily_job_search()
    except Exception as e:
        logger.error(f"Fatal error in Job Matching Agent: {e}")
        raise

if __name__ == "__main__":
    main()