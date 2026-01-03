from __future__ import annotations

import logging
import re
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Constants for requirements extraction
REQUIREMENTS_CONTEXT_BEFORE = 300
REQUIREMENTS_CONTEXT_AFTER = 9000
REQUIREMENTS_INTRO_LENGTH = 1500
REQUIREMENTS_PATTERNS = [r"\brequirements\b", r"\bmust\b", r"\bwhat you will bring\b"]


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


async def fetch_job_page(url: str) -> tuple[str | None, str]:
    """
    Fetch a job posting page from a URL.
    
    Returns:
        Tuple of (title, clean_text) where title may be None if not found.
        Returns (None, "") if the page is blocked (403 status).
    
    Raises:
        httpx.HTTPStatusError: For HTTP errors other than 403.
    """
    logger.info("Fetching job page", extra={"url": url})
    
    async with httpx.AsyncClient(
        verify=True,
        follow_redirects=True,
        timeout=httpx.Timeout(connect=5.0, read=20.0, write=20.0, pool=20.0)
    ) as client:
        try:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            
            if response.status_code == 403:
                logger.warning("Job page blocked by site (403)", extra={"url": url})
                return None, ""
            
            response.raise_for_status()
            logger.debug("Job page fetched successfully", extra={
                "url": url,
                "status_code": response.status_code,
                "content_length": len(response.text)
            })
            
            html = response.text
            title = extract_title_from_html(html)
            text = parse_html_to_clean_text(html)
            
            logger.info("Job page parsed", extra={
                "title": title,
                "text_length": len(text)
            })
            
            return title, text
            
        except httpx.HTTPError as e:
            logger.error("HTTP error fetching job page", extra={
                "url": url,
                "error": str(e)
            }, exc_info=True)
            raise
