import os
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import subprocess
import asyncio
from git import Repo, GitCommandError, InvalidGitRepositoryError

from agents.base_agent import BaseAgent
from config.settings import GITHUB_TOKEN, GITHUB_USERNAME, REPO_BASE_PATH

logger = logging.getLogger(__name__)

class GitHubAgent(BaseAgent):
    """Agent for GitHub operations"""
    
    def __init__(self, repo_url: str, llm_manager=None):
        super().__init__("github_agent", llm_manager)
        self.repo_url = repo_url
        self.repo_name = repo_url.split('/')[-1].replace('.git', '')
        self.repo_path = Path(REPO_BASE_PATH) / self.repo_name
        self.repo: Optional[Repo] = None
        self.is_empty_repo = False
        self.initial_commit_done = False
    
    def _setup(self):
        """Setup GitHub repository"""
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Check if it's a fresh directory (no .git folder)
            git_dir = self.repo_path / ".git"
            
            if not git_dir.exists():
                logger.info(f"Cloning repository: {self.repo_url}")
                # Use authenticated URL if token is provided
                if GITHUB_TOKEN and GITHUB_USERNAME:
                    auth_url = self.repo_url.replace(
                        "https://github.com/",
                        f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/"
                    )
                    self.repo = Repo.clone_from(auth_url, self.repo_path)
                else:
                    self.repo = Repo.clone_from(self.repo_url, self.repo_path)
                
                # Check if repository is empty by checking if there are any commits
                self._check_if_repo_empty()
                    
            else:
                logger.info(f"Opening existing repository: {self.repo_path}")
                self.repo = Repo(self.repo_path)
                self._check_if_repo_empty()
                
        except Exception as e:
            logger.error(f"Failed to setup repository: {e}")
            # Try to initialize a new repo
            self._initialize_new_repo()
    
    def _initialize_new_repo(self):
        """Initialize a new Git repository"""
        try:
            logger.info("Initializing new Git repository...")
            self.repo = Repo.init(self.repo_path)
            
            # Add remote if we have the URL
            if self.repo_url:
                try:
                    if "origin" in self.repo.remotes:
                        self.repo.delete_remote('origin')
                    
                    if GITHUB_TOKEN and GITHUB_USERNAME:
                        auth_url = self.repo_url.replace(
                            "https://github.com/",
                            f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/"
                        )
                        self.repo.create_remote('origin', auth_url)
                    else:
                        self.repo.create_remote('origin', self.repo_url)
                except Exception as e:
                    logger.warning(f"Could not add remote: {e}")
            
            self.is_empty_repo = True
            logger.info("New Git repository initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize new repository: {e}")
            raise
    
    def _check_if_repo_empty(self):
        """Check if repository is empty (no commits)"""
        try:
            # Try to get the list of commits
            commits = list(self.repo.iter_commits())
            self.is_empty_repo = len(commits) == 0
            if self.is_empty_repo:
                logger.warning("Repository has no commits (empty repository)")
            else:
                logger.info(f"Repository has {len(commits)} commits")
        except ValueError:
            # This happens when there are no commits
            self.is_empty_repo = True
            logger.warning("Repository has no commits (empty repository)")
        except Exception as e:
            logger.error(f"Error checking if repo is empty: {e}")
            self.is_empty_repo = True
    
    async def create_initial_commit(self) -> bool:
        """Create initial commit for empty repository"""
        try:
            logger.info("Creating initial commit for empty repository...")
            
            # Create a README file
            readme_content = """# GitHub AI Agents Repository

This repository is automatically maintained by AI agents that generate content and commit changes.

## About
- Content is generated using various LLM providers (NVIDIA, Google, OpenRouter)
- Commits are scheduled randomly over 8-hour periods
- Each commit contains unique articles or updates

## Automation
This repository demonstrates automated content generation and Git operations using AI agents.

*Generated by GitHub AI Agent System*
"""
            
            readme_path = self.repo_path / "README.md"
            readme_path.write_text(readme_content, encoding='utf-8')
            
            # Add and commit
            self.repo.git.add(A=True)
            self.repo.index.commit("Initial commit: Setup repository structure")
            
            self.is_empty_repo = False
            self.initial_commit_done = True
            logger.info("Initial commit created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create initial commit: {e}")
            return False
    
    async def pull_latest(self) -> bool:
        """Pull latest changes from remote"""
        try:
            # If repository is empty or has no remote, nothing to pull
            if self.is_empty_repo or not self.repo.remotes:
                logger.info("No remote or empty repo, skipping pull")
                return True
                
            origin = self.repo.remotes.origin
            origin.pull()
            logger.info("Successfully pulled latest changes")
            return True
        except GitCommandError as e:
            # If pull fails because branch doesn't exist upstream, that's OK for empty repo
            if "no upstream branch" in str(e).lower():
                logger.info("No upstream branch set yet (normal for new repos)")
                return True
            logger.error(f"Failed to pull: {e}")
            return False
    
    async def commit_and_push(self, commit_message: str, files: Optional[list] = None) -> Tuple[bool, str]:
        """Commit and push changes, returns (success, message)"""
        try:
            # Stage files
            if files:
                for file in files:
                    self.repo.git.add(file)
            else:
                self.repo.git.add(A=True)
            
            # Check if there are changes to commit
            status_output = self.repo.git.status(porcelain=True)
            if not status_output.strip():
                return False, "No changes to commit"
            
            # Commit
            self.repo.index.commit(commit_message)
            logger.info(f"Committed: {commit_message}")
            
            # Push to remote if we have a remote
            if self.repo.remotes:
                origin = self.repo.remotes.origin
                
                # For first push, we need to set upstream
                try:
                    origin.push()
                except GitCommandError as push_error:
                    if "no upstream branch" in str(push_error).lower():
                        current_branch = self.repo.active_branch.name
                        origin.push(refspec=f'{current_branch}', set_upstream=True)
                    else:
                        raise push_error
                
                logger.info("Successfully pushed to remote")
                return True, commit_message
            else:
                logger.warning("No remote configured, commit done locally only")
                return True, f"{commit_message} (local only)"
            
        except GitCommandError as e:
            logger.error(f"Commit/push failed: {e}")
            # If error is about HEAD, try creating initial commit
            if "HEAD" in str(e) and ("did not resolve" in str(e) or "not a valid object" in str(e)):
                logger.info("HEAD reference issue detected, attempting to create initial commit...")
                self.is_empty_repo = True
                if await self.create_initial_commit():
                    # Try commit again after initial commit
                    return await self.commit_and_push(commit_message, files)
                else:
                    return False, "Failed to create initial commit"
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error in commit/push: {e}")
            return False, str(e)
    
    async def create_file(self, filepath: str, content: str) -> bool:
        """Create a new file in the repository"""
        try:
            full_path = self.repo_path / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Created file: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to create file {filepath}: {e}")
            return False
    
    async def generate_commit_message(self, changes_summary: str = "") -> str:
        """Generate a commit message using LLM"""
        prompt = f"""Generate a concise, professional commit message for a GitHub repository.
        
        Context: This is part of an automated content generation system.
        Changes: {changes_summary if changes_summary else "Added or modified content files"}
        
        Requirements:
        - Use conventional commit format if appropriate
        - Keep it under 72 characters
        - Make it descriptive but concise
        - Use present tense
        
        Commit message:"""
        
        message = self.generate_with_llm(prompt)
        
        # Clean up and ensure it's not too long
        if message:
            message = message.strip().strip('"\'')
            # Extract just the commit message (remove explanations)
            if '\n' in message:
                message = message.split('\n')[0].strip()
            if len(message) > 72:
                message = message[:69] + "..."
        
        return message or f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    async def execute(self, content_agent=None) -> Tuple[bool, str]:
        """
        Execute a commit cycle
        Returns: (success, commit_message)
        """
        try:
            # Ensure we have a valid repo
            if not self.repo:
                logger.error("Repository not initialized")
                return False, "Repository not initialized"
            
            # If repository is empty, we need to handle it specially
            if self.is_empty_repo:
                logger.info("Repository is empty, will create article and initial commit together...")
                
                # Generate content first
                article_content = ""
                filename = ""
                
                if content_agent:
                    content, fname = await content_agent.execute()
                    if content and fname:
                        article_content = content
                        filename = fname
                        await self.create_file(filename, article_content)
                        changes_summary = f"Added new article: {filename}"
                    else:
                        # Create a simple timestamp file as fallback
                        timestamp = datetime.now().isoformat()
                        filename = f"updates/update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        await self.create_file(filename, f"Automated update at {timestamp}")
                        changes_summary = f"Added timestamp file: {filename}"
                else:
                    # Create a simple timestamp file
                    timestamp = datetime.now().isoformat()
                    filename = f"updates/update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    await self.create_file(filename, f"Automated update at {timestamp}")
                    changes_summary = f"Added timestamp file: {filename}"
                
                # Generate commit message
                commit_message = await self.generate_commit_message(changes_summary)
                
                # Create initial commit with both README and article
                logger.info("Creating initial commit with README and article...")
                
                # Create README
                readme_content = """# GitHub AI Agents Repository

    This repository is automatically maintained by AI agents that generate content and commit changes.

    ## About
    - Content is generated using various LLM providers (NVIDIA, Google, OpenRouter)
    - Commits are scheduled randomly over 8-hour periods
    - Each commit contains unique articles or updates

    ## Automation
    This repository demonstrates automated content generation and Git operations using AI agents.

    *Generated by GitHub AI Agent System*
    """
                readme_path = self.repo_path / "README.md"
                readme_path.write_text(readme_content, encoding='utf-8')
                
                # Add all files and commit
                self.repo.git.add(A=True)
                self.repo.index.commit(commit_message)
                
                self.is_empty_repo = False
                self.initial_commit_done = True
                
                # Push if we have remote
                if self.repo.remotes:
                    origin = self.repo.remotes.origin
                    try:
                        current_branch = self.repo.active_branch.name
                        origin.push(refspec=f'{current_branch}', set_upstream=True)
                        logger.info("Successfully pushed initial commit to remote")
                    except Exception as e:
                        logger.error(f"Failed to push initial commit: {e}")
                        return False, f"Initial commit created but push failed: {e}"
                
                logger.info(f"Initial commit successful: {commit_message}")
                return True, commit_message
            
            else:
                # Normal flow for non-empty repository
                # Pull latest changes
                await self.pull_latest()
                
                # Generate content
                article_content = ""
                filename = ""
                
                if content_agent:
                    content, fname = await content_agent.execute()
                    if content and fname:
                        article_content = content
                        filename = fname
                        await self.create_file(filename, article_content)
                        changes_summary = f"Added new article: {filename}"
                    else:
                        # Create a simple timestamp file as fallback
                        timestamp = datetime.now().isoformat()
                        filename = f"updates/update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        await self.create_file(filename, f"Automated update at {timestamp}")
                        changes_summary = f"Added timestamp file: {filename}"
                else:
                    # Create a simple timestamp file
                    timestamp = datetime.now().isoformat()
                    filename = f"updates/update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    await self.create_file(filename, f"Automated update at {timestamp}")
                    changes_summary = f"Added timestamp file: {filename}"
                
                # Generate commit message
                commit_message = await self.generate_commit_message(changes_summary)
                
                # Commit and push
                success, result_message = await self.commit_and_push(commit_message)
                
                if success:
                    return True, commit_message
                else:
                    return False, result_message
                
        except Exception as e:
            logger.error(f"Commit cycle failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, str(e)
    
    async def health_check(self) -> dict:
        """Extended health check for GitHub agent"""
        base_health = super().health_check()
        
        try:
            repo_status = {
                "repo_exists": self.repo_path.exists(),
                "git_repo_exists": (self.repo_path / ".git").exists() if self.repo_path.exists() else False,
                "repo_initialized": self.repo is not None,
                "is_empty_repo": self.is_empty_repo,
                "initial_commit_done": self.initial_commit_done,
                "has_remote": bool(self.repo.remotes) if self.repo else False
            }
            
            if self.repo and not self.is_empty_repo:
                try:
                    repo_status["branch"] = self.repo.active_branch.name
                    repo_status["commit_count"] = len(list(self.repo.iter_commits()))
                except:
                    pass
            
        except Exception as e:
            repo_status = {"error": str(e)}
        
        return {**base_health, **repo_status}