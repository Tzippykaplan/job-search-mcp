import json
import logging
from typing import Any


def strip_fences(text: str) -> str:
    """
    Remove markdown code fences from Gemini API responses.

    Handles cases like:
      ```json
      {...}
      ```
    """
    t = (text or "").strip()
    if not t.startswith("```"):
        return t

    lines = t.splitlines()

    # Drop the opening fence line: ``` or ```json
    if lines:
        lines = lines[1:]

    # Drop the closing fence line (may have spaces)
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip()


def as_list(value: Any) -> list[str]:
    """
    Safely convert a value to a list of strings, filtering non-string items.
    """
    return [i for i in value if isinstance(i, str)] if isinstance(value, list) else []


def robust_json_loads(raw: str) -> dict[str, Any]:
    """
    Parse JSON with fallback extraction using a proper decoder.

    First attempts direct json.loads(). If that fails, uses
    json.JSONDecoder().raw_decode() to extract the first valid JSON object
    or array from the string.

    Notes:
      - If an array is found, it is wrapped as {"data": [...]}
        to keep the return type consistent (dict).
    """
    raw = (raw or "").strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()

        # Find the earliest start of a JSON object/array: { or [
        starts = [(raw.find("{"), "{"), (raw.find("["), "[")]
        starts = [(idx, ch) for idx, ch in starts if idx != -1]
        if not starts:
            raise json.JSONDecodeError(
                "No valid JSON object found in response. Response preview: " + raw[:200],
                raw,
                0,
            )

        start, _ = min(starts, key=lambda x: x[0])

        try:
            obj, _end_idx = decoder.raw_decode(raw, start)
        except json.JSONDecodeError:
            raise json.JSONDecodeError(
                "No valid JSON object found in response. Response preview: " + raw[:200],
                raw,
                0,
            )

    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return {"data": obj}

    # Valid JSON, but not an object/array (e.g., string/number/bool/null)
    return {"data": obj}


def parse_llm_json_response(
    llm_response: str,
    operation: str,
    logger: logging.Logger,
) -> dict[str, Any]:
    """
    Parse LLM JSON response with standardized error handling.
    
    Args:
        llm_response: Raw response text from LLM
        operation: Name of operation for logging (e.g., "extraction", "rewrite")
        logger: Logger instance to use for logging
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        LLMResponseError: If JSON parsing fails
    """
    from job_mcp.exceptions import LLMResponseError
    
    try:
        parsed = robust_json_loads(llm_response)
        logger.info(f"Successfully parsed {operation} result", extra={
            "result_type": type(parsed).__name__
        })
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON for {operation}", extra={
            "error": str(e),
            "response_preview": llm_response[:200]
        }, exc_info=True)
        raise LLMResponseError(
            f"Gemini returned invalid JSON for {operation}. Error: {e}"
        ) from e
