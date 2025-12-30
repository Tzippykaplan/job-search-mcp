import os
import json
import re
from typing import Dict, Any, Optional
from google import genai
from job_mcp.utils.read_resume import read_resume_any

GEMINI_MODEL = "gemini-2.5-flash"


def strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def as_list(x) -> list[str]:
    return [i for i in x if isinstance(i, str)] if isinstance(x, list) else []


def compact_text(s: str) -> str:
    """
    Shrink token waste without deleting meaning:
    - normalize line endings
    - collapse 3+ newlines into 2
    - trim trailing spaces
    """
    s = (s or "").replace("\r\n", "\n")
    s = "\n".join(line.rstrip() for line in s.splitlines())
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def robust_json_loads(raw: str) -> Dict[str, Any]:
    """
    Try hard to parse JSON:
    1) direct json.loads
    2) extract the largest {...} block and parse
    """
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start : end + 1]
            return json.loads(candidate)
        raise


async def rewrite_resume_for_job_tool(
    job_extracted: dict,
    match_result: dict,
    resume_text: Optional[str] = None,
    resume_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool wrapper:
    - Accepts resume_text OR resume_file_path
    - Unwraps Tool-1 envelope { extracted: {...} }
    - Delegates to rewrite_resume_for_job (business logic)
    """
    if resume_file_path:
        if read_resume_any is None:
            raise RuntimeError(
                "resume_file_path provided but read_resume_any is not available. "
                "Create job_mcp/utils/read_resume.py and export read_resume_any(), "
                "or pass resume_text instead."
            )
        resume_text = read_resume_any(resume_file_path)

    resume_text = (resume_text or "").strip()
    if not resume_text:
        raise ValueError("Provide either resume_text or resume_file_path")

    extracted = (job_extracted or {}).get("extracted", job_extracted)
    return rewrite_resume_for_job(extracted, match_result, resume_text)


def rewrite_resume_for_job(
    job_extracted: Dict[str, Any],
    match_result: Dict[str, Any],
    resume_text: str
) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    resume_text = compact_text(resume_text)
    if not resume_text:
        raise ValueError("resume_text is required")

    # Unwrap Tool-1 envelope if caller passed it directly
    job_extracted = (job_extracted or {})
    job_extracted = job_extracted.get("extracted", job_extracted)

    # Token-saving: send only the parts of the job/match that matter for rewriting
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

    MAX_CHARS = 16000
    resume_payload = resume_text[:MAX_CHARS]

    client = genai.Client(api_key=api_key)

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

        sections = data.get("sections") if isinstance(data, dict) else None
        if not isinstance(sections, dict):
            sections = {}

        def sec(name: str) -> str:
            v = sections.get(name, "")
            return v if isinstance(v, str) else ""

        normalized_sections = {
            "Summary": sec("Summary"),
            "Skills": sec("Skills"),
            "Experience": sec("Experience"),
            "Projects": sec("Projects"),
            "Education": sec("Education"),
        }

        rewritten_resume = data.get("rewritten_resume", "")
        if not isinstance(rewritten_resume, str) or not rewritten_resume.strip():
            parts = []
            for k in ["Summary", "Skills", "Experience", "Projects", "Education"]:
                txt = normalized_sections[k].strip()
                if txt:
                    parts.append(f"{k}\n{txt}".strip())
            rewritten_resume = "\n\n".join(parts).strip()

        return {
            "sections": normalized_sections,
            "rewritten_resume": rewritten_resume,
            "changes": as_list(data.get("changes")),
            "warnings": as_list(data.get("warnings")),
        }

    except Exception:
        raise RuntimeError(f"Gemini returned non-JSON: {raw[:400]}")
