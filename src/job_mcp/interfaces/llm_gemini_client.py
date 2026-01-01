from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from google import genai

from job_mcp.config import GEMINI_MODEL
from job_mcp.utils.gemini_helpers import strip_fences

logger = logging.getLogger(__name__)


class GeminiLLMClient:
    """
    Low-level Gemini adapter:
    - reads GEMINI_API_KEY
    - calls Gemini
    - returns cleaned text (no code fences)
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")
        self._client = genai.Client(api_key=self._api_key)

    async def generate_text(self, prompt: str, *, model: str = GEMINI_MODEL) -> str:
        """
        Async-friendly wrapper (Gemini call is sync -> run in thread).
        """
        resp = await asyncio.to_thread(
            self._client.models.generate_content,
            model=model,
            contents=prompt,
        )
        text = (getattr(resp, "text", "") or "").strip()
        return strip_fences(text)
