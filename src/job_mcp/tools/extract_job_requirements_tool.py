from typing import Any
from job_mcp.services.extract_job_requirements_service import JobRequirementsExtractionService

# Singleton service instance
_service: JobRequirementsExtractionService | None = None


def _get_service() -> JobRequirementsExtractionService:
    """Get or create the JobRequirementsExtractionService singleton."""
    global _service
    if _service is None:
        _service = JobRequirementsExtractionService()
    return _service


async def extract_job_requirements(
    job_url: str | None = None,
    job_text: str | None = None,
) -> dict[str, Any]:
    """Extract job requirements from a URL or text."""
    service = _get_service()
    return await service.extract_job_requirements(job_url=job_url, job_text=job_text)
