"""MCP server for job-resume matching."""
import logging
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import truststore

from job_mcp.config import SYSTEM_PROMPT
from job_mcp.utils.validation import require_str, require_dict, require_one_of, require_bool
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
    description="""Extract structured job requirements from a job posting URL or raw text.
    
    Inputs (provide at least one):
    - job_url: URL to a job posting page (will be scraped)
    - job_text: Raw job description text (use if URL blocked)
    
    Returns (success):
    {
        "source": "job_url" or "job_text",
        "job_url": str or null,
        "extracted": {
            "title": str or null,
            "company": str or null,
            "location": str or null,
            "years_experience": list[str],
            "must_have_tech": list[str],
            "nice_to_have_tech": list[str],
            "soft_skills": list[str],
            "notes": list[str]
        }
    }
    
    Returns (scrape blocked):
    {"source": "job_url", "job_url": str, "error": "blocked_by_site", "message": str}
    
    Use this as the first step to analyze a job posting.""",
)
async def tool_extract_job_requirements(job_url: str | None = None, job_text: str | None = None):
    """Extract structured job requirements from URL or text."""
    logger.info("Tool called: extract_job_requirements", extra={"has_url": bool(job_url), "has_text": bool(job_text)})
    require_one_of(job_url=job_url, job_text=job_text)
    job_url = require_str("job_url", job_url, allow_none=True)
    job_text = require_str("job_text", job_text, allow_none=True)
    return await extract_job_requirements(job_url=job_url, job_text=job_text)

@mcp.tool(
    name="match_resume_to_job",
    description="""Evaluate how well a resume matches job requirements with detailed scoring and gap analysis.
    
    Inputs:
    - job_requirements: Output from extract_job_requirements (full object or just 'extracted' dict)
    - resume_text (optional): Resume content as plain text
    - resume_file_path (optional): Path to resume file (.txt, .md, .docx)
    (Provide either resume_text OR resume_file_path)
    
    Returns:
    {
        "score": int (0-100),
        "matched_keywords": list[str],    # Skills found in resume
        "missing_keywords": list[str],    # Skills NOT found in resume
        "strengths": list[str],           # Specific positive points
        "gaps": list[str]                 # Specific weaknesses
    }
    
    Scoring:
    - 90-100: Exceptional fit
    - 75-89: Strong fit
    - 60-74: Good fit
    - 40-59: Moderate fit with gaps
    - 0-39: Weak/poor fit
    
    Use this after extract_job_requirements to assess candidate fit.""",
)
async def tool_match_resume_to_job(
    job_requirements: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
):
    """Score resume fit against job requirements."""
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
    description="""Rewrite and optimize a resume for a specific job while maintaining complete truthfulness.
    
    IMPORTANT: Never invents experience, skills, or qualifications. Only reorganizes and rephrases existing content.
    
    Inputs:
    - job_requirements: Output from extract_job_requirements (full object or just 'extracted' dict)
    - match_result: Output from match_resume_to_job
    - resume_text (optional): Resume content as plain text
    - resume_file_path (optional): Path to resume file (.txt, .md, .docx)
    (Provide either resume_text OR resume_file_path)
    
    Returns:
    {
        "sections": {
            "Summary": str,
            "Skills": str,
            "Experience": str,
            "Projects": str,
            "Education": str
        },
        "rewritten_resume": str,          # Complete formatted resume
        "changes": list[str],             # List of improvements made
        "warnings": list[str]             # Critical gaps that couldn't be addressed
    }
    
    Optimizations applied:
    - Reorder sections/bullets to emphasize relevant experience
    - Use job-specific keywords from requirements
    - Strengthen weak phrasing with action verbs
    - Quantify achievements where numbers exist
    - ATS-optimized formatting
    
    Use this after match_resume_to_job to generate the final tailored resume.""",
)
async def tool_rewrite_resume_for_job(
    job_requirements: dict,
    match_result: dict,
    resume_text: str | None = None,
    resume_file_path: str | None = None,
):
    """Optimize resume for specific job while staying truthful."""
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
    description="""Export resume text to a professional DOCX file compatible with ATS systems.
    
    Inputs:
    - rewritten_resume: Final resume text (typically from rewrite_resume_for_job)
    - output_dir (optional): Directory to save file (default: 'output_resumes')
    - file_name (optional): Base filename without extension (default: 'rewritten_resume')
    - add_timestamp (optional): Append timestamp to filename to avoid overwriting (default: true)
    
    Returns:
    {
        "saved_path": str,        # Absolute path to generated .docx file
        "output_dir": str,        # Directory where file was saved
        "add_timestamp": bool     # Whether timestamp was added
    }
    
    Output format:
    - Clean, ATS-friendly formatting
    - Standard professional layout
    - Compatible with all major ATS systems
    - Ready to submit
    
    Use this as the final step to save the optimized resume.""",
)
async def tool_export_resume_docx(
    rewritten_resume: str,
    output_dir: str = "output_resumes",
    file_name: str | None = None,
    add_timestamp: bool = True,
):
    """Export resume to ATS-compatible DOCX file."""
    logger.info("Tool called: export_resume_docx", extra={"output_dir": output_dir, "add_timestamp": add_timestamp})
    rewritten_resume = require_str("rewritten_resume", rewritten_resume)
    output_dir = require_str("output_dir", output_dir)
    file_name = require_str("file_name", file_name, allow_none=True)
    add_timestamp = require_bool("add_timestamp", add_timestamp)

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