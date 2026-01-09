from __future__ import annotations

import json
import logging
from typing import Any, Callable

from job_mcp.adapters.gemini_client import GeminiLLMClient
from job_mcp.utils.gemini_helpers import as_list, parse_llm_json_response
from job_mcp.utils.read_resume import read_resume_any
from job_mcp.exceptions import ValidationError, LLMResponseError, FileReadError

logger = logging.getLogger(__name__)


class MatchResumeService:
    def __init__(
        self,
        llm: GeminiLLMClient | None = None,
        resume_reader: Callable[[str], str] = read_resume_any,
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

        parsed_match_result = parse_llm_json_response(
            llm_response, "resume matching", logger
        )

        # Check if result is a wrapped array (from robust_json_loads)
        if "data" in parsed_match_result and len(parsed_match_result) == 1:
            logger.error("LLM returned array instead of object")
            raise LLMResponseError("Gemini returned JSON but not an object for match_resume")

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
        from job_mcp.config import MAX_RESUME_LENGTH

        job_requirements_json = json.dumps(job_requirements, ensure_ascii=False)
        truncated_resume_text = (resume_text or "")[:MAX_RESUME_LENGTH]

        return f"""You are an ATS (Applicant Tracking System) resume matcher. Your task is to objectively match a candidate's resume against job requirements.

OUTPUT FORMAT:
- Return ONLY valid JSON
- No markdown, no code fences (no ```), no explanatory text
- Raw JSON object only

MATCHING PRINCIPLES:
1. Be STRICT and OBJECTIVE - only count skills/experience explicitly present in the resume
2. Do NOT infer, assume, or extrapolate experience not stated
3. Do NOT give credit for similar or related skills unless they match the requirement
4. Evaluate based on concrete evidence in the resume

SCORING CRITERIA (0-100):
- 90-100: Exceptional fit - meets all must-have requirements plus most nice-to-haves
- 75-89: Strong fit - meets all must-have requirements and some nice-to-haves
- 60-74: Good fit - meets most must-have requirements
- 40-59: Moderate fit - meets some must-have requirements, has gaps
- 20-39: Weak fit - meets few requirements, significant gaps
- 0-19: Poor fit - missing most critical requirements

JOB REQUIREMENTS:
{job_requirements_json}

CANDIDATE RESUME:
{truncated_resume_text}

OUTPUT SCHEMA (ALL fields required):
{{
  "score": number,
  "matched_keywords": string[],
  "missing_keywords": string[],
  "strengths": string[],
  "gaps": string[]
}}

FIELD DEFINITIONS:
- score: Integer 0-100 based on criteria above
- matched_keywords: Technical skills/technologies from job requirements found in resume (e.g., ["React", "Python", "AWS"])
- missing_keywords: Technical skills/technologies from job requirements NOT found in resume (e.g., ["Kubernetes", "GraphQL"])
- strengths: Specific positive points where candidate exceeds or meets requirements (e.g., ["8 years React experience (exceeds 5yr requirement)", "Led team of 6 engineers"])
- gaps: Specific weaknesses or missing requirements (e.g., ["No GraphQL experience mentioned", "Limited cloud infrastructure background"])

MATCHING EXAMPLES:
- Job requires "React" + Resume mentions "React" → matched_keywords: ["React"]
- Job requires "5+ years experience" + Resume shows "7 years" → strengths: ["7 years experience (exceeds 5yr requirement)"]
- Job requires "Kubernetes" + Resume has no mention → missing_keywords: ["Kubernetes"], gaps: ["No Kubernetes experience"]
- Job requires "leadership" + Resume shows "Led team of 10" → strengths: ["Leadership: Led team of 10"]

IMPORTANT:
- Only match exact or clearly equivalent technologies (e.g., "JS" = "JavaScript", "k8s" = "Kubernetes")
- Do NOT match similar but different technologies (e.g., "Vue" ≠ "React", "PostgreSQL" ≠ "MySQL")
- Use empty arrays [] when no items found
- Be honest about gaps - this helps candidates improve

Return ONLY the JSON object.""".strip()

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
        # Clamp score to the expected contract even if the LLM drifts.
        parsed_match_result["score"] = max(0, min(100, int(score)))

        return parsed_match_result