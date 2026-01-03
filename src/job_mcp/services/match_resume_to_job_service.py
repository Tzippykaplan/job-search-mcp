from __future__ import annotations

import json
import logging
from typing import Any, Callable

from job_mcp.adapters.gemini_client import GeminiLLMClient
from job_mcp.utils.gemini_helpers import as_list
from job_mcp.utils.read_resume import read_resume_any
from job_mcp.exceptions import ValidationError, LLMResponseError, FileReadError

logger = logging.getLogger(__name__)
ReadResume = Callable[[str], str]


class MatchResumeService:
    def __init__(
        self,
        llm: GeminiLLMClient | None = None,
        resume_reader: ReadResume = read_resume_any,
    ) -> None:
        self._llm = llm or GeminiLLMClient()
        self._resume_reader = resume_reader

    async def match_resume_to_job_requirements(
        self,
        job_requirements: dict[str, Any],
        resume_text: str | None = None,
        resume_file_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info("Starting resume-to-job matching", extra={
            "source": "file" if resume_file_path else "text"
        })
        
        if resume_file_path:
            logger.info("Reading resume from file", extra={"path": resume_file_path})
            resume_text = self._resume_reader(resume_file_path)
            logger.debug("Resume loaded from file", extra={"length": len(resume_text)})

        resume_text = (resume_text or "").strip()
        if not resume_text:
            logger.error("Validation failed: no resume text provided")
            raise ValidationError("Provide either resume_text or resume_file_path")

        prompt = self._build_matching_prompt(job_requirements, resume_text)
        
        logger.info("Calling Gemini API for resume matching", extra={"prompt_length": len(prompt)})
        llm_response = await self._llm.generate_text(prompt)
        logger.debug("Received LLM response", extra={"response_length": len(llm_response)})

        try:
            parsed_match_result = json.loads(llm_response)
            logger.info("Successfully parsed match result")
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", extra={
                "error": str(e),
                "response_preview": llm_response[:200]
            }, exc_info=True)
            raise LLMResponseError(f"Gemini returned invalid JSON for match_resume. Error: {e}") from e

        if not isinstance(parsed_match_result, dict):
            logger.error("LLM returned non-dict JSON", extra={"type": type(parsed_match_result).__name__})
            raise LLMResponseError("Gemini returned JSON but not an object for match_resume")

        result = self._normalize_match_result(parsed_match_result)
        logger.info("Resume matching completed", extra={
            "overall_score": result.get("overall_score"),
            "fit_level": result.get("fit_level")
        })
        return result

    def _build_matching_prompt(self, job_requirements: dict[str, Any], resume_text: str) -> str:
        job_requirements_json = json.dumps(job_requirements, ensure_ascii=False)
        truncated_resume_text = (resume_text or "")[:14000]

        return f"""Return ONLY valid JSON. No markdown. No code fences. No extra text.

Match resume against job requirements. Be strict.
Do NOT invent experience. Use ONLY what appears in resume.

job_requirements:
{job_requirements_json}

resume_text:
{truncated_resume_text}

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

    def _normalize_match_result(self, parsed_match_result: dict[str, Any]) -> dict[str, Any]:
        parsed_match_result.setdefault("matched_keywords", [])
        parsed_match_result.setdefault("missing_keywords", [])
        parsed_match_result.setdefault("strengths", [])
        parsed_match_result.setdefault("gaps", [])
        parsed_match_result.setdefault("score", 0)

        parsed_match_result["matched_keywords"] = as_list(parsed_match_result.get("matched_keywords"))
        parsed_match_result["missing_keywords"] = as_list(parsed_match_result.get("missing_keywords"))
        parsed_match_result["strengths"] = as_list(parsed_match_result.get("strengths"))
        parsed_match_result["gaps"] = as_list(parsed_match_result.get("gaps"))

        score = parsed_match_result.get("score")
        if not isinstance(score, (int, float)):
            score = 0
        parsed_match_result["score"] = max(0, min(100, int(score)))

        return parsed_match_result
