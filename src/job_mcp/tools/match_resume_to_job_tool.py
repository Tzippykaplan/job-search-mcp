from typing import Any

from job_mcp.services.match_resume_to_job_service import MatchResumeService

_service: MatchResumeService | None = None


def _get_service() -> MatchResumeService:
    """Get or create the MatchResumeService singleton."""
    global _service
    if _service is None:
        _service = MatchResumeService()
    return _service


async def match_resume_to_job(job_extracted: dict[str, Any], resume_text: str) -> dict[str, Any]:
    """Compare resume against job. Return match score and analysis."""
    service = _get_service()
    return await service.match_resume_to_job_requirements(job_extracted, resume_text)
