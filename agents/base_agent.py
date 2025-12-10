import logging
from abc import ABC, abstractmethod
from typing import Any, Optional
from llm.manager import LLMManager

from utils.logger import setup_logger
logger = setup_logger(__name__)

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, name: str, llm_manager: Optional[LLMManager] = None):
        self.name = name
        self.llm_manager = llm_manager or LLMManager()
        self.logger = logging.getLogger(f"agent.{name}")
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the agent"""
        try:
            self._setup()
            self.initialized = True
            self.logger.info(f"Agent '{self.name}' initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize agent '{self.name}': {e}")
            return False
    
    @abstractmethod
    def _setup(self):
        """Agent-specific setup"""
        pass
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute agent's main task"""
        pass
    
    def generate_with_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using LLM with fallback"""
        return self.llm_manager.generate(prompt, system_prompt)
    
    def health_check(self) -> dict:
        """Check agent health"""
        return {
            "name": self.name,
            "initialized": self.initialized,
            "llm_available": self.llm_manager is not None
        }