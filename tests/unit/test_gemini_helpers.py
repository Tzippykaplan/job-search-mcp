import json
import pytest

from job_mcp.utils.gemini_helpers import strip_fences, as_list, robust_json_loads


def test_strip_fences_removes_json_fence():
    text = "```json\n{\"a\": 1}\n```"
    assert strip_fences(text) == '{"a": 1}'


def test_strip_fences_no_fence_returns_same_trimmed():
    text = "  {\"a\": 1}  "
    assert strip_fences(text) == '{"a": 1}'


def test_as_list_filters_only_strings():
    assert as_list(["a", 1, None, "b"]) == ["a", "b"]
    assert as_list("nope") == []


def test_robust_json_loads_plain_json():
    assert robust_json_loads('{"x": 2}') == {"x": 2}


def test_robust_json_loads_json_inside_text():
    raw = "Here is your result:\n{\"ok\": true, \"n\": 3}\nThanks!"
    assert robust_json_loads(raw) == {"ok": True, "n": 3}


def test_robust_json_loads_raises_when_no_json():
    with pytest.raises(json.JSONDecodeError):
        robust_json_loads("no json here")
