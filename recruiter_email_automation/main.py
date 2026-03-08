#!/usr/bin/env python3
"""
Recruiter Email Automation System
Automated workflow for processing recruiter emails and generating responses
"""

import os
import sys
import schedule
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.email_processor import EmailProcessor
from src.email_classifier import EmailClassifier
from src.resume_generator import ResumeGenerator
from src.response_generator import ResponseGenerator
from src.email_sender import EmailSender
from src.database import EmailDatabase
from src.logger import setup_logger

# Get project root directory and load environment variables
project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

class RecruiterEmailAutomation:
    """Main automation system for processing recruiter emails"""
    
    def __init__(self):
        """Initialize the automation system"""
        self.logger = setup_logger()
        self.logger.info("Initializing Recruiter Email Automation System")
        
        # Initialize components
        self.email_processor = EmailProcessor()
        self.email_classifier = EmailClassifier()
        self.resume_generator = ResumeGenerator()
        self.response_generator = ResponseGenerator()
        self.email_sender = EmailSender()
        self.database = EmailDatabase()
        
        # Configuration
        self.summary_time = os.getenv('SUMMARY_TIME', '19:00')  # 7pm default
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        if not self.recipient_email:
            raise ValueError("RECIPIENT_EMAIL must be set in .env file")
        
        self.logger.info("System initialized successfully")
    
    def process_daily_emails(self):
        """Main workflow: Process emails from the past 24 hours"""
        self.logger.info("="*80)
        self.logger.info(f"Starting daily email processing at {datetime.now()}")
        self.logger.info("="*80)
        
        try:
            # Step 1: Fetch emails from last 24 hours
            self.logger.info("Step 1: Fetching emails from last 24 hours...")
            emails = self.email_processor.get_emails_last_24h()
            
            if not emails:
                self.logger.info("No new emails found in the last 24 hours")
                return
            
            self.logger.info(f"Found {len(emails)} emails to process")
            
            # Step 2: Filter out already processed emails
            self.logger.info("Step 2: Filtering out already processed emails...")
            new_emails = []
            for email in emails:
                if not self.database.is_email_processed(email['id']):
                    new_emails.append(email)
                else:
                    self.logger.debug(f"Email {email['id']} already processed, skipping")
            
            if not new_emails:
                self.logger.info("All emails have already been processed")
                return
            
            self.logger.info(f"Processing {len(new_emails)} new emails")
            
            # Step 3: Classify emails
            self.logger.info("Step 3: Classifying emails...")
            recruiter_emails = []
            task_emails = []
            other_emails = []
            
            for email in new_emails:
                category = self.email_classifier.classify_email(email)
                email['category'] = category
                
                if category == 'recruiter':
                    recruiter_emails.append(email)
                elif category == 'task':
                    task_emails.append(email)
                else:
                    other_emails.append(email)
            
            self.logger.info(f"Classification complete: {len(recruiter_emails)} recruiter, "
                           f"{len(task_emails)} task, {len(other_emails)} other")
            
            # Step 4: Process recruiter emails
            recruiter_responses = []
            if recruiter_emails:
                self.logger.info("Step 4: Processing recruiter emails...")
                for email in recruiter_emails:
                    try:
                        # Generate customized resume
                        resume_path = self.resume_generator.generate_resume(email)
                        
                        # Generate professional response
                        response = self.response_generator.generate_response(email, resume_path)
                        
                        recruiter_responses.append({
                            'email': email,
                            'response': response,
                            'resume_path': resume_path
                        })
                        
                        # Mark as processed
                        self.database.mark_email_processed(email['id'], 'recruiter', response)
                        
                        self.logger.info(f"Generated response for recruiter email from {email['sender_email']}")
                    except Exception as e:
                        self.logger.error(f"Error processing recruiter email {email['id']}: {e}")
                        # Still mark as processed to avoid retrying
                        self.database.mark_email_processed(email['id'], 'recruiter', f"Error: {str(e)}")
            
            # Step 5: Process task emails
            task_summaries = []
            if task_emails:
                self.logger.info("Step 5: Processing task emails...")
                for email in task_emails:
                    try:
                        summary = self.email_classifier.summarize_task_email(email)
                        task_summaries.append({
                            'email': email,
                            'summary': summary
                        })
                        
                        # Mark as processed
                        self.database.mark_email_processed(email['id'], 'task', summary)
                        
                        self.logger.info(f"Summarized task email from {email['sender_email']}")
                    except Exception as e:
                        self.logger.error(f"Error processing task email {email['id']}: {e}")
                        self.database.mark_email_processed(email['id'], 'task', f"Error: {str(e)}")
            
            # Step 6: Process other emails
            other_summaries = []
            if other_emails:
                self.logger.info("Step 6: Processing other emails...")
                for email in other_emails:
                    other_summaries.append({
                        'sender_name': email['sender_name'],
                        'subject': email['subject']
                    })
                    
                    # Mark as processed
                    self.database.mark_email_processed(email['id'], 'other', '')
            
            # Step 7: Send summaries email (by 7pm)
            if task_summaries or other_summaries:
                self.logger.info("Step 7: Sending daily summary email...")
                self.email_sender.send_daily_summary(
                    task_summaries=task_summaries,
                    other_summaries=other_summaries,
                    recipient=self.recipient_email
                )
            
            # Step 8: Send recruiter response emails (separate emails)
            if recruiter_responses:
                self.logger.info("Step 8: Sending recruiter response emails...")
                for response_data in recruiter_responses:
                    self.email_sender.send_recruiter_response(
                        email=response_data['email'],
                        response=response_data['response'],
                        resume_path=response_data['resume_path'],
                        recipient=self.recipient_email
                    )
            
            self.logger.info("="*80)
            self.logger.info("Daily email processing completed successfully")
            self.logger.info(f"Processed: {len(recruiter_emails)} recruiter, "
                           f"{len(task_emails)} task, {len(other_emails)} other")
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"Error in daily email processing: {e}", exc_info=True)
    
    def schedule_daily_runs(self):
        """Schedule the automation to run daily at the specified time"""
        schedule.every().day.at(self.summary_time).do(self.process_daily_emails)
        
        self.logger.info(f"⏰ Automation scheduled to run daily at {self.summary_time}")
        self.logger.info("🔄 Starting scheduler... (Press Ctrl+C to stop)")
        
        # Also run immediately if it's before the scheduled time
        current_time = datetime.now().time()
        scheduled_time = datetime.strptime(self.summary_time, '%H:%M').time()
        
        if current_time >= scheduled_time:
            self.logger.info("Running initial processing now...")
            self.process_daily_emails()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("\n👋 Automation scheduler stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Recruiter Email Automation System')
    parser.add_argument('--test', action='store_true', 
                       help='Run immediately for testing (don\'t start scheduler)')
    parser.add_argument('--once', action='store_true',
                       help='Process emails once and exit')
    args = parser.parse_args()
    
    print("🤖 Recruiter Email Automation System Starting...")
    
    try:
        automation = RecruiterEmailAutomation()
        
        if args.test or args.once:
            # Run immediately for testing
            print("🧪 Running in test mode (processing emails now)...")
            automation.process_daily_emails()
            if args.once:
                print("✅ Processing complete. Exiting.")
                return
        else:
            # Start the scheduler
            automation.schedule_daily_runs()
        
    except KeyboardInterrupt:
        print("\n👋 Automation stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start automation: {e}")
        print("\nPlease ensure:")
        print("1. Gmail credentials.json file exists")
        print("2. All required environment variables are set in .env file")
        print("3. All required packages are installed")
        print("\nRun 'python test_setup.py' to verify your setup")
        sys.exit(1)

if __name__ == "__main__":
    main()

