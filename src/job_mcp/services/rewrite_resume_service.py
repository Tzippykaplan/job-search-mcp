from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from job_mcp.config import MAX_RESUME_LENGTH
from job_mcp.interfaces.llm_gemini_client import GeminiLLMClient
from job_mcp.utils.gemini_helpers import as_list, robust_json_loads
from job_mcp.utils.read_resume import read_resume_any

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

    async def rewrite(
        self,
        job_extracted: dict[str, Any],
        match_result: dict[str, Any],
        resume_text: str | None = None,
        resume_file_path: str | None = None,
    ) -> dict[str, Any]:
        if resume_file_path:
            logger.info("Reading resume from file: %s", resume_file_path)
            resume_text = self._resume_reader(resume_file_path)

        resume_text = (resume_text or "").strip()
        if not resume_text:
            raise ValueError("Provide either resume_text or resume_file_path")

        extracted = (job_extracted or {}).get("extracted", job_extracted)
        return await self._rewrite(extracted, match_result, resume_text)

    async def _rewrite(
        self,
        job_extracted: dict[str, Any],
        match_result: dict[str, Any],
        resume_text: str,
    ) -> dict[str, Any]:
        resume_text = self._compact_text(resume_text)
        if not resume_text:
            raise ValueError("resume_text is required and cannot be empty")

        logger.info("Starting resume rewrite...")

        job_extracted = (job_extracted or {}).get("extracted", job_extracted)

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
        prompt = self._build_prompt(job_small, match_small, resume_payload)
        raw = await self._llm.generate_text(prompt)

        try:
            data = robust_json_loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Gemini returned invalid JSON. Could not rewrite resume. Error: {e}"
            ) from e

        if not isinstance(data, dict):
            raise ValueError("Gemini returned JSON but not an object for rewrite_resume")

        return self._normalize(data)

    @staticmethod
    def _compact_text(s: str) -> str:
        s = (s or "").replace("\r\n", "\n")
        s = "\n".join(line.rstrip() for line in s.splitlines())
        s = re.sub(r"\n{3,}", "\n\n", s).strip()
        return s

    @staticmethod
    def _build_prompt(
        job_small: dict[str, Any],
        match_small: dict[str, Any],
        resume_payload: str,
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
""".strip()

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
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
            for key in ["Summary", "Skills", "Experience", "Projects", "Education"]:
                txt = normalized_sections[key].strip()
                if txt:
                    parts.append(f"{key}\n{txt}".strip())
            rewritten_resume = "\n\n".join(parts).strip()

        logger.info("Resume rewrite completed successfully")
        return {
            "sections": normalized_sections,
            "rewritten_resume": rewritten_resume,
            "changes": as_list(data.get("changes")),
            "warnings": as_list(data.get("warnings")),
        }
