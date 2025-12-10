import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")
REPO_BASE_PATH = os.getenv("REPO_BASE_PATH", "./repos")

# LLM Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
NIM_API_KEY = os.getenv("NIM_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# LLM Models
DEFAULT_PROVIDER = "nvidia"
NIM_MODEL = os.getenv("NIM_MODEL", "microsoft/phi-4-mini-instruct")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# App Configuration
MAX_COMMITS_PER_DAY = int(os.getenv("MAX_COMMITS_PER_DAY", "30"))
MIN_COMMITS_PER_DAY = int(os.getenv("MIN_COMMITS_PER_DAY", "20"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "7000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# Scheduler Configuration
COMMIT_WINDOW_HOURS = 8
RANDOMIZE_COMMITS = True