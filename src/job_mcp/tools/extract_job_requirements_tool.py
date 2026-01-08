from typing import Any
from job_mcp.services.extract_job_requirements_service import JobRequirementsExtractionService


async def extract_job_requirements(
    job_url: str | None = None,
    job_text: str | None = None,
) -> dict[str, Any]:
    """Extract structured requirements from a job post (URL or pasted text).

        Inputs (provide at least one):
        - job_url: URL to a job posting page
        - job_text: raw job description text

        Returns (success):
        - {
                "source": "job_url"|"job_text",
                "job_url": str|None,
                "extracted": {
                    "title": str|None,
                    "company": str|None,
                    "location": str|None,
                    "years_experience": list[str],
                    "must_have_tech": list[str],
                    "nice_to_have_tech": list[str],
                    "soft_skills": list[str],
                    "notes": list[str]
                }
            }

        Returns (scrape blocked / empty page):
        - {"source": ..., "job_url": ..., "error": "blocked_by_site", "message": str}
        """
    job_requirements_extraction_service = JobRequirementsExtractionService()
    return await job_requirements_extraction_service.extract_job_requirements(job_url=job_url, job_text=job_text)
