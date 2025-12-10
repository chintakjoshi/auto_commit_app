import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with UTF-8 encoding for Windows compatibility"""
    logger = logging.getLogger(name)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler with UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with UTF-8
    file_handler = logging.FileHandler('github_agent.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    return logger