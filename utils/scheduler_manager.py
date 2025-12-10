import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from utils.human_patterns import CommitPatternGenerator
from config.settings import MIN_COMMITS_PER_DAY, MAX_COMMITS_PER_DAY, COMMIT_WINDOW_HOURS

from utils.logger import setup_logger
logger = setup_logger(__name__)

class SchedulerManager:
    """Manages scheduling of commits"""
    
    def __init__(self):
        self.pattern_generator = CommitPatternGenerator(
            min_commits=MIN_COMMITS_PER_DAY,
            max_commits=MAX_COMMITS_PER_DAY,
            window_hours=COMMIT_WINDOW_HOURS,
            randomize=True
        )
        self.schedule: List[datetime] = []
        self.next_commit_idx = 0
        self.is_running = False
        self.start_time = None
        self.total_commits = 0
        self.successful_commits = 0
    
    def generate_new_schedule(self, start_from: Optional[datetime] = None):
        """Generate a new random schedule"""
        start_time = start_from or datetime.now()
        self.schedule = self.pattern_generator.generate_commit_schedule(start_time)
        self.next_commit_idx = 0
        self.start_time = start_time
        
        # Log schedule
        logger.info("Generated commit schedule:")
        for i, commit_time in enumerate(self.schedule[:10]):  # Show first 10
            logger.info(f"  {i+1:2d}. {commit_time.strftime('%H:%M:%S')}")
        if len(self.schedule) > 10:
            logger.info(f"  ... and {len(self.schedule) - 10} more")
        
        return self.schedule
    
    def get_next_commit_time(self) -> Optional[datetime]:
        """Get the next scheduled commit time"""
        if self.next_commit_idx < len(self.schedule):
            return self.schedule[self.next_commit_idx]
        return None
    
    def mark_commit_completed(self, success: bool = True):
        """Mark the current commit as completed"""
        self.next_commit_idx += 1
        self.total_commits += 1
        if success:
            self.successful_commits += 1
    
    def get_schedule_progress(self) -> Dict:
        """Get current schedule progress"""
        now = datetime.now()
        upcoming = [t for t in self.schedule if t > now]
        
        return {
            "total_scheduled": len(self.schedule),
            "completed": self.next_commit_idx,
            "remaining": len(self.schedule) - self.next_commit_idx,
            "upcoming": len(upcoming),
            "successful": self.successful_commits,
            "next_commit": upcoming[0] if upcoming else None,
            "window_end": self.start_time + timedelta(hours=COMMIT_WINDOW_HOURS) if self.start_time else None
        }
    
    async def wait_for_next_commit(self) -> Optional[datetime]:
        """Wait until the next commit time"""
        if self.next_commit_idx >= len(self.schedule):
            return None
        
        next_time = self.schedule[self.next_commit_idx]
        now = datetime.now()
        
        if next_time <= now:
            # Commit is due now or overdue
            return next_time
        
        # Calculate wait time
        wait_seconds = (next_time - now).total_seconds()
        
        if wait_seconds > 0:
            # Add some random jitter to avoid exact timing patterns
            jitter = random.uniform(-30, 30)  # ±30 seconds
            wait_seconds = max(1, wait_seconds + jitter)
            
            logger.info(f"Waiting {wait_seconds:.0f} seconds until next commit at {next_time.strftime('%H:%M:%S')}")
            await asyncio.sleep(wait_seconds)
        
        return next_time
    
    def should_stop(self) -> bool:
        """Check if scheduler should stop"""
        if not self.start_time:
            return False
        
        # Stop after window hours
        window_end = self.start_time + timedelta(hours=COMMIT_WINDOW_HOURS)
        return datetime.now() >= window_end or self.next_commit_idx >= len(self.schedule)