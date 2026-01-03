from typing import Any

from job_mcp.services.match_resume_to_job_service import MatchResumeService


async def match_resume_to_job(job_requirements: dict[str, Any], resume_text: str) -> dict[str, Any]:
    """Compare resume against job. Return match score and analysis."""
    service = MatchResumeService()
    return await service.match_resume_to_job_requirements(job_requirements, resume_text)
