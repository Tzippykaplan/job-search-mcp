import os, re, json
from typing import Optional, Dict, Any, Tuple

import httpx
from bs4 import BeautifulSoup
from google import genai

GEMINI_MODEL = "gemini-2.5-flash"


def extract_title_from_html(html: str) -> Optional[str]:
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
    """
    Keep the beginning (often contains title/company/location) + a relevant requirements chunk.
    If we don't find a requirements marker, return original text.
    """
    patterns = [r"\brequirements\b", r"\bmust\b", r"\bwhat you will bring\b", r"\bדרישות\b"]
    lower = text.lower()

    for p in patterns:
        m = re.search(p, lower, flags=re.IGNORECASE)
        if m:
            head = text[:1500]  # keep the first part for title/company/location
            start = max(0, m.start() - 300)
            end = min(len(text), m.start() + 9000)
            return (head + "\n\n" + text[start:end]).strip()

    return text


async def fetch_job_page(url: str) -> Tuple[Optional[str], str]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 403:
            return None, ""  # blocked
        r.raise_for_status()
        html = r.text
        title = extract_title_from_html(html)
        text = html_to_text(html)
        return title, text

def strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        lines = s.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def gemini_extract(job_text: str, title_hint: Optional[str] = None) -> Dict[str, Any]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    client = genai.Client(api_key=key)
    job_text = job_text[:18000]

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
    return json.loads(raw)


async def extract_job_requirements(job_url: Optional[str] = None, job_text: Optional[str] = None):
    if not job_url and not job_text:
        raise ValueError("Provide job_url or job_text")

    title_hint = None
    text = job_text

    if not text and job_url:
        title_hint, text = await fetch_job_page(job_url)

    # IMPORTANT: handle blocked/empty BEFORE calling Gemini
    if not text:
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
