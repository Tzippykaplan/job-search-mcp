"""Custom exceptions for Job Search MCP server."""


class JobSearchMCPError(Exception):
    """Base exception for all job search MCP errors."""
    pass


class ValidationError(JobSearchMCPError):
    """Input validation failed."""
    pass


class LLMResponseError(JobSearchMCPError):
    """LLM returned invalid or unparseable response."""
    pass


class ExternalServiceError(JobSearchMCPError):
    """External service (HTTP, API) failure."""
    pass


class FileReadError(JobSearchMCPError):
    """Failed to read file (resume, config, etc.)."""
    pass
