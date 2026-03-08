import logging
import os
from typing import List, Dict
from datetime import datetime
from src.gmail import GmailClient, EmailParser, JobExtractor
from src.storage import FileManager, SheetsManager
from src.ai import JobEvaluator
from src.config import Config

class GmailJobAgent:
    """Agent 1: Gmail job extraction and processing"""
    
    def __init__(self):
        self.config = Config()
        self.gmail_client = GmailClient()
        self.email_parser = EmailParser()
        self.job_extractor = JobExtractor()
        self.file_manager = FileManager()
        self.sheets_manager = SheetsManager()
        self.job_evaluator = JobEvaluator()
        self.logger = logging.getLogger(__name__)
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Setup logging
        if not self.logger.handlers:
            logging.basicConfig(
                level=getattr(logging, self.config.LOG_LEVEL.upper()),
                format=self.config.LOG_FORMAT,
                handlers=[
                    logging.FileHandler('logs/gmail_agent.log'),
                    logging.StreamHandler()
                ]
            )
    
    def run(self) -> Dict:
        """Main execution method for Gmail job agent with full pipeline"""
        self.logger.info("Starting Gmail Job Agent execution with full pipeline")
        
        results = {
            'execution_time': datetime.now(),
            'emails_processed': 0,
            'job_alerts_found': 0,
            'jobs_extracted': 0,
            'jobs_evaluated': 0,
            'high_scoring_jobs': 0,
            'jobs_added_to_sheet': 0,
            'jobs': [],
            'evaluated_jobs': [],
            'storage_results': {},
            'sheets_results': {},
            'errors': [],
            'success': False
        }
        
        try:
            # Step 1: Authenticate with Gmail
            if not self.gmail_client.authenticate():
                raise Exception("Failed to authenticate with Gmail API")
            
            # Step 2: Retrieve recent emails
            self.logger.info(f"Retrieving emails from last {self.config.GMAIL_SEARCH_DAYS} days")
            emails = self.gmail_client.get_recent_emails()
            results['emails_processed'] = len(emails)
            
            if not emails:
                self.logger.warning("No emails found matching criteria")
                results['success'] = True
                return results
            
            # Step 3: Filter job alert emails
            job_alert_emails = []
            for email in emails:
                if self.gmail_client.is_job_alert(email):
                    job_alert_emails.append(email)
            
            results['job_alerts_found'] = len(job_alert_emails)
            self.logger.info(f"Found {len(job_alert_emails)} job alert emails")
            
            # Step 4: Store raw email alerts in Google Drive
            if job_alert_emails:
                storage_results = self.file_manager.store_raw_email_alerts(job_alert_emails)
                results['storage_results'] = storage_results
                if not storage_results['success']:
                    self.logger.warning("Failed to store raw email alerts")
                    results['errors'].extend(storage_results['errors'])
            
            # Step 5: Parse and extract job data
            all_jobs = []
            for email in job_alert_emails:
                try:
                    # Parse email
                    parsed_email = self.email_parser.parse_job_email(email)
                    
                    if not parsed_email:
                        continue
                    
                    # Extract job data
                    jobs = self.job_extractor.extract_job_data(parsed_email)
                    
                    # Validate and clean job data
                    valid_jobs = []
                    for job in jobs:
                        if self.job_extractor.validate_job_data(job):
                            # Add additional metadata
                            job.update({
                                'extracted_at': datetime.now(),
                                'agent_version': '1.0.0'
                            })
                            valid_jobs.append(job)
                    
                    all_jobs.extend(valid_jobs)
                    self.logger.info(f"Extracted {len(valid_jobs)} valid jobs from email {email.get('id', 'unknown')}")
                    
                except Exception as e:
                    error_msg = f"Error processing email {email.get('id', 'unknown')}: {str(e)}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            results['jobs_extracted'] = len(all_jobs)
            results['jobs'] = all_jobs
            
            # Step 6: Store extracted job data
            if all_jobs:
                job_storage_results = self.file_manager.store_extracted_jobs(all_jobs)
                if not job_storage_results['success']:
                    self.logger.warning("Failed to store extracted job data")
                    results['errors'].extend(job_storage_results['errors'])
            
            # Step 7: AI Job Evaluation
            if all_jobs:
                try:
                    self.logger.info("Starting AI job evaluation")
                    
                    # Get profile data
                    profile_data = self.file_manager.get_profile_files()
                    if not profile_data['success']:
                        self.logger.warning("Failed to load profile data for evaluation")
                        results['errors'].extend(profile_data['errors'])
                        # Use empty profile data as fallback
                        profile_data = {'linkedin_pdf': '', 'summary_txt': ''}
                    
                    # Evaluate jobs
                    evaluated_jobs = self.job_evaluator.evaluate_job_batch(all_jobs, profile_data)
                    results['jobs_evaluated'] = len(evaluated_jobs)
                    results['evaluated_jobs'] = evaluated_jobs
                    
                    # Filter high-scoring jobs
                    high_scoring_jobs = self.job_evaluator.filter_high_scoring_jobs(evaluated_jobs)
                    results['high_scoring_jobs'] = len(high_scoring_jobs)
                    
                    self.logger.info(f"Evaluated {len(evaluated_jobs)} jobs, {len(high_scoring_jobs)} scored 85+")
                    
                except Exception as e:
                    error_msg = f"Error in AI job evaluation: {str(e)}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
                    # Use original jobs without evaluation
                    evaluated_jobs = all_jobs
                    results['evaluated_jobs'] = evaluated_jobs
            
            # Step 8: Update Google Sheets
            if results.get('evaluated_jobs'):
                try:
                    self.logger.info("Updating Google Sheets with job data")
                    sheets_results = self.sheets_manager.add_jobs_to_sheet(results['evaluated_jobs'])
                    results['sheets_results'] = sheets_results
                    results['jobs_added_to_sheet'] = sheets_results.get('added_count', 0)
                    
                    if not sheets_results['success']:
                        results['errors'].extend(sheets_results['errors'])
                    
                    self.logger.info(f"Added {sheets_results.get('added_count', 0)} jobs to Google Sheets")
                    
                except Exception as e:
                    error_msg = f"Error updating Google Sheets: {str(e)}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Step 9: Generate and store job evaluation report
            if results.get('evaluated_jobs'):
                try:
                    self.logger.info("Generating job evaluation report")
                    
                    # Prepare report data
                    report_data = {
                        'summary': {
                            'total_jobs': results['jobs_evaluated'],
                            'high_scoring_count': results['high_scoring_jobs'],
                            'average_score': sum(job.get('score', 0) for job in results['evaluated_jobs']) / len(results['evaluated_jobs']) if results['evaluated_jobs'] else 0,
                            'evaluation_date': datetime.now().isoformat()
                        },
                        'jobs': results['evaluated_jobs'],
                        'execution_summary': {
                            'emails_processed': results['emails_processed'],
                            'job_alerts_found': results['job_alerts_found'],
                            'jobs_extracted': results['jobs_extracted'],
                            'execution_time': results['execution_time'].isoformat()
                        }
                    }
                    
                    # Store report in Reports folder
                    report_results = self.file_manager.store_job_evaluation_report(report_data)
                    if report_results['success']:
                        self.logger.info(f"Generated job evaluation report: {report_results['file_id']}")
                    else:
                        self.logger.warning("Failed to generate job evaluation report")
                        results['errors'].extend(report_results['errors'])
                    
                except Exception as e:
                    error_msg = f"Error generating job evaluation report: {str(e)}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Final success check
            results['success'] = len(results['errors']) == 0 or results['jobs_extracted'] > 0
            
            # Summary logging
            self.logger.info(f"Gmail Job Agent pipeline completed:")
            self.logger.info(f"  - Processed {results['emails_processed']} emails")
            self.logger.info(f"  - Found {results['job_alerts_found']} job alerts")
            self.logger.info(f"  - Extracted {results['jobs_extracted']} jobs")
            self.logger.info(f"  - Evaluated {results['jobs_evaluated']} jobs")
            self.logger.info(f"  - Found {results['high_scoring_jobs']} high-scoring jobs")
            self.logger.info(f"  - Added {results['jobs_added_to_sheet']} jobs to Google Sheets")
            
        except Exception as e:
            error_msg = f"Gmail Job Agent execution failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            results['success'] = False
        
        return results
    
    def get_job_alert_summary(self, days: int = None) -> Dict:
        """Get summary of job alerts without full processing"""
        days = days or self.config.GMAIL_SEARCH_DAYS
        
        summary = {
            'total_emails': 0,
            'job_alert_emails': 0,
            'sources': {},
            'date_range': f"Last {days} days"
        }
        
        try:
            if not self.gmail_client.authenticate():
                return summary
            
            emails = self.gmail_client.get_recent_emails(days)
            summary['total_emails'] = len(emails)
            
            job_alerts = []
            for email in emails:
                if self.gmail_client.is_job_alert(email):
                    job_alerts.append(email)
                    
                    # Track sources
                    parsed = self.email_parser.parse_job_email(email)
                    source = parsed.get('source_type', 'Unknown')
                    summary['sources'][source] = summary['sources'].get(source, 0) + 1
            
            summary['job_alert_emails'] = len(job_alerts)
            
        except Exception as e:
            self.logger.error(f"Error generating job alert summary: {str(e)}")
        
        return summary
    
    def test_connection(self) -> bool:
        """Test Gmail API connection"""
        try:
            return self.gmail_client.authenticate()
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {str(e)}")
            return False