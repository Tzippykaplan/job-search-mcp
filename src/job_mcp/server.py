from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from job_mcp.tools.extract_job_requirements import extract_job_requirements
from job_mcp.tools.match_resume_to_job import match_resume_to_job
from job_mcp.tools.rewrite_resume_for_job import rewrite_resume_for_job_tool
from job_mcp.tools.export_resume_docx_tool import export_resume_docx_tool

mcp = FastMCP("job-search-mcp")

load_dotenv()


@mcp.tool(description="Extract structured job requirements from a job URL or a job description text.")
async def extract_job_requirements_tool(job_url: str | None = None, job_text: str | None = None):
    return await extract_job_requirements(job_url=job_url, job_text=job_text)


@mcp.tool(description="Evaluate how well a resume matches a specific job and identify strengths and gaps.")
async def match_resume_to_job_tool(job_extracted: dict, resume_text: str):
    extracted = job_extracted.get("extracted", job_extracted)
    return match_resume_to_job(extracted, resume_text)


@mcp.tool(description="Rewrite a resume to better match a job posting while keeping all content truthful.")
async def rewrite_resume_for_job(job_extracted: dict,match_result: dict,resume_text: str | None = None,resume_file_path: str | None = None,):
    return await rewrite_resume_for_job_tool(job_extracted, match_result, resume_text, resume_file_path)


@mcp.tool(description='Export rewritten resume text to a DOCX file.')
async def export_resume_docx(rewritten_resume: str,output_dir: str = "output_resumes", file_name: str | None = None, add_timestamp: bool = True,):
    return await export_resume_docx_tool(rewritten_resume, output_dir,file_name, add_timestamp)

if __name__ == "__main__":
    mcp.run()
