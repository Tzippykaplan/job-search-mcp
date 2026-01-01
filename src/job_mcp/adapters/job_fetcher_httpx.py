from __future__ import annotations

import logging
import re
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_title_from_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip() or None

    if soup.title and soup.title.string:
        return soup.title.string.strip() or None

    return None


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        t.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def focus_on_requirements(text: str) -> str:
    patterns = [r"\brequirements\b", r"\bmust\b", r"\bwhat you will bring\b"]
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
    async with httpx.AsyncClient(
        verify=False, follow_redirects=True, timeout=20
    ) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 403:
            logger.warning(f"Job page blocked by site: {url}")
            return None, ""
        r.raise_for_status()
        html = r.text
        title = extract_title_from_html(html)
        text = html_to_text(html)
        return title, text
