from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from job_mcp.config import MAX_RESUME_LENGTH
from job_mcp.adapters.gemini_client import GeminiLLMClient
from job_mcp.utils.gemini_helpers import as_list, robust_json_loads
from job_mcp.utils.read_resume import read_resume_any
from job_mcp.exceptions import ValidationError, LLMResponseError, FileReadError

logger = logging.getLogger(__name__)
ReadResume = Callable[[str], str]


class RewriteResumeService:
    def __init__(
        self,
        llm: GeminiLLMClient | None = None,
        resume_reader: ReadResume = read_resume_any,
    ) -> None:
        self._llm = llm or GeminiLLMClient()
        self._resume_reader = resume_reader

    async def rewrite_resume_for_job(
        self,
        job_requirements: dict[str, Any],
        match_result: dict[str, Any],
        resume_text: str | None = None,
        resume_file_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info("Starting resume rewrite", extra={
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

        extracted = (job_requirements or {}).get("extracted", job_requirements)
        return await self._rewrite_resume_with_llm(extracted, match_result, resume_text)

    async def _rewrite_resume_with_llm(
        self,
        job_requirements: dict[str, Any],
        match_result: dict[str, Any],
        resume_text: str,
    ) -> dict[str, Any]:
        resume_text = self._compact_text(resume_text)
        if not resume_text:
            logger.error("Resume text is empty after compacting")
            raise ValidationError("resume_text is required and cannot be empty")

        logger.debug("Resume text compacted", extra={"final_length": len(resume_text)})

        job_requirements = (job_requirements or {}).get("extracted", job_requirements)

        filtered_job_requirements = {
            "title": job_requirements.get("title") or job_requirements.get("role_title"),
            "must_have_tech": job_requirements.get("must_have_tech", []),
            "nice_to_have_tech": job_requirements.get("nice_to_have_tech", []),
            "years_experience": job_requirements.get("years_experience"),
            "responsibilities": job_requirements.get("responsibilities", []),
            "notes": job_requirements.get("notes", []),
        }

        filtered_match_result = {
            "score": match_result.get("score") if isinstance(match_result, dict) else None,
            "matched_keywords": match_result.get("matched_keywords", []) if isinstance(match_result, dict) else [],
            "missing_keywords": match_result.get("missing_keywords", []) if isinstance(match_result, dict) else [],
            "strengths": match_result.get("strengths", []) if isinstance(match_result, dict) else [],
            "gaps": match_result.get("gaps", []) if isinstance(match_result, dict) else [],
        }

        truncated_resume_text = resume_text[:MAX_RESUME_LENGTH]
        prompt = self._build_rewrite_prompt(filtered_job_requirements, filtered_match_result, truncated_resume_text)
        
        logger.info("Calling Gemini API for resume rewrite", extra={"prompt_length": len(prompt)})
        llm_response = await self._llm.generate_text(prompt)
        logger.debug("Received LLM response", extra={"response_length": len(llm_response)})

        try:
            parsed_rewrite_result = robust_json_loads(llm_response)
            logger.info("Successfully parsed rewrite result", extra={
                "result_type": type(parsed_rewrite_result).__name__
            })
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", extra={
                "error": str(e),
                "response_preview": llm_response[:200]
            }, exc_info=True)
            raise LLMResponseError(
                f"Gemini returned invalid JSON. Could not rewrite resume. Error: {e}"
            ) from e

        if not isinstance(parsed_rewrite_result, dict):
            logger.error("LLM returned non-dict JSON", extra={"type": type(parsed_rewrite_result).__name__})
            raise LLMResponseError("Gemini returned JSON but not an object for rewrite_resume")

        return self._normalize_rewrite_result(parsed_rewrite_result)

    @staticmethod
    def _compact_text(s: str) -> str:
        s = (s or "").replace("\r\n", "\n")
        s = "\n".join(line.rstrip() for line in s.splitlines())
        s = re.sub(r"\n{3,}", "\n\n", s).strip()
        return s

    @staticmethod
    def _build_rewrite_prompt(
        filtered_job_requirements: dict[str, Any],
        filtered_match_result: dict[str, Any],
        truncated_resume_text: str,
    ) -> str:
        return f"""
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

job_requirements (filtered):
{json.dumps(filtered_job_requirements, ensure_ascii=False)}

match_result (filtered):
{json.dumps(filtered_match_result, ensure_ascii=False)}

resume_text:
\"\"\"{truncated_resume_text}\"\"\"

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
""".strip()

    @staticmethod
    def _normalize_rewrite_result(parsed_rewrite_result: dict[str, Any]) -> dict[str, Any]:
        sections = parsed_rewrite_result.get("sections") if isinstance(parsed_rewrite_result, dict) else None
        if not isinstance(sections, dict):
            sections = {}

        def get_section(name: str) -> str:
            v = sections.get(name, "")
            return v if isinstance(v, str) else ""

        normalized_sections = {
            "Summary": get_section("Summary"),
            "Skills": get_section("Skills"),
            "Experience": get_section("Experience"),
            "Projects": get_section("Projects"),
            "Education": get_section("Education"),
        }

        rewritten_resume = parsed_rewrite_result.get("rewritten_resume", "")
        if not isinstance(rewritten_resume, str) or not rewritten_resume.strip():
            resume_sections = []
            for key in ["Summary", "Skills", "Experience", "Projects", "Education"]:
                txt = normalized_sections[key].strip()
                if txt:
                    resume_sections.append(f"{key}\n{txt}".strip())
            rewritten_resume = "\n\n".join(resume_sections).strip()

        return {
            "sections": normalized_sections,
            "rewritten_resume": rewritten_resume,
            "changes": as_list(parsed_rewrite_result.get("changes")),
            "warnings": as_list(parsed_rewrite_result.get("warnings")),
        }
