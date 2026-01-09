"""Configuration constants for the Job Search MCP server."""

from pathlib import Path

# Gemini API Configuration
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_REQUEST_TIMEOUT = 60.0  # seconds
GEMINI_MAX_REQUESTS_PER_MINUTE = 60

# Token and Length Limits (to save API costs)
MAX_JOB_TEXT_LENGTH = 18000  # Maximum job posting text length in characters
MAX_RESUME_LENGTH = 16000  # Maximum resume text length in characters
MAX_FILENAME_LENGTH = 120  # Maximum output filename length

# Job Text Extraction Configuration
# Context window for requirements section extraction
REQUIREMENTS_CONTEXT_BEFORE = 300   # Characters before "requirements" keyword
REQUIREMENTS_CONTEXT_AFTER = 9000   # Characters after (captures full section)
REQUIREMENTS_INTRO_LENGTH = 1500    # Intro text when match is far from start
# Chosen to balance:
# - API token costs (shorter is cheaper)
# - Information completeness (longer captures more context)
# - LLM context window limits

# File and Directory Settings
DEFAULT_OUTPUT_DIR = "output_resumes"  # Directory for exported resume files
SUPPORTED_RESUME_FORMATS = [".txt", ".md", ".docx"]  # Supported resume file formats

# Project root directory (parent of this config file)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# System Prompt for MCP Agent
PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system_prompt.txt"
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")