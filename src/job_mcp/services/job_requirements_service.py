from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from job_mcp.adapters.job_fetcher_httpx import fetch_job_page, focus_on_requirements

from job_mcp.config import MAX_JOB_TEXT_LENGTH
from job_mcp.utils.gemini_helpers import robust_json_loads
from job_mcp.interfaces.llm_gemini_client import GeminiLLMClient
FetchJobPage = Callable[[str], Awaitable[tuple[str | None, str]]]


class JobRequirementsService:
    def __init__(
        self,
        llm: GeminiLLMClient | None = None,
        fetcher: FetchJobPage = fetch_job_page,
    ) -> None:
        self._llm = llm or GeminiLLMClient()
        self._fetcher = fetcher

    async def extract(
        self,
        job_url: str | None = None,
        job_text: str | None = None,
    ) -> dict[str, Any]:
        if not job_url and not job_text:
            raise ValueError("Provide either job_url or job_text")

        title_hint: str | None = None
        text: str | None = job_text

        if not text and job_url:
            title_hint, text = await self._fetcher(job_url)

        if not text:
            return {
                "source": "job_url" if job_url else "job_text",
                "job_url": job_url,
                "error": "blocked_by_site",
                "message": "Site blocked scraping (403) or empty page. Paste the job content into job_text instead.",
            }

        text = text[:MAX_JOB_TEXT_LENGTH]
        focused = focus_on_requirements(text)

        prompt = self._build_extract_job_prompt(
            job_text=focused,
            title_hint=title_hint,
        )

        raw = await self._llm.generate_text(prompt)

        try:
            extracted = robust_json_loads(raw)
        except json.JSONDecodeError as e:
            # keep the error explicit to the caller
            raise ValueError(
                f"Gemini returned invalid JSON. Could not extract job requirements. Error: {e}"
            ) from e

        return {
            "source": "job_url" if job_url else "job_text",
            "job_url": job_url,
            "extracted": extracted,
        }

    def _build_extract_job_prompt(self, *, job_text: str, title_hint: str | None) -> str:
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
