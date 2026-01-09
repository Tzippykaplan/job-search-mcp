from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from job_mcp.adapters.job_page_fetcher import fetch_job_page, extract_requirements_section

from job_mcp.config import MAX_JOB_TEXT_LENGTH
from job_mcp.utils.gemini_helpers import parse_llm_json_response
from job_mcp.adapters.gemini_client import GeminiLLMClient
from job_mcp.exceptions import ValidationError, LLMResponseError

logger = logging.getLogger(__name__)
JobPageFetcher = Callable[[str], Awaitable[tuple[str | None, str]]]

# Load prompt template once at module level
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "extract_job_requirements_prompt.txt"
EXTRACT_PROMPT_TEMPLATE = PROMPT_FILE.read_text(encoding="utf-8")


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

        parsed_requirements = parse_llm_json_response(
            llm_response, "job extraction", logger
        )

        return {
            "source": "job_url" if job_url else "job_text",
            "job_url": job_url,
            "extracted": parsed_requirements,
        }

    def _build_extraction_prompt(self, *, job_text: str, title_hint: str | None) -> str:
        title_hint_text = (
            f'Use "{title_hint}" as the title unless the job text explicitly contradicts it'
            if title_hint
            else 'Extract title from job text if available'
        )
        
        return EXTRACT_PROMPT_TEMPLATE.format(
            title_hint_text=title_hint_text,
            job_text=job_text
        )