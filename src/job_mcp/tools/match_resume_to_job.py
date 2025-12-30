import os
import json
from typing import Dict, Any
from google import genai
GEMINI_MODEL = "gemini-2.5-flash"


def strip_fences(text: str) -> str:
    """If Gemini returns ```json ... ```, remove the fences so json.loads works."""
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def as_list(x):
    return [i for i in x if isinstance(i, str)] if isinstance(x, list) else []


def match_resume_to_job(job_extracted: Dict[str, Any], resume_text: str) -> Dict[str, Any]:
    # 1) API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    # 2) Validate inputs
    resume_text = (resume_text or "").strip()
    if not resume_text:
        raise ValueError("resume_text is required")

    # 3) Model client
    client = genai.Client(api_key=api_key)

    # 4) Prompt (strict + JSON only)
    prompt = f"""
Return ONLY valid JSON (no markdown, no ```).

You are an ATS-style evaluator matching a resume to a job.
Be strict but fair.

CRITICAL:
- Do NOT invent experience.
- Use ONLY what appears in resume_text.
- If unsure, do not claim it.
- If some fields are missing or empty in job_extracted, infer keywords only from what exists. Do not fail.


job_extracted (from Tool 1):
{json.dumps(job_extracted, ensure_ascii=False)}

resume_text:
\"\"\"{resume_text[:14000]}\"\"\"

Output JSON schema:
{{
  "score": number,  // 0-100, must-have tech is highest weight
  "matched_keywords": string[],
  "missing_keywords": string[],
  "strengths": string[],  // 3-7 bullets supported by resume_text
  "gaps": string[]        // 3-7 bullets missing/weak vs job_extracted
}}

Rules:
- matched_keywords/missing_keywords should be mainly based on must_have_tech and nice_to_have_tech
  (or similar fields) inside job_extracted.
- strengths/gaps must be short and concrete.
"""

    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    raw = strip_fences(resp.text)

    try:
        data = json.loads(raw)

        data["matched_keywords"] = as_list(data.get("matched_keywords"))
        data["missing_keywords"] = as_list(data.get("missing_keywords"))
        data["strengths"] = as_list(data.get("strengths"))
        data["gaps"] = as_list(data.get("gaps"))

        if not isinstance(data.get("score"), (int, float)):
            data["score"] = 0
        data["score"] = max(0, min(100, int(data["score"])))

        return data

    except json.JSONDecodeError:
        raise RuntimeError(f"Gemini returned non-JSON: {raw[:300]}")
