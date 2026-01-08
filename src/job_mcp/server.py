"""MCP server for job-resume matching."""
import logging
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import truststore

from job_mcp.config import SYSTEM_PROMPT
from job_mcp.utils.validation import require_str, require_dict, require_one_of
from job_mcp.exceptions import ValidationError
from job_mcp.utils.logger import setup_logging

truststore.inject_into_ssl()
load_dotenv()

# Setup logging before anything else
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

mcp = FastMCP("job-search-mcp")

from job_mcp.tools.export_resume_docx_tool import export_resume_docx_tool
from job_mcp.tools.extract_job_requirements_tool import extract_job_requirements
from job_mcp.tools.match_resume_to_job_tool import match_resume_to_job
from job_mcp.tools.rewrite_resume_for_job_tool import rewrite_resume_for_job_tool

logger = logging.getLogger(__name__)


@mcp.tool(
    name="extract_job_requirements",
    description="Extract structured job requirements from a job URL or pasted text. Input: job_url|job_text. Returns: {source, job_url, extracted} or {error, message} if scraping is blocked.",
)
async def tool_extract_job_requirements(job_url: str | None = None, job_text: str | None = None):
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
    logger.info("Tool called: extract_job_requirements", extra={"has_url": bool(job_url), "has_text": bool(job_text)})
    require_one_of(job_url=job_url, job_text=job_text)
    job_url = require_str("job_url", job_url, allow_none=True)
    job_text = require_str("job_text", job_text, allow_none=True)
    return await extract_job_requirements(job_url=job_url, job_text=job_text)

@mcp.tool(
    name="match_resume_to_job",
    description="Evaluate resume fit vs job requirements. Inputs: job_requirements + (resume_text|resume_file_path). Returns: {score, matched_keywords, missing_keywords, strengths, gaps}."
)
async def tool_match_resume_to_job(
    job_requirements: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
):
    """Compare a resume to job requirements.

    Inputs:
    - job_requirements: output of `extract_job_requirements` (or just its "extracted" dict)
    - resume_text|resume_file_path: resume source (provide at least one)

    Returns:
    - {
        "score": int,                 # 0..100
        "matched_keywords": list[str],
        "missing_keywords": list[str],
        "strengths": list[str],
        "gaps": list[str]
      }
    """
    logger.info("Tool called: match_resume_to_job", extra={"has_text": bool(resume_text), "has_file": bool(resume_file_path)})
    job_requirements = require_dict("job_requirements", job_requirements)
    
    require_one_of(resume_text=resume_text, resume_file_path=resume_file_path)
    resume_text = require_str("resume_text", resume_text, allow_none=True)
    resume_file_path = require_str("resume_file_path", resume_file_path, allow_none=True)

    # Accept either the raw extracted dict or a wrapper payload that contains it.
    requirements = job_requirements.get("extracted", job_requirements)
    return await match_resume_to_job(requirements, resume_text, resume_file_path)


@mcp.tool(
    name="rewrite_resume_for_job",
    description="Rewrite a resume for a specific job while staying truthful. Inputs: job_requirements + match_result + resume. Returns: {sections, rewritten_resume, changes, warnings}."
)
async def tool_rewrite_resume_for_job(
    job_requirements: dict,
    match_result: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
):
    """Rewrite a resume to better align with a target job (without inventing facts).

    Inputs:
    - job_requirements: output of `extract_job_requirements` (or just its "extracted" dict)
    - match_result: output of `match_resume_to_job`
    - resume_text|resume_file_path: resume source (provide at least one)

    Returns:
    - {
        "sections": {"Summary": str, "Skills": str, "Experience": str, "Projects": str, "Education": str},
        "rewritten_resume": str,
        "changes": list[str],
        "warnings": list[str]
      }
    """
    logger.info("Tool called: rewrite_resume_for_job", extra={"has_text": bool(resume_text), "has_file": bool(resume_file_path)})
    job_requirements = require_dict("job_requirements", job_requirements)
    match_result = require_dict("match_result", match_result)

    require_one_of(resume_text=resume_text, resume_file_path=resume_file_path)
    resume_text = require_str("resume_text", resume_text, allow_none=True)
    resume_file_path = require_str("resume_file_path", resume_file_path, allow_none=True)

    return await rewrite_resume_for_job_tool(
        job_requirements,
        match_result,
        resume_text,
        resume_file_path,
    )


@mcp.tool(
    name="export_resume_docx",
    description="Export resume text to a DOCX file. Inputs: rewritten_resume + output options. Returns: {saved_path, output_dir, add_timestamp}."
)
async def tool_export_resume_docx(
    rewritten_resume: str,
    output_dir: str = "output_resumes",
    file_name: str | None = None,
    add_timestamp: bool = True,
):
    """Export resume content to a local .docx file.

    Inputs:
    - rewritten_resume: final resume text to write into the DOCX
    - output_dir: directory to save into (default: output_resumes)
    - file_name: base name without extension (optional)
    - add_timestamp: avoid overwriting by appending a timestamp

    Returns:
    - {"saved_path": str, "output_dir": str, "add_timestamp": bool}
    """
    logger.info("Tool called: export_resume_docx", extra={"output_dir": output_dir, "add_timestamp": add_timestamp})
    rewritten_resume = require_str("rewritten_resume", rewritten_resume)
    output_dir = require_str("output_dir", output_dir)
    file_name = require_str("file_name", file_name, allow_none=True)

    if not isinstance(add_timestamp, bool):
        # Guard against clients sending "true"/"false" strings instead of JSON booleans.
        raise ValidationError("add_timestamp must be a boolean")

    return await export_resume_docx_tool(rewritten_resume, output_dir, file_name, add_timestamp)


@mcp.prompt(
    name="job_search_assistant",
    description="End-to-end job application assistant that proactively analyzes jobs and adapts resumes."
)
def job_search_assistant_prompt() -> str:
    return SYSTEM_PROMPT


if __name__ == "__main__":
    logger.info("Starting Job Search MCP server...")
    mcp.run()
