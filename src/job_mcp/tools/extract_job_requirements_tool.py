from typing import Any
from job_mcp.services.extract_job_requirements_service import JobRequirementsExtractionService


async def extract_job_requirements(
    job_url: str | None = None,
    job_text: str | None = None,
) -> dict[str, Any]:
    """Extract job requirements from a URL or text."""
    service = JobRequirementsExtractionService()
    return await service.extract_job_requirements(job_url=job_url, job_text=job_text)
