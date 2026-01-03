import pytest

from job_mcp.utils.validation import require_str, require_dict, require_one_of
from job_mcp.exceptions import ValidationError


def test_require_str_returns_stripped_value():
    assert require_str("x", "  hello  ") == "hello"

def test_require_str_allows_empty_inside_but_not_all_whitespace():
    assert require_str("x", " a b ") == "a b"

def test_require_str_none_not_allowed_raises():
    with pytest.raises(ValidationError, match=r"^x is required$"):
        require_str("x", None)

def test_require_str_none_allowed_returns_none():
    assert require_str("x", None, allow_none=True) is None

@pytest.mark.parametrize("value", [123, 12.3, True, {}, [], object()])
def test_require_str_non_string_raises(value):
    with pytest.raises(ValidationError, match=r"^x must be a string$"):
        require_str("x", value)

@pytest.mark.parametrize("value", ["", "   ", "\n\t  "])
def test_require_str_empty_or_whitespace_raises(value):
    with pytest.raises(ValidationError, match=r"^x cannot be empty or whitespace$"):
        require_str("x", value)


def test_require_dict_returns_same_dict():
    d = {"a": 1}
    assert require_dict("d", d) is d 

@pytest.mark.parametrize("value", [None, "x", 1, 1.2, True, [], (), set()])
def test_require_dict_non_dict_raises(value):
    with pytest.raises(ValidationError, match=r"^d must be a dictionary$"):
        require_dict("d", value)

def test_require_dict_empty_dict_raises():
    with pytest.raises(ValidationError, match=r"^d cannot be empty$"):
        require_dict("d", {}, allow_empty=False)

def test_require_dict_empty_dict_allowed_by_default():
    assert require_dict("d", {}) == {}



def test_require_one_of_raises_when_all_missing_or_empty():
    with pytest.raises(ValidationError, match=r"^At least one input must be provided$"):
        require_one_of(a=None, b="", c="   ", d=0, e=False, f=[])

def test_require_one_of_passes_when_nonempty_string_present():
 
    require_one_of(a="  x ", b=None)

def test_require_one_of_passes_when_truthy_non_string_present():
    require_one_of(a=1, b=None)

def test_require_one_of_passes_when_truthy_collection_present():
    require_one_of(a=[], b={"k": "v"}) 

def test_require_one_of_treats_whitespace_string_as_empty():
    with pytest.raises(ValidationError):
        require_one_of(a="   ", b=None)
