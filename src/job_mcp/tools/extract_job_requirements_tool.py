from typing import Any
from job_mcp.services.job_requirements_service import JobRequirementsService

# Singleton service instance
_service: JobRequirementsService | None = None


def _get_service() -> JobRequirementsService:
    """Get or create the JobRequirementsService singleton."""
    global _service
    if _service is None:
        _service = JobRequirementsService()
    return _service


async def extract_job_requirements(
    job_url: str | None = None,
    job_text: str | None = None,
) -> dict[str, Any]:
    """Extract job requirements from a URL or text."""
    service = _get_service()
    return await service.extract(job_url=job_url, job_text=job_text)
