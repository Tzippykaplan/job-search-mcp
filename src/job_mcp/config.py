"""Configuration constants for the Job Search MCP server."""

# Gemini API Configuration
GEMINI_MODEL = "gemini-2.5-flash"

# Token and Length Limits (to save API costs)
MAX_JOB_TEXT_LENGTH = 18000
MAX_RESUME_LENGTH = 16000
MAX_FILENAME_LENGTH = 120

# File and Directory Settings
DEFAULT_OUTPUT_DIR = "output_resumes"
SUPPORTED_RESUME_FORMATS = [".txt", ".md", ".docx"]
