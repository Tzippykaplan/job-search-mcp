def require_str(name: str, value: object, *, allow_none: bool = False) -> str | None:
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{name} is required")
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    v = value.strip()
    if not v:
        raise ValueError(f"{name} cannot be empty or whitespace")
    return v

def require_dict(name: str, value: object, *, allow_empty: bool = True) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a dictionary")
    if not allow_empty and not value:
        raise ValueError(f"{name} cannot be empty")
    return value

def require_one_of(**kwargs: object) -> None:
    # expects key=value pairs, at least one must be truthy (after strip for strings)
    for v in kwargs.values():
        if isinstance(v, str):
            if v.strip():  # Only return if string has non-whitespace content
                return
        elif v:  # For non-strings, check truthiness
            return
    raise ValueError("At least one input must be provided")
