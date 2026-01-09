from __future__ import annotations

import asyncio
import logging
import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from job_mcp.config import (
    REQUIREMENTS_CONTEXT_BEFORE,
    REQUIREMENTS_CONTEXT_AFTER,
    REQUIREMENTS_INTRO_LENGTH,
)
from job_mcp.exceptions import ValidationError

logger = logging.getLogger(__name__)

REQUIREMENTS_PATTERNS = [r"\brequirements\b", r"\bmust\b", r"\bwhat you will bring\b"]


def validate_url(url: str) -> None:
    """
    Validate URL has valid format and scheme.

    Args:
        url: URL to validate.

    Raises:
        ValidationError: If URL format is invalid or uses unsupported scheme.
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {e}") from e

    # Require HTTP/HTTPS
    if parsed.scheme not in ["http", "https"]:
        raise ValidationError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")


def extract_title_from_html(html: str) -> str | None:
    """Extract job title from HTML, preferring Open Graph meta tag over title tag."""
    soup = BeautifulSoup(html, "html.parser")

    og_meta_tag = soup.find("meta", property="og:title")
    if og_meta_tag and og_meta_tag.get("content"):
        return og_meta_tag["content"].strip() or None

    if soup.title and soup.title.string:
        return soup.title.string.strip() or None

    return None


def parse_html_to_clean_text(html: str) -> str:
    """Parse HTML and extract clean text content, removing scripts, styles, and navigation elements."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_requirements_section(text: str) -> str:
    """
    Extract the requirements section from job posting text.
    
    Searches for requirements keywords and returns a focused slice of text
    around the match, optionally including an intro section if the match
    is far from the beginning.
    """
    lower = text.lower()

    for pattern in REQUIREMENTS_PATTERNS:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - REQUIREMENTS_CONTEXT_BEFORE)
            end = min(len(text), match.start() + REQUIREMENTS_CONTEXT_AFTER)
            # Only include head if the match is far from the beginning
            if start > REQUIREMENTS_INTRO_LENGTH:
                head = text[:REQUIREMENTS_INTRO_LENGTH]
                return (head + "\n\n" + text[start:end]).strip()
            else:
                return text[start:end].strip()

    return text


async def fetch_job_page(url: str, max_retries: int = 3) -> tuple[str | None, str]:
    """
    Fetch a job posting page from a URL with retry logic.

    Args:
        url: Job posting URL to fetch.
        max_retries: Maximum number of retry attempts for transient failures.

    Returns:
        Tuple of (title, clean_text) where title may be None if not found.
        Returns (None, "") if the page is blocked (403 status).

    Raises:
        ValidationError: If URL format is invalid.
        httpx.HTTPStatusError: For HTTP errors other than 403.
    """
    # Validate URL format before fetching
    validate_url(url)

    logger.info("Fetching job page", extra={"url": url, "max_retries": max_retries})

    last_exception = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(
                verify=True,
                follow_redirects=True,
                timeout=httpx.Timeout(connect=5.0, read=20.0, write=20.0, pool=20.0)
            ) as client:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})

                if response.status_code == 403:
                    logger.warning("Job page blocked by site (403)", extra={"url": url})
                    return None, ""

                response.raise_for_status()
                logger.debug("Job page fetched successfully", extra={
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(response.text),
                    "attempt": attempt + 1
                })

                html = response.text
                title = extract_title_from_html(html)
                text = parse_html_to_clean_text(html)

                logger.info("Job page parsed", extra={
                    "title": title,
                    "text_length": len(text)
                })

                return title, text

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Transient error fetching job page, retrying in {wait_time}s", extra={
                    "url": url,
                    "attempt": attempt + 1,
                    "error": str(e)
                })
                await asyncio.sleep(wait_time)
            else:
                logger.error("Max retries reached for job page fetch", extra={
                    "url": url,
                    "error": str(e)
                }, exc_info=True)
                raise

        except httpx.HTTPError as e:
            # Don't retry on HTTP errors (4xx/5xx or other failures)
            # HTTPStatusError is a subclass of HTTPError, so this catches both
            if isinstance(e, httpx.HTTPStatusError):
                logger.error("HTTP status error fetching job page", extra={
                    "url": url,
                    "status_code": e.response.status_code,
                    "error": str(e)
                }, exc_info=True)
            else:
                logger.error("HTTP error fetching job page", extra={
                    "url": url,
                    "error": str(e)
                }, exc_info=True)
            raise

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    return None, ""




