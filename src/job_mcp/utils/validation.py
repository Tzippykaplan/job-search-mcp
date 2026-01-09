"""Input validation utilities for MCP tool parameters."""

from job_mcp.exceptions import ValidationError


def require_str(name: str, value: object, *, allow_none: bool = False) -> str | None:
    """
    Validate that a value is a non-empty string.

    Args:
        name: Parameter name for error messages.
        value: Value to validate.
        allow_none: If True, None is allowed and returned as-is.

    Returns:
        Stripped string value, or None if allow_none=True and value is None.

    Raises:
        ValidationError: If value is None (when not allowed), not a string,
                        or empty/whitespace only.

    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{name} is required")
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")
    v = value.strip()
    if not v:
        raise ValidationError(f"{name} cannot be empty or whitespace")
    return v

def require_dict(name: str, value: object, *, allow_empty: bool = True) -> dict:
    """
    Validate that a value is a dictionary.

    Args:
        name: Parameter name for error messages.
        value: Value to validate.
        allow_empty: If False, raises error for empty dictionaries.

    Returns:
        The validated dictionary.

    Raises:
        ValidationError: If value is not a dict or is empty (when not allowed).
    """
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be a dictionary")
    if not allow_empty and not value:
        raise ValidationError(f"{name} cannot be empty")
    return value

def require_one_of(**kwargs: object) -> None:
    """
    Validate that at least one of the provided arguments is truthy.

    For string arguments, checks for non-empty content after stripping whitespace.
    For other types, checks truthiness directly.

    Args:
        **kwargs: Named arguments to check (e.g., job_url=url, job_text=text).

    Raises:
        ValidationError: If all arguments are falsy or empty strings.

    """
    for v in kwargs.values():
        if isinstance(v, str):
            if v.strip():  # Only return if string has non-whitespace content
                return
        elif v:  # For non-strings, check truthiness
            return
    raise ValidationError("At least one input must be provided")


def require_bool(name: str, value: object) -> bool:
    """
    Validate that a value is a boolean.

    Args:
        name: Parameter name for error messages.
        value: Value to validate.

    Returns:
        The validated boolean value.

    Raises:
        ValidationError: If value is not a boolean (true/false).
    """
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be a boolean (true/false)")
    return value
