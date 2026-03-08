"""
Main entry point for the Job Matching and Resume Generation System.
"""
import os
import sys
import logging
import argparse
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.job_matching_agent import JobMatchingAgent
from src.resume_generation_agent import ResumeGenerationAgent
from src.scheduler.job_scheduler import JobScheduler

# Configure logging
def setup_logging():
    """Setup logging configuration."""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/main.log'),
            logging.StreamHandler()
        ]
    )

def run_job_matching():
    """Run the job matching agent once."""
    logger = logging.getLogger(__name__)
    logger.info("Running Job Matching Agent...")
    
    try:
        agent = JobMatchingAgent()
        agent.run_daily_job_search()
        logger.info("Job matching completed successfully")
    except Exception as e:
        logger.error(f"Error in job matching: {e}")
        sys.exit(1)

def run_resume_generation():
    """Run the resume generation agent once."""
    logger = logging.getLogger(__name__)
    logger.info("Running Resume Generation Agent...")
    
    try:
        agent = ResumeGenerationAgent()
        processed_count = agent.check_once()
        logger.info(f"Resume generation completed. Processed {processed_count} jobs.")
    except Exception as e:
        logger.error(f"Error in resume generation: {e}")
        sys.exit(1)

def start_resume_monitoring():
    """Start continuous resume generation monitoring."""
    logger = logging.getLogger(__name__)
    logger.info("Starting Resume Generation Monitoring...")
    
    try:
        agent = ResumeGenerationAgent()
        agent.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Resume monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error in resume monitoring: {e}")
        sys.exit(1)

def run_scheduler():
    """Run the full scheduler with both agents."""
    logger = logging.getLogger(__name__)
    logger.info("Starting Job Scheduler...")
    
    scheduler = JobScheduler()
    
    try:
        # Initialize agents
        scheduler.initialize_agents()
        
        # Setup schedules
        scheduler.setup_daily_job_search(hour=18, minute=0)  # 6 PM daily
        scheduler.setup_resume_monitoring(interval_minutes=60)  # Every hour
        
        # List scheduled jobs
        scheduler.list_jobs()
        
        # Start scheduler
        logger.info("Scheduler started. Press Ctrl+C to stop.")
        scheduler.start_scheduler()
        
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        scheduler.stop_scheduler()
    except Exception as e:
        logger.error(f"Error in scheduler: {e}")
        scheduler.stop_scheduler()
        sys.exit(1)

def print_status():
    """Print system status and configuration."""
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*60)
    print("JOB MATCHING AND RESUME GENERATION SYSTEM")
    print("="*60)
    
    # Check environment variables
    required_vars = [
        'OPENAI_API_KEY', 'GOOGLE_DRIVE_CREDENTIALS', 'GOOGLE_SHEETS_ID',
        'LINKEDIN_PDF_ID', 'SUMMARY_TXT_ID', 'LINKEDIN_EMAIL', 'SENDER_EMAIL'
    ]
    
    print("\nEnvironment Configuration:")
    for var in required_vars:
        value = os.getenv(var)
        status = "✓ Set" if value else "✗ Missing"
        print(f"  {var}: {status}")
    
    # Check directories
    print("\nDirectory Structure:")
    dirs_to_check = ['logs', 'data', 'templates', 'config']
    for dir_name in dirs_to_check:
        exists = os.path.exists(dir_name)
        status = "✓ Exists" if exists else "✗ Missing"
        print(f"  {dir_name}/: {status}")
    
    print("\nAvailable Commands:")
    print("  python main.py job-matching      - Run job matching once")
    print("  python main.py resume-generation - Run resume generation once") 
    print("  python main.py resume-monitoring - Start continuous resume monitoring")
    print("  python main.py scheduler         - Start full automated scheduler")
    print("  python main.py status           - Show this status information")
    
    print(f"\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

def main():
    """Main entry point with command line argument parsing."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description='Job Matching and Resume Generation System')
    parser.add_argument('command', choices=[
        'job-matching', 'resume-generation', 'resume-monitoring', 'scheduler', 'status'
    ], help='Command to execute')
    
    # Parse arguments
    if len(sys.argv) == 1:
        print_status()
        return
    
    args = parser.parse_args()
    
    logger.info(f"Starting system with command: {args.command}")
    
    try:
        if args.command == 'job-matching':
            run_job_matching()
        elif args.command == 'resume-generation':
            run_resume_generation()
        elif args.command == 'resume-monitoring':
            start_resume_monitoring()
        elif args.command == 'scheduler':
            run_scheduler()
        elif args.command == 'status':
            print_status()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()