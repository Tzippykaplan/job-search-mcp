"""Configuration constants for the Job Search MCP server."""

from pathlib import Path

# Gemini API Configuration
GEMINI_MODEL = "gemini-2.5-flash"

# Token and Length Limits (to save API costs)
MAX_JOB_TEXT_LENGTH = 18000
MAX_RESUME_LENGTH = 16000
MAX_FILENAME_LENGTH = 120

# File and Directory Settings
DEFAULT_OUTPUT_DIR = "output_resumes"
SUPPORTED_RESUME_FORMATS = [".txt", ".md", ".docx"]

# System Prompt for MCP Agent
PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system_prompt.txt"
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else ""
