"""
Monitor for Google Sheets Apply column to detect when new jobs are selected for resume generation.
"""
import time
import logging
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ApplyColumnMonitor:
    def __init__(self, sheets_manager, check_interval: int = 300):  # 5 minutes default
        self.sheets_manager = sheets_manager
        self.check_interval = check_interval
        self.last_check = None
        self.processed_jobs: Set[str] = set()  # Track processed jobs to avoid duplicates
    
    def start_monitoring(self, callback_function, max_iterations: int = None):
        """
        Start monitoring the Apply column for changes.
        
        Args:
            callback_function: Function to call when new jobs are found (takes job_data as parameter)
            max_iterations: Maximum number of check cycles (None for infinite)
        """
        logger.info(f"Starting Apply column monitoring (check interval: {self.check_interval}s)")
        
        iteration_count = 0
        
        try:
            while max_iterations is None or iteration_count < max_iterations:
                try:
                    # Get jobs marked for application
                    jobs_to_apply = self.sheets_manager.get_jobs_to_apply()
                    
                    # Filter out already processed jobs
                    new_jobs = []
                    for job in jobs_to_apply:
                        job_key = self._generate_job_key(job)
                        if job_key not in self.processed_jobs:
                            new_jobs.append(job)
                            self.processed_jobs.add(job_key)
                    
                    if new_jobs:
                        logger.info(f"Found {len(new_jobs)} new jobs marked for application")
                        
                        # Process each new job
                        for job in new_jobs:
                            try:
                                callback_function(job)
                            except Exception as e:
                                logger.error(f"Error processing job {job.get('title', 'Unknown')}: {e}")
                    else:
                        logger.debug("No new jobs found for resume generation")
                    
                    self.last_check = datetime.now()
                    iteration_count += 1
                    
                    # Wait before next check
                    if max_iterations is None or iteration_count < max_iterations:
                        time.sleep(self.check_interval)
                
                except Exception as e:
                    logger.error(f"Error in monitoring cycle: {e}")
                    time.sleep(self.check_interval)  # Wait before retrying
                    
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in monitoring: {e}")
            raise
    
    def check_once(self) -> List[Dict[str, Any]]:
        """
        Perform a single check for jobs marked for application.
        
        Returns:
            List of new jobs found
        """
        try:
            jobs_to_apply = self.sheets_manager.get_jobs_to_apply()
            
            # Filter out already processed jobs
            new_jobs = []
            for job in jobs_to_apply:
                job_key = self._generate_job_key(job)
                if job_key not in self.processed_jobs:
                    new_jobs.append(job)
                    self.processed_jobs.add(job_key)
            
            self.last_check = datetime.now()
            
            if new_jobs:
                logger.info(f"Found {len(new_jobs)} new jobs in single check")
            
            return new_jobs
            
        except Exception as e:
            logger.error(f"Error in single check: {e}")
            return []
    
    def _generate_job_key(self, job_data: Dict[str, Any]) -> str:
        """Generate a unique key for a job to track processing."""
        title = job_data.get('title', '').strip().lower()
        company = job_data.get('company', '').strip().lower()
        row_number = job_data.get('row_number', 0)
        
        # Use row number as primary key, with title+company as fallback
        return f"row_{row_number}_{title}_{company}".replace(' ', '_')
    
    def mark_job_processed(self, job_data: Dict[str, Any]):
        """Manually mark a job as processed."""
        job_key = self._generate_job_key(job_data)
        self.processed_jobs.add(job_key)
        logger.debug(f"Marked job as processed: {job_key}")
    
    def reset_processed_jobs(self):
        """Clear the processed jobs cache."""
        self.processed_jobs.clear()
        logger.info("Processed jobs cache cleared")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'processed_jobs_count': len(self.processed_jobs),
            'check_interval': self.check_interval,
            'processed_job_keys': list(self.processed_jobs)
        }
    
    def set_check_interval(self, interval_seconds: int):
        """Update the check interval."""
        self.check_interval = max(60, interval_seconds)  # Minimum 1 minute
        logger.info(f"Check interval updated to {self.check_interval} seconds")
    
    def cleanup_old_processed_jobs(self, hours_old: int = 24):
        """
        Clean up old processed job keys to prevent memory buildup.
        Note: This is a simple implementation. In production, you might want
        to store timestamps with job keys for more accurate cleanup.
        """
        # For now, just limit the size of processed_jobs set
        if len(self.processed_jobs) > 1000:
            # Keep only the most recent 500
            recent_jobs = list(self.processed_jobs)[-500:]
            self.processed_jobs = set(recent_jobs)
            logger.info("Cleaned up old processed job keys")
    
    def is_job_processed(self, job_data: Dict[str, Any]) -> bool:
        """Check if a job has already been processed."""
        job_key = self._generate_job_key(job_data)
        return job_key in self.processed_jobs