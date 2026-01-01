from __future__ import annotations

from typing import Any, Awaitable, Callable

from job_mcp.adapters.job_fetcher_httpx import fetch_job_page, focus_on_requirements
from job_mcp.adapters.llm_gemini import GeminiExtractor
from job_mcp.interfaces.llm import JobExtractor


FetchJobPage = Callable[[str], Awaitable[tuple[str | None, str]]]


class JobRequirementsService:
    def __init__(
        self,
        llm: JobExtractor | None = None,
        fetcher: FetchJobPage = fetch_job_page,
    ) -> None:
        self._llm: JobExtractor = llm or GeminiExtractor()
        self._fetcher: FetchJobPage = fetcher

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

        focused = focus_on_requirements(text)
        extracted = self._llm.extract_job(focused, title_hint=title_hint)

        return {
            "source": "job_url" if job_url else "job_text",
            "job_url": job_url,
            "extracted": extracted,
        }
