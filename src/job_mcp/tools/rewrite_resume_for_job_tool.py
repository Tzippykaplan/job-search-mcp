from typing import Any

from job_mcp.services.rewrite_resume_for_job_service import RewriteResumeService

_service: RewriteResumeService | None = None


def _get_service() -> RewriteResumeService:
    """Get or create the RewriteResumeService singleton."""
    global _service
    if _service is None:
        _service = RewriteResumeService()
    return _service


async def rewrite_resume_for_job_tool(
    job_extracted: dict,
    match_result: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
) -> dict[str, Any]:
    """Rewrite a resume to better match a job posting."""
    service = _get_service()
    return await service.rewrite_resume_for_job(
        job_requirements=job_extracted,
        match_result=match_result,
        resume_text=resume_text,
        resume_file_path=resume_file_path,
    )
