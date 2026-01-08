from typing import Any

from job_mcp.services.rewrite_resume_for_job_service import RewriteResumeService


async def rewrite_resume_for_job_tool(
    job_requirements: dict,
    match_result: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
) -> dict[str, Any]:
    """Rewrite a resume to better match a specific job (truthful ATS-style edit).

        Inputs:
        - job_requirements: output of `extract_job_requirements` (or just its "extracted" payload)
        - match_result: output of `match_resume_to_job`
        - resume_text|resume_file_path: resume source (provide at least one)

        Returns:
        - {
                "sections": {
                    "Summary": str,
                    "Skills": str,
                    "Experience": str,
                    "Projects": str,
                    "Education": str
                },
                "rewritten_resume": str,      # full combined resume text (used by export)
                "changes": list[str],         # short bullets describing edits
                "warnings": list[str]         # gaps that can't be fixed without new experience
            }
        """
    rewrite_resume_service = RewriteResumeService()
    return await rewrite_resume_service.rewrite_resume_for_job(
        job_requirements=job_requirements,
        match_result=match_result,
        resume_text=resume_text,
        resume_file_path=resume_file_path,
    )
