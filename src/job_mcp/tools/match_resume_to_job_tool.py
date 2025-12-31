"""Match resume to job requirements."""

import json
import logging
import os
from typing import Any

from google import genai

from job_mcp.config import GEMINI_MODEL
from job_mcp.utils.gemini_helpers import as_list, strip_fences

logger = logging.getLogger(__name__)


async def match_resume_to_job(job_extracted: dict[str, Any], resume_text: str) -> dict[str, Any]:
    """Compare resume against job. Return match score and analysis."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    resume_text = (resume_text or "").strip()
    if not resume_text:
        raise ValueError("resume_text required")

    logger.info("Matching resume to job...")
    client = genai.Client(api_key=api_key)
    prompt = f"""Return ONLY valid JSON.

Match resume against job requirements. Be strict.
Do NOT invent experience. Use ONLY what appears in resume.

job_extracted:
{json.dumps(job_extracted, ensure_ascii=False)}

resume_text:
\"\"\"{resume_text[:14000]}\"\"\"

Output: {{"score": number (0-100), "matched_keywords": string[],
"missing_keywords": string[], "strengths": string[], "gaps": string[]}}
"""

    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    raw = strip_fences(resp.text)
    data = json.loads(raw)

    # Normalize output
    data["matched_keywords"] = as_list(data.get("matched_keywords"))
    data["missing_keywords"] = as_list(data.get("missing_keywords"))
    data["strengths"] = as_list(data.get("strengths"))
    data["gaps"] = as_list(data.get("gaps"))

    if not isinstance(data.get("score"), (int, float)):
        data["score"] = 0
    data["score"] = max(0, min(100, int(data["score"])))

    logger.info(f"Match score: {data['score']}/100")
    return data
