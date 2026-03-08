#!/usr/bin/env python3
"""
Job Evaluation System - Main Entry Point
Implements intelligent job evaluation and resume generation from Gmail alerts
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.agents import GmailJobAgent, ResumeGenerationAgent

def setup_logging():
    """Setup logging configuration"""
    config = Config()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler('logs/system.log'),
            logging.StreamHandler()
        ]
    )

def run_gmail_agent():
    """Execute Gmail job extraction agent"""
    logger = logging.getLogger(__name__)
    logger.info("Starting Job Evaluation System - Gmail Agent")
    
    try:
        # Validate configuration
        Config.validate()
        
        # Initialize and run Gmail agent
        gmail_agent = GmailJobAgent()
        results = gmail_agent.run()
        
        if results['success']:
            logger.info("Gmail agent completed successfully")
            print(f"\nGmail Job Agent Results:")
            print(f"   Emails processed: {results['emails_processed']}")
            print(f"   Job alerts found: {results['job_alerts_found']}")
            print(f"   Jobs extracted: {results['jobs_extracted']}")
            print(f"   Jobs evaluated: {results['jobs_evaluated']}")
            print(f"   High-scoring jobs (85+): {results['high_scoring_jobs']}")
            print(f"   Jobs added to Google Sheets: {results['jobs_added_to_sheet']}")
            
            if results.get('evaluated_jobs'):
                print(f"\nTop Evaluated Jobs:")
                top_jobs = sorted(results['evaluated_jobs'], key=lambda x: x.get('match_score', 0), reverse=True)[:5]
                for i, job in enumerate(top_jobs, 1):
                    score = job.get('match_score', 0)
                    print(f"   {i}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')} (Score: {score})")
                    print(f"      Source: {job.get('source_type', 'N/A')}")
                
                if len(results['evaluated_jobs']) > 5:
                    print(f"   ... and {len(results['evaluated_jobs']) - 5} more jobs")
        else:
            logger.error("Gmail agent execution failed")
            print(f"\nGmail Agent Failed:")
            for error in results['errors']:
                print(f"   - {error}")
                
    except Exception as e:
        logger.error(f"System error: {str(e)}")
        print(f"System Error: {str(e)}")

def run_resume_agent():
    """Execute Resume generation agent"""
    logger = logging.getLogger(__name__)
    logger.info("Starting Job Evaluation System - Resume Agent")
    
    try:
        # Validate configuration
        Config.validate()
        
        # Initialize and run Resume agent
        resume_agent = ResumeGenerationAgent()
        results = resume_agent.run()
        
        if results['success']:
            logger.info("Resume agent completed successfully")
            print(f"\n📄 Resume Generation Agent Results:")
            print(f"   Jobs checked: {results['jobs_checked']}")
            print(f"   Jobs marked for application: {results['jobs_marked_for_application']}")
            print(f"   Resumes generated: {results['resumes_generated']}")
            print(f"   Feedback documents generated: {results['feedback_generated']}")
            print(f"   Files uploaded to Google Drive: {results['files_uploaded']}")
            
            if results.get('processed_jobs'):
                print(f"\nProcessed Jobs:")
                for job in results['processed_jobs']:
                    status = "Success" if job['resume_generated'] else "Failed"
                    print(f"   {status} {job['job_title']} at {job['company']}")
                    if job['errors']:
                        for error in job['errors']:
                            print(f"      Error: {error}")
        else:
            logger.error("Resume agent execution failed")
            print(f"\nResume Agent Failed:")
            for error in results['errors']:
                print(f"   - {error}")
                
    except Exception as e:
        logger.error(f"System error: {str(e)}")
        print(f"System Error: {str(e)}")

def run_full_pipeline():
    """Execute both agents in sequence"""
    print("Running Full Job Evaluation Pipeline")
    print("=" * 50)
    
    # Step 1: Run Gmail agent
    print("\nStep 1: Gmail Job Extraction")
    run_gmail_agent()
    
    # Step 2: Run Resume agent
    print("\nStep 2: Resume Generation")
    run_resume_agent()
    
    print("\nFull pipeline completed!")

def test_gmail_connection():
    """Test Gmail API connection"""
    print("Testing Gmail API connection...")
    
    try:
        gmail_agent = GmailJobAgent()
        success = gmail_agent.test_connection()
        
        if success:
            print("Gmail API connection successful")
        else:
            print("Gmail API connection failed")
            
    except Exception as e:
        print(f"Connection test error: {str(e)}")

def get_job_alert_summary():
    """Get summary of job alerts"""
    print("Getting job alert summary...")
    
    try:
        gmail_agent = GmailJobAgent()
        summary = gmail_agent.get_job_alert_summary()
        
        print(f"\n📈 Job Alert Summary ({summary['date_range']}):")
        print(f"   Total emails: {summary['total_emails']}")
        print(f"   Job alert emails: {summary['job_alert_emails']}")
        
        if summary['sources']:
            print(f"   Sources:")
            for source, count in summary['sources'].items():
                print(f"     - {source}: {count}")
                
    except Exception as e:
        print(f"Summary error: {str(e)}")

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Job Evaluation System')
    parser.add_argument('--run-gmail', action='store_true', 
                       help='Run Gmail job extraction agent')
    parser.add_argument('--run-resume', action='store_true',
                       help='Run Resume generation agent')
    parser.add_argument('--run-pipeline', action='store_true',
                       help='Run full pipeline (Gmail + Resume agents)')
    parser.add_argument('--test-connection', action='store_true',
                       help='Test Gmail API connection')
    parser.add_argument('--summary', action='store_true',
                       help='Get job alert summary')
    parser.add_argument('--run-tests', action='store_true',
                       help='Run test suite')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    print("Job Evaluation System")
    print("=" * 40)
    
    if args.test_connection:
        test_gmail_connection()
    elif args.summary:
        get_job_alert_summary()
    elif args.run_gmail:
        run_gmail_agent()
    elif args.run_resume:
        run_resume_agent()
    elif args.run_pipeline:
        run_full_pipeline()
    elif args.run_tests:
        import subprocess
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                'src/tests/test_gmail_extraction.py', '-v'
            ], cwd=os.path.dirname(__file__))
            sys.exit(result.returncode)
        except FileNotFoundError:
            print("pytest not found. Running basic tests...")
            import src.tests.test_gmail_extraction
    else:
        print("No action specified. Use --help for available options.")
        print("\nQuick start:")
        print("  python main.py --test-connection   # Test Gmail connection")
        print("  python main.py --summary          # Get job alert summary")
        print("  python main.py --run-gmail        # Run Gmail agent only")
        print("  python main.py --run-resume       # Run Resume agent only") 
        print("  python main.py --run-pipeline     # Run full pipeline")
        print("  python main.py --run-tests        # Run test suite")

if __name__ == '__main__':
    main()