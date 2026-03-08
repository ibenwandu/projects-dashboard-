"""
Job scheduler for automating the job matching and resume generation agents.
"""
import logging
from datetime import datetime, time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from job_matching_agent import JobMatchingAgent
from resume_generation_agent import ResumeGenerationAgent

logger = logging.getLogger(__name__)

class JobScheduler:
    def __init__(self, use_background_scheduler: bool = False):
        """
        Initialize the job scheduler.
        
        Args:
            use_background_scheduler: If True, uses BackgroundScheduler (non-blocking)
                                    If False, uses BlockingScheduler (blocking)
        """
        if use_background_scheduler:
            self.scheduler = BackgroundScheduler()
        else:
            self.scheduler = BlockingScheduler()
        
        self.job_matching_agent = None
        self.resume_generation_agent = None
        
        # Configure logging for APScheduler
        logging.getLogger('apscheduler').setLevel(logging.INFO)
    
    def initialize_agents(self):
        """Initialize both agents."""
        try:
            logger.info("Initializing Job Matching Agent...")
            self.job_matching_agent = JobMatchingAgent()
            
            logger.info("Initializing Resume Generation Agent...")
            self.resume_generation_agent = ResumeGenerationAgent()
            
            logger.info("Both agents initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            raise
    
    def setup_daily_job_search(self, hour: int = 18, minute: int = 0):
        """
        Setup daily job search at specified time.
        
        Args:
            hour: Hour to run (24-hour format, default 18 = 6 PM)
            minute: Minute to run (default 0)
        """
        try:
            self.scheduler.add_job(
                func=self._run_job_matching_agent,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_job_search',
                name='Daily Job Search',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"Daily job search scheduled for {hour:02d}:{minute:02d}")
            
        except Exception as e:
            logger.error(f"Error setting up daily job search: {e}")
            raise
    
    def setup_resume_monitoring(self, interval_minutes: int = 60):
        """
        Setup resume generation monitoring at regular intervals.
        
        Args:
            interval_minutes: Check interval in minutes (default 60)
        """
        try:
            self.scheduler.add_job(
                func=self._run_resume_generation_check,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='resume_monitoring',
                name='Resume Generation Monitoring',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"Resume monitoring scheduled every {interval_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error setting up resume monitoring: {e}")
            raise
    
    def setup_custom_schedule(self, job_function, trigger, job_id: str, name: str):
        """
        Setup a custom scheduled job.
        
        Args:
            job_function: Function to execute
            trigger: APScheduler trigger object
            job_id: Unique job ID
            name: Human-readable job name
        """
        try:
            self.scheduler.add_job(
                func=job_function,
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"Custom job '{name}' scheduled with ID '{job_id}'")
            
        except Exception as e:
            logger.error(f"Error setting up custom schedule: {e}")
            raise
    
    def _run_job_matching_agent(self):
        """Execute the job matching agent."""
        try:
            logger.info("Starting scheduled job matching process")
            
            if not self.job_matching_agent:
                self.job_matching_agent = JobMatchingAgent()
            
            self.job_matching_agent.run_daily_job_search()
            logger.info("Scheduled job matching completed successfully")
            
        except Exception as e:
            logger.error(f"Error in scheduled job matching: {e}")
            # Send error notification if possible
            try:
                if self.job_matching_agent:
                    self.job_matching_agent._send_error_notification(str(e))
            except:
                pass
    
    def _run_resume_generation_check(self):
        """Execute a single resume generation check."""
        try:
            logger.info("Starting scheduled resume generation check")
            
            if not self.resume_generation_agent:
                self.resume_generation_agent = ResumeGenerationAgent()
            
            processed_count = self.resume_generation_agent.check_once()
            logger.info(f"Scheduled resume check completed. Processed {processed_count} jobs.")
            
        except Exception as e:
            logger.error(f"Error in scheduled resume generation: {e}")
            # Send error notification if possible
            try:
                if self.resume_generation_agent:
                    self.resume_generation_agent._send_error_notification(str(e))
            except:
                pass
    
    def start_scheduler(self):
        """Start the scheduler."""
        try:
            logger.info("Starting job scheduler...")
            self.scheduler.start()
            logger.info("Job scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise
    
    def stop_scheduler(self):
        """Stop the scheduler gracefully."""
        try:
            logger.info("Stopping job scheduler...")
            self.scheduler.shutdown(wait=True)
            logger.info("Job scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def list_jobs(self):
        """List all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        
        if not jobs:
            logger.info("No scheduled jobs found")
            return
        
        logger.info(f"Scheduled jobs ({len(jobs)}):")
        for job in jobs:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'Never'
            logger.info(f"  - {job.name} (ID: {job.id}) - Next run: {next_run}")
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job '{job_id}' removed")
        except Exception as e:
            logger.error(f"Error removing job '{job_id}': {e}")
    
    def run_job_now(self, job_id: str):
        """Execute a scheduled job immediately."""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.func()
                logger.info(f"Job '{job_id}' executed manually")
            else:
                logger.error(f"Job '{job_id}' not found")
        except Exception as e:
            logger.error(f"Error running job '{job_id}': {e}")

def main():
    """Main function for running the scheduler."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scheduler.log'),
            logging.StreamHandler()
        ]
    )
    
    scheduler = JobScheduler(use_background_scheduler=False)
    
    try:
        # Initialize agents
        scheduler.initialize_agents()
        
        # Setup schedules based on requirements from CLAUDE.md
        scheduler.setup_daily_job_search(hour=18, minute=0)  # 6 PM daily
        scheduler.setup_resume_monitoring(interval_minutes=60)  # Every hour
        
        # List scheduled jobs
        scheduler.list_jobs()
        
        # Start scheduler (this will block)
        logger.info("Starting scheduler. Press Ctrl+C to stop.")
        scheduler.start_scheduler()
        
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        scheduler.stop_scheduler()
    except Exception as e:
        logger.error(f"Fatal error in scheduler: {e}")
        scheduler.stop_scheduler()
        raise

if __name__ == "__main__":
    main()