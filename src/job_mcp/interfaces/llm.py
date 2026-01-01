from __future__ import annotations
from typing import Any, Protocol


class JobExtractor(Protocol):
    """Protocol for LLM-based job requirement extractors."""
    
    def extract_job(self, job_text: str, title_hint: str | None = None) -> dict[str, Any]:
        """
        Extract structured job requirements from text.
        
        Args:
            job_text: Raw job posting text.
            title_hint: Optional title hint to guide extraction.
        
        Returns:
            Dictionary with extracted job fields (title, company, location, skills, etc).
        """
