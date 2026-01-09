from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from job_mcp.adapters.job_page_fetcher import fetch_job_page, extract_requirements_section

from job_mcp.config import MAX_JOB_TEXT_LENGTH
from job_mcp.utils.gemini_helpers import parse_llm_json_response
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

        parsed_requirements = parse_llm_json_response(
            llm_response, "job extraction", logger
        )

        return {
            "source": "job_url" if job_url else "job_text",
            "job_url": job_url,
            "extracted": parsed_requirements,
        }

    def _build_extraction_prompt(self, *, job_text: str, title_hint: str | None) -> str:
        return f"""You are a job requirements extraction expert. Your task is to parse a job posting and extract structured information.

OUTPUT FORMAT:
- Return ONLY valid JSON
- No markdown formatting, no code fences (no ```), no explanatory text
- Raw JSON object only

TITLE HINT:
{f'Use "{title_hint}" as the title unless the job text explicitly contradicts it' if title_hint else 'Extract title from job text if available'}

EXTRACTION RULES:
1. Extract ONLY information explicitly stated in the job posting
2. Do NOT infer, assume, or add information not present in the text
3. Distinguish between required vs. preferred qualifications
4. Separate technical skills from soft skills
5. Keep all entries concise and deduplicated
6. Use empty arrays [] when no information is found for a category

OUTPUT SCHEMA:
{{
  "title": string | null,
  "company": string | null,
  "location": string | null,
  "years_experience": string[],
  "must_have_tech": string[],
  "nice_to_have_tech": string[],
  "soft_skills": string[],
  "notes": string[]
}}

FIELD DEFINITIONS:
- title: Job title (e.g., "Senior Frontend Engineer")
- company: Company name if mentioned
- location: Work location, remote status, or "Remote"
- years_experience: Required experience levels (e.g., ["5+ years JavaScript", "3+ years React"])
- must_have_tech: REQUIRED technical skills - languages, frameworks, tools, databases, cloud platforms, libraries. Look for words like: "required", "must have", "essential", "mandatory"
- nice_to_have_tech: PREFERRED technical skills. Look for words like: "nice to have", "preferred", "bonus", "plus", "advantage", "beneficial"
- soft_skills: Non-technical abilities (e.g., "teamwork", "communication", "problem-solving", "leadership")
- notes: Important constraints or details (e.g., "hybrid 3 days/week", "travel 20%", "on-call rotation", "salary $120k-150k", "early-stage startup")

EXAMPLES OF CLASSIFICATION:
- "Must have experience with React" → must_have_tech: ["React"]
- "Knowledge of Vue.js is a plus" → nice_to_have_tech: ["Vue.js"]
- "Strong communication skills" → soft_skills: ["communication"]
- "Remote with quarterly onsite meetings" → notes: ["remote with quarterly onsite meetings"]

JOB POSTING TEXT:
\"\"\"{job_text}\"\"\"

Remember: Return ONLY the JSON object, nothing else.""".strip()