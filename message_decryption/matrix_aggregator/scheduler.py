import asyncio
import schedule
import time
import logging
from datetime import datetime
from typing import Callable

logger = logging.getLogger(__name__)

class MessageScheduler:
    def __init__(self, sync_function: Callable, frequency: str = "daily", time_str: str = "02:00"):
        self.sync_function = sync_function
        self.frequency = frequency
        self.time_str = time_str
        self.running = False
    
    def setup_schedule(self):
        """Setup the schedule based on configuration"""
        schedule.clear()
        
        if self.frequency == "daily":
            schedule.every().day.at(self.time_str).do(self._run_sync_job)
        elif self.frequency == "hourly":
            schedule.every().hour.do(self._run_sync_job)
        elif self.frequency == "weekly":
            schedule.every().week.do(self._run_sync_job)
        else:
            logger.warning(f"Unknown frequency: {self.frequency}, defaulting to daily")
            schedule.every().day.at(self.time_str).do(self._run_sync_job)
        
        logger.info(f"Scheduled sync: {self.frequency} at {self.time_str}")
    
    def _run_sync_job(self):
        """Wrapper to run async sync function"""
        try:
            asyncio.run(self.sync_function())
            logger.info(f"Scheduled sync completed at {datetime.now()}")
        except Exception as e:
            logger.error(f"Scheduled sync failed: {e}")
    
    def run_scheduler(self):
        """Run the scheduler in blocking mode"""
        self.setup_schedule()
        self.running = True
        
        logger.info("Scheduler started")
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        logger.info("Scheduler stopped")