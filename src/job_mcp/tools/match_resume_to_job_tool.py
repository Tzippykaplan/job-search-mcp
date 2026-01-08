from typing import Any

from job_mcp.services.match_resume_to_job_service import MatchResumeService


async def match_resume_to_job(
    job_requirements: dict[str, Any],
    resume_text: str | None = None,
    resume_file_path: str | None = None,
) -> dict[str, Any]:
    """Compare a resume against job requirements.

    Inputs:
    - job_requirements: output of `extract_job_requirements` (or just its "extracted" payload)
    - resume_text: resume content as plain text (optional)
    - resume_file_path: path to a local resume file (optional)

    Returns:
    - {
        "score": int,                 # 0..100
        "matched_keywords": list[str],
        "missing_keywords": list[str],
        "strengths": list[str],
        "gaps": list[str]
      }
    """
    match_resume_service = MatchResumeService()
    return await match_resume_service.match_resume_to_job_requirements(
        job_requirements,
        resume_text=resume_text,
        resume_file_path=resume_file_path,
    )
