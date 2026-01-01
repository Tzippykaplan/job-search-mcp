from __future__ import annotations

import json
import logging
import os
from typing import Any
from google import genai

from job_mcp.config import GEMINI_MODEL, MAX_JOB_TEXT_LENGTH
from job_mcp.utils.gemini_helpers import strip_fences, robust_json_loads

logger = logging.getLogger(__name__)


class GeminiExtractor:
    def extract_job(self, job_text: str, title_hint: str | None = None) -> dict[str, Any]:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Missing GEMINI_API_KEY")

        client = genai.Client(api_key=key)
        job_text = job_text[:MAX_JOB_TEXT_LENGTH]

        prompt = f"""
Return ONLY JSON (no markdown, no ```).

If title_hint is provided, use it as the title unless the text clearly shows a different title.
title_hint: {title_hint}

Extract ONLY what is explicitly required in the job post.
Split into technical vs soft skills.

Schema:
{{
  "title": string|null,
  "company": string|null,
  "location": string|null,
  "years_experience": string[],
  "must_have_tech": string[],
  "nice_to_have_tech": string[],
  "soft_skills": string[],
  "notes": string[]
}}

Rules:
- must_have_tech: languages/frameworks/tools/DB/cloud that are REQUIRED/must have.
- nice_to_have_tech: tech that is preferred/nice to have/advantage.
- soft_skills: teamwork/communication/creative thinking/leadership etc.
- notes: short important constraints (hybrid, mobile, design systems, travel %, salary etc.).
- Keep items short. De-duplicate (don't list Python twice).
- Return empty array [] if no items found for a category.

Job text:
\"\"\"{job_text}\"\"\"
"""

        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = strip_fences((resp.text or "").strip())
        
        try:
            return robust_json_loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON. Raw response: {raw}")
            raise ValueError(
                f"Gemini returned invalid JSON. Could not extract job requirements. Error: {e}"
            ) from e
