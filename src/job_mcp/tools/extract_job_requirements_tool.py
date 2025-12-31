"""Extract structured job requirements from URLs or text using Gemini."""

import json
import logging
import os
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from google import genai

from job_mcp.config import GEMINI_MODEL, MAX_JOB_TEXT_LENGTH
from job_mcp.utils.gemini_helpers import strip_fences

logger = logging.getLogger(__name__)


def extract_title_from_html(html: str) -> str | None:
    """
    Extract the job title from an HTML page.

    Tries to extract from og:title meta tag first, then falls back to <title> tag.

    Args:
        html: Raw HTML content of the page.

    Returns:
        Job title if found, None otherwise.
    """
    soup = BeautifulSoup(html, "html.parser")

    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip() or None

    if soup.title and soup.title.string:
        return soup.title.string.strip() or None

    return None


def html_to_text(html: str) -> str:
    """
    Extract plain text from HTML, removing scripts, styles, and nav elements.

    Args:
        html: Raw HTML content.

    Returns:
        Cleaned text with normalized whitespace.
    """
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        t.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def focus_on_requirements(text: str) -> str:
    """
    Extract the most relevant part of a job posting (requirements section).

    Looks for common section markers and extracts the surrounding context.
    If no markers found, returns the original text.

    Args:
        text: Full job posting text.

    Returns:
        Focused text containing requirements section or original text.
    """
    patterns = [r"\brequirements\b", r"\bmust\b", r"\bwhat you will bring\b", ]
    lower = text.lower()

    for p in patterns:
        m = re.search(p, lower, flags=re.IGNORECASE)
        if m:
            head = text[:1500]
            start = max(0, m.start() - 300)
            end = min(len(text), m.start() + 9000)
            return (head + "\n\n" + text[start:end]).strip()

    return text


async def fetch_job_page(url: str) -> tuple[str | None, str]:
    """
    Fetch and parse a job posting from a URL.

    Args:
        url: Job posting URL.

    Returns:
        Tuple of (title, text) from the page. Returns (None, "") if page is blocked.

    Raises:
        httpx.HTTPStatusError: For non-403 HTTP errors.
    """
    async with httpx.AsyncClient(verify=False,follow_redirects=True, timeout=20) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 403:
            logger.warning(f"Job page blocked by site: {url}")
            return None, ""
        r.raise_for_status()
        html = r.text
        title = extract_title_from_html(html)
        text = html_to_text(html)
        return title, text


def gemini_extract(job_text: str, title_hint: str | None = None) -> dict[str, Any]:
    """
    Extract structured job requirements using Gemini API.

    Args:
        job_text: Raw job posting text (will be truncated to MAX_JOB_TEXT_LENGTH).
        title_hint: Optional title hint to guide extraction.

    Returns:
        Dictionary with extracted fields: title, company, location, years_experience,
        must_have_tech, nice_to_have_tech, soft_skills, notes.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set.
    """
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable")

    client = genai.Client(api_key=key)
    job_text = job_text[:MAX_JOB_TEXT_LENGTH]

    prompt = f"""
Return ONLY JSON (no markdown, no ```).

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
- must_have_tech: languages/frameworks/tools/DB/cloud that are REQUIRED/must.
- nice_to_have_tech: tech that is preferred/advantage.
- soft_skills: teamwork/communication/creative thinking etc.
- notes: short important constraints (hybrid, mobile, design systems, etc.).
- Keep items short. De-duplicate.

Job text:
\"\"\"{job_text}\"\"\"
"""
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    raw = strip_fences((resp.text or "").strip())
    logger.info("Successfully extracted job requirements from Gemini")
    return json.loads(raw)


async def extract_job_requirements(
        job_url: str | None = None, job_text: str | None = None
) -> dict[str, Any]:
    """
    Extract job requirements from either a URL or raw text.

    This is the main tool function. It fetches job content, focuses on the
    requirements section, and uses Gemini to structure the information.

    Args:
        job_url: URL to a job posting page.
        job_text: Raw job posting text (plain text or HTML).

    Returns:
        Dictionary with keys:
        - source: "job_url" or "job_text"
        - job_url: The URL used (if applicable)
        - extracted: Structured job data (if successful)
        - error: Error code (if failed)
        - message: Error message (if failed)

    Raises:
        ValueError: If neither job_url nor job_text is provided.
    """
    if not job_url and not job_text:
        raise ValueError("Provide either job_url or job_text")

    title_hint = None
    text = job_text

    if not text and job_url:
        logger.info(f"Fetching job page from: {job_url}")
        title_hint, text = await fetch_job_page(job_url)

    # Handle blocked/empty pages BEFORE calling Gemini
    if not text:
        logger.warning("Job page is empty or blocked")
        return {
            "source": "job_url" if job_url else "job_text",
            "job_url": job_url,
            "error": "blocked_by_site",
            "message": "Site blocked scraping (403) or empty page. Paste the job content into job_text instead."
        }

    text = focus_on_requirements(text)
    extracted = gemini_extract(text, title_hint=title_hint)

    return {
        "source": "job_url" if job_url else "job_text",
        "job_url": job_url,
        "extracted": extracted
    }
