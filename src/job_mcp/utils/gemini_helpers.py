"""Shared utilities for Gemini API interactions and JSON parsing."""

import json
from typing import Any


def strip_fences(text: str) -> str:
    """
    Remove markdown code fences from Gemini API responses.
    
    Handles the common pattern where Gemini returns ```json ... ``` format.
    
    Args:
        text: Response text that may contain code fences.
    
    Returns:
        Clean text with fences removed.
    """
    t = (text or "").strip()
    if t.startswith("```"):
        # Gemini frequently wraps JSON in markdown fences (```json ... ```).
        lines = t.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def as_list(value: Any) -> list[str]:
    """
    Safely convert a value to a list of strings, filtering non-string items.
    
    Args:
        value: Any value that should be converted to a string list.
    
    Returns:
        List of strings, empty list if value is not a list or is None.
    """
    return [i for i in value if isinstance(i, str)] if isinstance(value, list) else []


def robust_json_loads(raw: str) -> dict[str, Any]:
    """
    Parse JSON with fallback extraction of the {...} block.
    
    First attempts direct json.loads(). If that fails, extracts the largest
    {...} block and tries to parse that. Useful for partially malformed responses.
    
    Args:
        raw: Raw text containing JSON.
    
    Returns:
        Parsed dictionary.
    
    Raises:
        json.JSONDecodeError: If JSON cannot be extracted or parsed.
    """
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract the outermost {...} block when the model wraps JSON with prose.
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start : end + 1]
            return json.loads(candidate)
        raise
