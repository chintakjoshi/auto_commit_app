import random
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from enum import Enum
import logging

from utils.logger import setup_logger
logger = setup_logger(__name__)

class CommitPatternGenerator:
    """Generator for randomized commit patterns"""
    
    def __init__(self, min_commits: int = 20, max_commits: int = 30, 
                 window_hours: int = 8, randomize: bool = True):
        self.min_commits = min_commits
        self.max_commits = max_commits
        self.window_hours = window_hours
        self.randomize = randomize
        self.last_commit_time = None
        
    def generate_commit_schedule(self, start_time: datetime) -> List[datetime]:
        """
        Generate a random commit schedule for the next 8 hours
        Returns: List of commit times
        """
        if not self.randomize:
            # Evenly distribute commits
            num_commits = self.max_commits
            interval = self.window_hours * 3600 / num_commits
            return [start_time + timedelta(seconds=i*interval) 
                    for i in range(num_commits)]
        
        # Random number of commits (20-30)
        num_commits = random.randint(self.min_commits, self.max_commits)
        logger.info(f"Generating {num_commits} commits over {self.window_hours} hours")
        
        commit_times = []
        
        # Use exponential distribution for natural-looking intervals
        # with some clustering to simulate "work sessions"
        current_time = start_time
        end_time = start_time + timedelta(hours=self.window_hours)
        
        while len(commit_times) < num_commits and current_time < end_time:
            # Base interval: 10-45 minutes (600-2700 seconds)
            base_interval = random.uniform(600, 2700)
            
            # Add some randomness
            random_factor = random.uniform(0.7, 1.3)
            interval = base_interval * random_factor
            
            # Chance of clustering (multiple commits close together)
            if random.random() < 0.2:  # 20% chance of clustering
                cluster_size = random.randint(2, 4)
                for _ in range(cluster_size):
                    if len(commit_times) >= num_commits or current_time >= end_time:
                        break
                    commit_times.append(current_time)
                    # Small gap between clustered commits (1-5 minutes)
                    current_time += timedelta(seconds=random.uniform(60, 300))
            else:
                # Single commit
                commit_times.append(current_time)
                current_time += timedelta(seconds=interval)
        
        # Ensure we have the right number of commits
        if len(commit_times) > num_commits:
            commit_times = commit_times[:num_commits]
        elif len(commit_times) < num_commits:
            # Fill remaining slots with random times
            while len(commit_times) < num_commits:
                random_time = start_time + timedelta(
                    seconds=random.uniform(0, self.window_hours * 3600)
                )
                commit_times.append(random_time)
        
        # Sort times
        commit_times.sort()
        
        # Avoid patterns by adding small random jitter
        jittered_times = []
        for time in commit_times:
            jitter = timedelta(seconds=random.uniform(-120, 120))
            jittered_time = time + jitter
            # Ensure time is within window
            if start_time <= jittered_time <= end_time:
                jittered_times.append(jittered_time)
            else:
                jittered_times.append(time)
        
        logger.info(f"Generated {len(jittered_times)} commit times")
        return jittered_times
    
    def should_commit_now(self) -> bool:
        """Check if a commit should be made right now (for immediate first commit)"""
        return True