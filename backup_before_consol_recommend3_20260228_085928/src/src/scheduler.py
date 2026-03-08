"""Schedule analysis at specific times"""

import os
from datetime import datetime, time
from typing import List, Optional
from dotenv import load_dotenv
import pytz
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

class AnalysisScheduler:
    """Manage scheduled analysis times"""
    
    def __init__(self):
        """Initialize scheduler"""
        # Default: Run every hour (00:00, 01:00, 02:00, ..., 23:00)
        # Generate all 24 hours programmatically
        default_times = ",".join([f"{hour:02d}:00" for hour in range(24)])
        times_str = os.getenv('ANALYSIS_TIMES', default_times)
        
        # Get timezone (default to EST/EDT)
        timezone_str = os.getenv('ANALYSIS_TIMEZONE', 'America/New_York')
        try:
            self.timezone = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {timezone_str}, using EST/EDT")
            self.timezone = pytz.timezone('America/New_York')
        
        self.scheduled_times = self._parse_times(times_str)
        # Log summary instead of all 24 times
        if len(self.scheduled_times) == 24:
            logger.info(f"Analysis scheduled for: Every hour (00:00-23:00) ({timezone_str})")
        else:
            logger.info(f"Analysis scheduled for: {[t.strftime('%H:%M') for t in self.scheduled_times]} ({timezone_str})")
    
    def _parse_times(self, times_str: str) -> List[time]:
        """Parse comma-separated time string into time objects"""
        times = []
        for time_str in times_str.split(','):
            time_str = time_str.strip()
            try:
                hour, minute = map(int, time_str.split(':'))
                times.append(time(hour, minute))
            except ValueError:
                logger.warning(f"Invalid time format: {time_str}, skipping")
        return sorted(times)
    
    def should_run_analysis(self, current_time: datetime = None) -> bool:
        """
        Check if analysis should run at current time
        
        Args:
            current_time: Current datetime (defaults to now, in UTC)
            
        Returns:
            True if analysis should run
        """
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        # Convert current time to target timezone (EST/EDT)
        if current_time.tzinfo is None:
            # Assume UTC if no timezone info
            current_time = pytz.UTC.localize(current_time)
        
        current_time_est = current_time.astimezone(self.timezone)
        current_time_only = current_time_est.time()
        
        # Check if current time matches any scheduled time (within 5 minutes)
        for scheduled_time in self.scheduled_times:
            if self._times_match(current_time_only, scheduled_time, tolerance_minutes=5):
                return True
        
        return False
    
    def _times_match(self, time1: time, time2: time, tolerance_minutes: int = 5) -> bool:
        """Check if two times match within tolerance"""
        minutes1 = time1.hour * 60 + time1.minute
        minutes2 = time2.hour * 60 + time2.minute
        diff = abs(minutes1 - minutes2)
        return diff <= tolerance_minutes
    
    def get_next_analysis_time(self, current_time: datetime = None) -> Optional[datetime]:
        """
        Get next scheduled analysis time (returns UTC datetime)
        
        Args:
            current_time: Current datetime (defaults to now, in UTC)
            
        Returns:
            Next analysis datetime (in UTC)
        """
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        # Convert current time to target timezone (EST/EDT)
        if current_time.tzinfo is None:
            # Assume UTC if no timezone info
            current_time = pytz.UTC.localize(current_time)
        
        current_time_est = current_time.astimezone(self.timezone)
        current_time_only = current_time_est.time()
        current_date_est = current_time_est.date()
        
        # Find next scheduled time today in EST
        for scheduled_time in self.scheduled_times:
            if current_time_only <= scheduled_time:
                # Create datetime in EST timezone
                next_analysis_est = self.timezone.localize(
                    datetime.combine(current_date_est, scheduled_time)
                )
                # Convert to UTC for return
                return next_analysis_est.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # If no time today, use first time tomorrow in EST
        if self.scheduled_times:
            from datetime import timedelta
            tomorrow_est = current_date_est + timedelta(days=1)
            next_analysis_est = self.timezone.localize(
                datetime.combine(tomorrow_est, self.scheduled_times[0])
            )
            # Convert to UTC for return
            return next_analysis_est.astimezone(pytz.UTC).replace(tzinfo=None)
        
        return None

class AgentScheduler:
    """Manage scheduled agent runs (multi-agent workflow)"""

    def __init__(self):
        """Initialize agent scheduler"""
        # Default: Run agents at 5:30 PM EST (17:30)
        agent_run_time = os.getenv('AGENT_RUN_TIME', '17:30')

        # Get timezone (default to EST/EDT)
        timezone_str = os.getenv('AGENT_TIMEZONE', 'America/New_York')
        try:
            self.timezone = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {timezone_str}, using EST/EDT")
            self.timezone = pytz.timezone('America/New_York')

        # Parse agent run time
        try:
            hour, minute = map(int, agent_run_time.split(':'))
            self.agent_run_time = time(hour, minute)
            logger.info(f"Agent workflow scheduled for: {self.agent_run_time.strftime('%H:%M')} ({timezone_str})")
        except ValueError:
            logger.warning(f"Invalid AGENT_RUN_TIME format: {agent_run_time}, using default 17:30")
            self.agent_run_time = time(17, 30)

    def should_run_agents(self, current_time: datetime = None) -> bool:
        """
        Check if agents should run at current time

        Args:
            current_time: Current datetime (defaults to now, in UTC)

        Returns:
            True if agents should run
        """
        if current_time is None:
            current_time = datetime.now(pytz.UTC)

        # Convert current time to target timezone (EST/EDT)
        if current_time.tzinfo is None:
            current_time = pytz.UTC.localize(current_time)

        current_time_est = current_time.astimezone(self.timezone)
        current_time_only = current_time_est.time()

        # Check if current time matches agent run time (within 5 minutes)
        minutes1 = current_time_only.hour * 60 + current_time_only.minute
        minutes2 = self.agent_run_time.hour * 60 + self.agent_run_time.minute
        diff = abs(minutes1 - minutes2)

        return diff <= 5  # 5-minute tolerance

    def get_next_agent_run_time(self, current_time: datetime = None) -> Optional[datetime]:
        """
        Get next scheduled agent run time (returns UTC datetime)

        Args:
            current_time: Current datetime (defaults to now, in UTC)

        Returns:
            Next agent run datetime (in UTC)
        """
        if current_time is None:
            current_time = datetime.now(pytz.UTC)

        # Convert current time to target timezone (EST/EDT)
        if current_time.tzinfo is None:
            current_time = pytz.UTC.localize(current_time)

        current_time_est = current_time.astimezone(self.timezone)
        current_time_only = current_time_est.time()
        current_date_est = current_time_est.date()

        # Check if agent run time is still today
        if current_time_only <= self.agent_run_time:
            next_run_est = self.timezone.localize(
                datetime.combine(current_date_est, self.agent_run_time)
            )
            return next_run_est.astimezone(pytz.UTC).replace(tzinfo=None)

        # If agent already ran today, next run is tomorrow
        from datetime import timedelta
        tomorrow_est = current_date_est + timedelta(days=1)
        next_run_est = self.timezone.localize(
            datetime.combine(tomorrow_est, self.agent_run_time)
        )
        return next_run_est.astimezone(pytz.UTC).replace(tzinfo=None)

