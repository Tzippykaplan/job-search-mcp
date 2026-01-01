from __future__ import annotations

import json
import logging
from typing import Any

from job_mcp.adapters.llm_gemini_client import GeminiLLMClient
from job_mcp.utils.gemini_helpers import as_list

logger = logging.getLogger(__name__)


class MatchResumeService:
    def __init__(self, llm: GeminiLLMClient | None = None) -> None:
        self._llm = llm or GeminiLLMClient()

    async def match(self, job_extracted: dict[str, Any], resume_text: str) -> dict[str, Any]:
        resume_text = (resume_text or "").strip()
        if not resume_text:
            raise ValueError("resume_text required")

        logger.info("Matching resume to job...")
        prompt = self._build_prompt(job_extracted, resume_text)

        raw = await self._llm.generate_text(prompt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            # keep error clear to caller
            raise ValueError(f"Gemini returned invalid JSON for match_resume. Error: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Gemini returned JSON but not an object for match_resume")

        return self._normalize(data)

    def _build_prompt(self, job_extracted: dict[str, Any], resume_text: str) -> str:
        job_json = json.dumps(job_extracted, ensure_ascii=False)
        resume_snippet = (resume_text or "")[:14000]

        return f"""Return ONLY valid JSON. No markdown. No code fences. No extra text.

Match resume against job requirements. Be strict.
Do NOT invent experience. Use ONLY what appears in resume.

job_extracted:
{job_json}

resume_text:
{resume_snippet}

Output JSON schema (ALL keys required):
{{
  "score": number,
  "matched_keywords": string[],
  "missing_keywords": string[],
  "strengths": string[],
  "gaps": string[]
}}

Rules:
- score must be between 0 and 100.
- Use [] when nothing found.
""".strip()

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        data.setdefault("matched_keywords", [])
        data.setdefault("missing_keywords", [])
        data.setdefault("strengths", [])
        data.setdefault("gaps", [])
        data.setdefault("score", 0)

        data["matched_keywords"] = as_list(data.get("matched_keywords"))
        data["missing_keywords"] = as_list(data.get("missing_keywords"))
        data["strengths"] = as_list(data.get("strengths"))
        data["gaps"] = as_list(data.get("gaps"))

        score = data.get("score")
        if not isinstance(score, (int, float)):
            score = 0
        data["score"] = max(0, min(100, int(score)))

        logger.info("Match score: %s/100", data["score"])
        return data
