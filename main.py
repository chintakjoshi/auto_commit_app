#!/usr/bin/env python3
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
import signal

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config.settings import LOG_LEVEL, GITHUB_TOKEN, GITHUB_USERNAME
from llm.manager import LLMManager
from agents.github_agent import GitHubAgent
from agents.A1_content_agent import ContentAgent
from utils.scheduler_manager import SchedulerManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('github_agent.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GitHubAIAgentApp:
    """Main application orchestrating AI agents"""
    
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.llm_manager = LLMManager()
        self.github_agent: GitHubAgent = None
        self.A1_content_agent: ContentAgent = None
        self.scheduler = SchedulerManager()
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle interrupt signals"""
        logger.info(f"Received signal {sig}, shutting down...")
        self.running = False
    
    async def initialize(self) -> bool:
        """Initialize all components"""
        logger.info("Initializing GitHub AI Agent App...")
        
        # Test LLM connections
        logger.info("Testing LLM connections...")
        llm_status = self.llm_manager.test_connection()
        working_providers = [p for p, s in llm_status.items() if s]
        
        if not working_providers:
            logger.error("No LLM providers available. Check API keys.")
            logger.info("Available providers status:")
            for provider, status in llm_status.items():
                logger.info(f"  {provider}: {'Working' if status else 'Failed'}")
            return False
        
        logger.info(f"Working LLM providers: {', '.join(working_providers)}")
        
        # Initialize agents
        self.github_agent = GitHubAgent(self.repo_url, self.llm_manager)
        self.A1_content_agent = ContentAgent(self.llm_manager)
        
        # Initialize agents
        if not self.github_agent.initialize():
            logger.error("Failed to initialize GitHub agent")
            return False
        
        if not self.A1_content_agent.initialize():
            logger.error("Failed to initialize content agent")
            return False
        
        logger.info("All agents initialized successfully")
        
        # Log GitHub agent status
        github_status = await self.github_agent.health_check()
        logger.info(f"GitHub Agent Status: {github_status}")
        
        return True
    
    async def execute_single_commit(self) -> bool:
        """Execute a single commit cycle"""
        logger.info("Executing commit cycle...")
        
        # Ensure we have a valid repo
        if not self.github_agent.repo:
            logger.error("GitHub agent repository not initialized")
            return False
        
        # Check if repo is empty
        if self.github_agent.is_empty_repo:
            logger.info("Repository is empty, will create initial commit first")
        
        # Execute commit
        success, message = await self.github_agent.execute(self.A1_content_agent)
        
        if success:
            logger.info(f"Commit successful: {message}")
        else:
            logger.error(f"Commit failed: {message}")
        
        return success
    
    async def run(self):
        """Main run loop"""
        # Initialize
        if not await self.initialize():
            logger.error("Initialization failed. Exiting.")
            return
        
        # Execute immediate commit
        logger.info("=" * 50)
        logger.info("EXECUTING IMMEDIATE COMMIT")
        logger.info("=" * 50)
        await self.execute_single_commit()
        
        # Ask if user wants to continue with scheduled commits
        logger.info("\n" + "=" * 50)
        logger.info("IMMEDIATE COMMIT COMPLETE")
        logger.info("=" * 50)
        
        # Check if user wants to run scheduled commits
        logger.info("\nWould you like to continue with scheduled commits?")
        logger.info("Press Ctrl+C to exit or wait 10 seconds to continue...")
        
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.info("User cancelled scheduled commits")
            return
        
        # Start scheduled commits
        await self.run_scheduled_commits()
    
    async def run_scheduled_commits(self):
        """Run scheduled commits for 8 hours"""
        logger.info("=" * 50)
        logger.info("STARTING SCHEDULED COMMITS FOR 8 HOURS")
        logger.info("=" * 50)
        
        # Generate schedule
        start_time = datetime.now()
        self.scheduler.generate_new_schedule(start_time)
        
        self.running = True
        
        while self.running and not self.scheduler.should_stop():
            try:
                # Wait for next commit time
                commit_time = await self.scheduler.wait_for_next_commit()
                
                if not commit_time:
                    logger.info("No more scheduled commits")
                    break
                
                # Execute commit
                logger.info(f"Executing scheduled commit at {datetime.now().strftime('%H:%M:%S')}")
                success, message = await self.github_agent.execute(self.A1_content_agent)
                
                # Mark as completed
                self.scheduler.mark_commit_completed(success)
                
                # Log result
                if success:
                    logger.info(f"Scheduled commit successful: {message}")
                else:
                    logger.warning(f"Scheduled commit failed: {message}")
                
                # Log progress
                progress = self.scheduler.get_schedule_progress()
                logger.info(f"Progress: {progress['completed']}/{progress['total_scheduled']} commits completed")
                
            except asyncio.CancelledError:
                logger.info("Scheduled commits cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduled commit: {e}")
                # Continue with next commit
                await asyncio.sleep(5)
        
        # Log final statistics
        progress = self.scheduler.get_schedule_progress()
        logger.info("=" * 50)
        logger.info("COMMIT SESSION COMPLETED!")
        logger.info(f"Total commits attempted: {progress['completed']}")
        logger.info(f"Successful commits: {progress['successful']}")
        logger.info(f"Failed commits: {progress['completed'] - progress['successful']}")
        logger.info("=" * 50)
        
        self.running = False
    
    async def stop(self):
        """Stop the application"""
        self.running = False
        logger.info("Stopping application...")

async def main():
    """Main entry point"""
    # Configuration
    REPO_URL = "https://github.com/chintak07/github_ai_agents.git"
    
    # Check for required configuration
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        logger.error("ERROR: GITHUB_TOKEN and GITHUB_USERNAME are required!")
        logger.error("Please create a .env file with:")
        logger.error("GITHUB_TOKEN=your_token_here")
        logger.error("GITHUB_USERNAME=chintak07")
        logger.error("\nOr set them as environment variables.")
        return
    
    # Create and run app
    app = GitHubAIAgentApp(REPO_URL)
    
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal")
        await app.stop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())