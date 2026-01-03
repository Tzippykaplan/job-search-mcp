from typing import Any

from job_mcp.services.rewrite_resume_for_job_service import RewriteResumeService


async def rewrite_resume_for_job_tool(
    job_requirements: dict,
    match_result: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
) -> dict[str, Any]:
    """Rewrite a resume to better match a job posting."""
    service = RewriteResumeService()
    return await service.rewrite_resume_for_job(
        job_requirements=job_requirements,
        match_result=match_result,
        resume_text=resume_text,
        resume_file_path=resume_file_path,
    )
