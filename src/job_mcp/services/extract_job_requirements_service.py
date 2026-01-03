from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from job_mcp.adapters.job_page_fetcher import fetch_job_page, extract_requirements_section

from job_mcp.config import MAX_JOB_TEXT_LENGTH
from job_mcp.utils.gemini_helpers import robust_json_loads
from job_mcp.adapters.gemini_client import GeminiLLMClient
from job_mcp.exceptions import ValidationError, LLMResponseError

logger = logging.getLogger(__name__)
JobPageFetcher = Callable[[str], Awaitable[tuple[str | None, str]]]


class JobRequirementsExtractionService:
    def __init__(
        self,
        llm: GeminiLLMClient | None = None,
        job_page_fetcher: JobPageFetcher = fetch_job_page,
    ) -> None:
        self._llm = llm or GeminiLLMClient()
        self._job_page_fetcher = job_page_fetcher

    async def extract_job_requirements(
        self,
        job_url: str | None = None,
        job_text: str | None = None,
    ) -> dict[str, Any]:
        logger.info("Starting job requirements extraction", extra={"source": "url" if job_url else "text"})
        
        if not job_url and not job_text:
            logger.error("Validation failed: neither job_url nor job_text provided")
            raise ValidationError("Provide either job_url or job_text")

        title_hint: str | None = None
        job_posting_text: str | None = job_text

        if not job_posting_text and job_url:
            logger.debug("Fetching job page from URL", extra={"url": job_url})
            title_hint, job_posting_text = await self._job_page_fetcher(job_url)

        if not job_posting_text:
            logger.warning("Failed to fetch job page content", extra={"url": job_url})
            return {
                "source": "job_url" if job_url else "job_text",
                "job_url": job_url,
                "error": "blocked_by_site",
                "message": "Site blocked scraping (403) or empty page. Paste the job content into job_text instead.",
            }

        job_posting_text = job_posting_text[:MAX_JOB_TEXT_LENGTH]
        requirements_section = extract_requirements_section(job_posting_text)
        logger.debug("Extracted requirements section", extra={"length": len(requirements_section)})

        prompt = self._build_extraction_prompt(
            job_text=requirements_section,
            title_hint=title_hint,
        )

        logger.info("Calling Gemini API for job extraction", extra={"prompt_length": len(prompt)})
        llm_response = await self._llm.generate_text(prompt)
        logger.debug("Received LLM response", extra={"response_length": len(llm_response)})

        try:
            parsed_requirements = robust_json_loads(llm_response)
            logger.info("Successfully extracted job requirements", extra={
                "fields": list(parsed_requirements.keys()) if isinstance(parsed_requirements, dict) else None
            })
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", extra={
                "error": str(e),
                "response_preview": llm_response[:200]
            }, exc_info=True)
            raise LLMResponseError(
                f"Gemini returned invalid JSON. Could not extract job requirements. Error: {e}"
            ) from e

        return {
            "source": "job_url" if job_url else "job_text",
            "job_url": job_url,
            "extracted": parsed_requirements,
        }

    def _build_extraction_prompt(self, *, job_text: str, title_hint: str | None) -> str:
        return f"""
Return ONLY JSON (no markdown, no ```). No extra text.

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
- Keep items short. De-duplicate.
- Return empty array [] if no items found for a category.

Job text:
\"\"\"{job_text}\"\"\"
""".strip()
