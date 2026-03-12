"""
Tick-based scheduler for Emy.

Jobs are registered with a cadence (seconds) and executed on schedule.
No external cron required - runs inside main loop.
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger('EMyScheduler')


class Job:
    """Represents a scheduled job."""

    def __init__(self, name: str, callable_fn: Callable, cadence_seconds: int,
                 *args, **kwargs):
        """Initialize a job."""
        self.name = name
        self.callable = callable_fn
        self.cadence_seconds = cadence_seconds
        self.args = args
        self.kwargs = kwargs
        self.next_run_time = datetime.now()  # Run immediately on first tick
        self.last_run_time: Optional[datetime] = None
        self.last_success = False
        self.last_error: Optional[str] = None

    def is_due(self, current_time: datetime) -> bool:
        """Check if job is due to run."""
        return current_time >= self.next_run_time

    def execute(self, current_time: datetime) -> bool:
        """Execute the job and update schedule."""
        try:
            self.callable(*self.args, **self.kwargs)
            self.last_run_time = current_time
            self.last_success = True
            self.last_error = None
            self.next_run_time = current_time + timedelta(seconds=self.cadence_seconds)
            return True
        except Exception as e:
            self.last_run_time = current_time
            self.last_success = False
            self.last_error = str(e)
            self.next_run_time = current_time + timedelta(seconds=self.cadence_seconds)
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dict for display."""
        return {
            'name': self.name,
            'cadence_seconds': self.cadence_seconds,
            'next_run_time': self.next_run_time.isoformat(),
            'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
            'last_success': self.last_success,
            'last_error': self.last_error
        }


class EMyScheduler:
    """Tick-based job scheduler."""

    def __init__(self):
        """Initialize scheduler."""
        self.jobs: Dict[str, Job] = {}
        self.logger = logging.getLogger('EMyScheduler')

    def register_job(self, name: str, callable_fn: Callable, cadence_seconds: int,
                     *args, **kwargs) -> bool:
        """
        Register a job to run on schedule.

        Args:
            name: Unique job name
            callable_fn: Function to call
            cadence_seconds: How often to run (in seconds)
            *args, **kwargs: Arguments for callable

        Returns:
            True if registered
        """
        try:
            job = Job(name, callable_fn, cadence_seconds, *args, **kwargs)
            self.jobs[name] = job
            self.logger.info(f"[REGISTER] Job {name}: every {cadence_seconds}s")
            return True
        except Exception as e:
            self.logger.error(f"Error registering job {name}: {e}")
            return False

    def tick(self, current_time: datetime = None) -> List[str]:
        """
        Execute jobs that are due.

        Args:
            current_time: Current time (default: now)

        Returns:
            List of executed job names
        """
        if current_time is None:
            current_time = datetime.now()

        executed = []

        for job_name, job in self.jobs.items():
            if job.is_due(current_time):
                try:
                    success = job.execute(current_time)
                    executed.append(job_name)
                    status = "OK" if success else "FAIL"
                    self.logger.info(f"[RUN] {job_name}: {status}")
                except Exception as e:
                    self.logger.error(f"[ERROR] {job_name}: {e}")

        return executed

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all registered jobs with status."""
        return [job.to_dict() for job in self.jobs.values()]

    def get_job(self, name: str) -> Optional[Job]:
        """Get a job by name."""
        return self.jobs.get(name)

    def unregister_job(self, name: str) -> bool:
        """Unregister a job."""
        if name in self.jobs:
            del self.jobs[name]
            self.logger.info(f"[UNREGISTER] Job {name}")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        total_jobs = len(self.jobs)
        executed = sum(1 for job in self.jobs.values() if job.last_run_time)
        successful = sum(1 for job in self.jobs.values() if job.last_success)

        next_jobs = sorted(self.jobs.values(), key=lambda j: j.next_run_time)
        next_due = next_jobs[0].name if next_jobs else None

        return {
            'total_jobs': total_jobs,
            'executed': executed,
            'successful': successful,
            'next_due': next_due
        }
