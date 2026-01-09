from __future__ import annotations

import asyncio
import logging
import os
import time

from google import genai

from job_mcp.config import (
    GEMINI_MODEL,
    GEMINI_REQUEST_TIMEOUT,
    GEMINI_MAX_REQUESTS_PER_MINUTE,
)
from job_mcp.exceptions import LLMResponseError
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
    - Rate limiting to prevent quota exhaustion (shared across all instances)
    - Request timeouts to prevent hanging
    """

    # Class-level rate limiting (shared across all instances)
    _class_rate_limit_lock: asyncio.Lock | None = None
    _class_request_timestamps: list[float] = []
    _class_max_requests_per_minute: int = GEMINI_MAX_REQUESTS_PER_MINUTE

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = GEMINI_REQUEST_TIMEOUT,
    ) -> None:
        """
        Initialize Gemini client with rate limiting.

        Rate limiting is shared across all instances to prevent quota exhaustion.

        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
            timeout: Default timeout for requests in seconds.

        Raises:
            RuntimeError: If API key is not provided and not in environment.
        """
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise RuntimeError(MISSING_API_KEY_ERROR)
        self._client = genai.Client(api_key=self._api_key)
        self._default_timeout = timeout

        # Initialize class-level lock on first instance creation
        if GeminiLLMClient._class_rate_limit_lock is None:
            GeminiLLMClient._class_rate_limit_lock = asyncio.Lock()

    async def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limit using sliding window algorithm.

        Tracks request timestamps and waits if rate limit would be exceeded.
        Rate limiting is shared across all instances of this class.
        """
        # Use class-level lock (initialized in __init__)
        assert self._class_rate_limit_lock is not None
        async with self._class_rate_limit_lock:
            now = time.time()
            window_start = now - 60.0  # 60 second window

            # Remove timestamps older than 60 seconds
            GeminiLLMClient._class_request_timestamps = [
                ts for ts in GeminiLLMClient._class_request_timestamps if ts > window_start
            ]

            # If we've hit the limit, wait until oldest request expires
            if len(GeminiLLMClient._class_request_timestamps) >= GeminiLLMClient._class_max_requests_per_minute:
                oldest_timestamp = GeminiLLMClient._class_request_timestamps[0]
                wait_time = 60.0 - (now - oldest_timestamp)

                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached, waiting {wait_time:.2f}s",
                        extra={"requests_in_window": len(GeminiLLMClient._class_request_timestamps)}
                    )
                    await asyncio.sleep(wait_time)

                    # Recalculate after waiting
                    now = time.time()
                    window_start = now - 60.0
                    GeminiLLMClient._class_request_timestamps = [
                        ts for ts in GeminiLLMClient._class_request_timestamps if ts > window_start
                    ]

            # Record this request
            GeminiLLMClient._class_request_timestamps.append(now)
            logger.debug("Rate limit check passed", extra={
                "requests_in_window": len(GeminiLLMClient._class_request_timestamps),
                "limit": GeminiLLMClient._class_max_requests_per_minute
            })

    async def generate_text(
        self,
        prompt: str,
        model: str = GEMINI_MODEL,
        timeout: float | None = None,
    ) -> str:
        """
        Generate text completion from a prompt using Gemini with rate limiting.

        Args:
            prompt: The input prompt text.
            model: Gemini model name (default from config).
            timeout: Request timeout in seconds (default from config).

        Returns:
            Generated text with markdown code fences removed.

        Raises:
            LLMResponseError: If request times out or API fails.
        """
        timeout = timeout or self._default_timeout

        # Apply rate limiting
        await self._enforce_rate_limit()

        logger.info("Calling Gemini API", extra={
            "model": model,
            "prompt_length": len(prompt),
            "timeout": timeout
        })

        try:
            # Wrap sync API call with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.models.generate_content,
                    model=model,
                    contents=prompt,
                ),
                timeout=timeout
            )

            text = (getattr(response, "text", "") or "").strip()
            cleaned = strip_fences(text)

            logger.info("Gemini API response received", extra={
                "response_length": len(cleaned),
                "had_fences": len(text) != len(cleaned)
            })

            return cleaned

        except asyncio.TimeoutError:
            logger.error(f"Gemini API timeout after {timeout}s")
            raise LLMResponseError(
                f"API request timed out after {timeout} seconds. Try again or increase timeout."
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise LLMResponseError(f"API request failed: {e}") 