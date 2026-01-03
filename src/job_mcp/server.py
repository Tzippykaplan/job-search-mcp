"""MCP server for job-resume matching."""
import logging

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import truststore

from job_mcp.config import SYSTEM_PROMPT
from job_mcp.utils.validation import require_str, require_dict, require_one_of
from job_mcp.exceptions import ValidationError

truststore.inject_into_ssl()
load_dotenv()

mcp = FastMCP("job-search-mcp")

from job_mcp.tools.export_resume_docx_tool import export_resume_docx_tool
from job_mcp.tools.extract_job_requirements_tool import extract_job_requirements
from job_mcp.tools.match_resume_to_job_tool import match_resume_to_job
from job_mcp.tools.rewrite_resume_for_job_tool import rewrite_resume_for_job_tool

logger = logging.getLogger(__name__)


@mcp.tool(
    name="extract_job_requirements",
    description="Extract structured job requirements from a job URL or job description text. Returns title, company, location, skills, years, and notes."
)
async def tool_extract_job_requirements(job_url: str | None = None, job_text: str | None = None):
    require_one_of(job_url=job_url, job_text=job_text)
    job_url = require_str("job_url", job_url, allow_none=True)
    job_text = require_str("job_text", job_text, allow_none=True)
    return await extract_job_requirements(job_url=job_url, job_text=job_text)

@mcp.tool(
    name="match_resume_to_job",
    description="Evaluate how well a resume matches a job. Returns match score (0-100) + strengths, gaps, missing keywords."
)
async def tool_match_resume_to_job(
    job_requirements: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
):
    job_requirements = require_dict("job_requirements", job_requirements)
    
    require_one_of(resume_text=resume_text, resume_file_path=resume_file_path)
    resume_text = require_str("resume_text", resume_text, allow_none=True)
    resume_file_path = require_str("resume_file_path", resume_file_path, allow_none=True)

    requirements = job_requirements.get("extracted", job_requirements)
    return await match_resume_to_job(requirements, resume_text, resume_file_path)


@mcp.tool(
    name="rewrite_resume_for_job",
    description="Rewrite a resume to better match a job posting while staying truthful. Improves ATS compatibility."
)
async def tool_rewrite_resume_for_job(
    job_requirements: dict,
    match_result: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
):
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
    description="Export a rewritten resume to a DOCX file. Returns the output path."
)
async def tool_export_resume_docx(
    rewritten_resume: str,
    output_dir: str = "output_resumes",
    file_name: str | None = None,
    add_timestamp: bool = True,
):
    rewritten_resume = require_str("rewritten_resume", rewritten_resume)
    output_dir = require_str("output_dir", output_dir)
    file_name = require_str("file_name", file_name, allow_none=True)

    if not isinstance(add_timestamp, bool):
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
