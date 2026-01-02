from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from google import genai

from job_mcp.config import GEMINI_MODEL
from job_mcp.utils.gemini_helpers import strip_fences

logger = logging.getLogger(__name__)

# Error messages
MISSING_API_KEY_ERROR = "Missing GEMINI_API_KEY"


class GeminiLLMClient:
    """
    Gemini AI adapter for LLM text generation.
    
    Provides async interface to Google's Gemini API with automatic:
    - API key management from environment
    - Markdown code fence stripping from responses
    - Thread-safe async wrapping of sync API calls
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
        
        Raises:
            RuntimeError: If API key is not provided and not in environment.
        """
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise RuntimeError(MISSING_API_KEY_ERROR)
        self._client = genai.Client(api_key=self._api_key)

    async def generate_text(self, prompt: str, model: str = GEMINI_MODEL) -> str:
        """
        Generate text completion from a prompt using Gemini.
        
        Args:
            prompt: The input prompt text.
            model: Gemini model name (default from config).
        
        Returns:
            Generated text with markdown code fences removed.
        """
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=model,
            contents=prompt,
        )
        text = (getattr(response, "text", "") or "").strip()
        return strip_fences(text)
