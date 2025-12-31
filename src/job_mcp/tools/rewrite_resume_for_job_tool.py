"""Rewrite a resume to better match a job posting using Gemini."""

import json
import logging
import os
import re
from typing import Any

from google import genai

from job_mcp.config import GEMINI_MODEL, MAX_RESUME_LENGTH
from job_mcp.utils.gemini_helpers import as_list, robust_json_loads, strip_fences
from job_mcp.utils.read_resume import read_resume_any

logger = logging.getLogger(__name__)


def compact_text(s: str) -> str:
    """
    Compress text to reduce token usage without losing meaning.

    Normalizes line endings, collapses multiple newlines, and trims whitespace.

    Args:
        s: Text to compress.

    Returns:
        Compacted text.
    """
    s = (s or "").replace("\r\n", "\n")
    s = "\n".join(line.rstrip() for line in s.splitlines())
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


async def rewrite_resume_for_job_tool(
        job_extracted: dict,
        match_result: dict,
        resume_text: str | None = None,
        resume_file_path: str | None = None,
) -> dict[str, Any]:
    """
    Tool wrapper: Rewrite resume from text OR file path.

    Accepts either resume_text or resume_file_path, validates inputs,
    and delegates to the core rewriting logic.

    Args:
        job_extracted: Job requirements from extract_job_requirements_tool.
        match_result: Match evaluation from match_resume_to_job_tool.
        resume_text: Resume content as plain text.
        resume_file_path: Path to resume file (.docx, .txt, or .md).

    Returns:
        Dictionary with rewritten resume and analysis.

    Raises:
        RuntimeError: If file cannot be read.
        ValueError: If no resume content is provided.
    """
    # Load resume from file if path provided
    if resume_file_path:
        logger.info(f"Reading resume from file: {resume_file_path}")
        resume_text = read_resume_any(resume_file_path)

    # Validate resume content
    resume_text = (resume_text or "").strip()
    if not resume_text:
        raise ValueError("Provide either resume_text or resume_file_path")

    # Unwrap job_extracted if it has "extracted" key
    extracted = (job_extracted or {}).get("extracted", job_extracted)
    return rewrite_resume_for_job(extracted, match_result, resume_text)


def rewrite_resume_for_job(
        job_extracted: dict[str, Any],
        match_result: dict[str, Any],
        resume_text: str
) -> dict[str, Any]:
    """
    Core logic: Rewrite resume to match job requirements.

    Uses Gemini to rewrite the resume while keeping all content truthful,
    emphasizing relevant skills, and reorganizing for ATS compatibility.

    Args:
        job_extracted: Structured job requirements.
        match_result: Analysis of resume-to-job match.
        resume_text: Original resume content.

    Returns:
        Dictionary with:
        - sections: Rewritten sections (Summary, Skills, Experience, Projects, Education)
        - rewritten_resume: Full rewritten resume text
        - changes: List of improvements made
        - warnings: Important gaps that cannot be fixed

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set or API call fails.
        ValueError: If resume_text is empty.
    """
    # Validate API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable")

    # Validate and compact resume
    resume_text = compact_text(resume_text)
    if not resume_text:
        raise ValueError("resume_text is required and cannot be empty")

    logger.info("Starting resume rewrite...")

    # Unwrap job_extracted if caller passed the wrapper
    job_extracted = (job_extracted or {})
    job_extracted = job_extracted.get("extracted", job_extracted)

    # Extract only the parts that matter for rewriting (token efficiency)
    job_small = {
        "title": job_extracted.get("title") or job_extracted.get("role_title"),
        "must_have_tech": job_extracted.get("must_have_tech", []),
        "nice_to_have_tech": job_extracted.get("nice_to_have_tech", []),
        "years_experience": job_extracted.get("years_experience"),
        "responsibilities": job_extracted.get("responsibilities", []),
        "notes": job_extracted.get("notes", []),
    }

    match_small = {
        "score": match_result.get("score") if isinstance(match_result, dict) else None,
        "matched_keywords": match_result.get("matched_keywords", []) if isinstance(match_result, dict) else [],
        "missing_keywords": match_result.get("missing_keywords", []) if isinstance(match_result, dict) else [],
        "strengths": match_result.get("strengths", []) if isinstance(match_result, dict) else [],
        "gaps": match_result.get("gaps", []) if isinstance(match_result, dict) else [],
    }

    resume_payload = resume_text[:MAX_RESUME_LENGTH]

    # Create Gemini client
    client = genai.Client(api_key=api_key)

    # Construct rewriting prompt
    prompt = f"""
Return ONLY valid JSON (no markdown, no ```).

You are an ATS resume editor.

Goal:
Rewrite the resume to better match the job. Keep it truthful.

STRICT RULES:
- Do NOT add experience that is not explicitly present in resume_text.
- Do NOT add new technologies that do not appear in resume_text.
- Do NOT remove truthful information; if less relevant, keep it but move it lower or compress it.
- You MAY rephrase, reorder, and emphasize what already exists.
- Keep it concise and readable (~1 page style), bullet points, clear sections.

Use match_result to emphasize strengths and reduce gaps via phrasing (not by inventing).

job_extracted (filtered):
{json.dumps(job_small, ensure_ascii=False)}

match_result (filtered):
{json.dumps(match_small, ensure_ascii=False)}

resume_text:
\"\"\"{resume_payload}\"\"\"

Output JSON schema:
{{
  "sections": {{
    "Summary": string,
    "Skills": string,
    "Experience": string,
    "Projects": string,
    "Education": string
  }},
  "rewritten_resume": string,
  "changes": string[],
  "warnings": string[]
}}

Rules for output:
- Fill sections ONLY if relevant info exists; otherwise use "".
- "rewritten_resume" MUST be the full final resume text composed from the sections, in this order:
  Summary, Skills, Experience, Projects, Education
- changes: short bullets explaining improvements (e.g., "Moved Angular/RxJS to top skills")
- warnings: important gaps that cannot be fixed without new experience
"""

    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    raw = strip_fences(getattr(resp, "text", "") or "")

    try:
        data = robust_json_loads(raw)

        # Normalize sections
        sections = data.get("sections") if isinstance(data, dict) else None
        if not isinstance(sections, dict):
            sections = {}

        def sec(name: str) -> str:
            """Helper to extract and validate section content."""
            v = sections.get(name, "")
            return v if isinstance(v, str) else ""

        normalized_sections = {
            "Summary": sec("Summary"),
            "Skills": sec("Skills"),
            "Experience": sec("Experience"),
            "Projects": sec("Projects"),
            "Education": sec("Education"),
        }

        # Reconstruct resume if needed
        rewritten_resume = data.get("rewritten_resume", "")
        if not isinstance(rewritten_resume, str) or not rewritten_resume.strip():
            parts = []
            for k in ["Summary", "Skills", "Experience", "Projects", "Education"]:
                txt = normalized_sections[k].strip()
                if txt:
                    parts.append(f"{k}\n{txt}".strip())
            rewritten_resume = "\n\n".join(parts).strip()

        logger.info("Resume rewrite completed successfully")
        return {
            "sections": normalized_sections,
            "rewritten_resume": rewritten_resume,
            "changes": as_list(data.get("changes")),
            "warnings": as_list(data.get("warnings")),
        }

    except Exception as e:
        logger.error(f"Failed to parse rewrite response: {raw[:200]}")
        raise RuntimeError(f"Gemini returned non-JSON response: {raw[:400]}") from e
