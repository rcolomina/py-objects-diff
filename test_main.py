import pytest
from main import verify_object_match


class Host:
    verify_object_match = verify_object_match


@pytest.fixture
def v():
    return Host()


# --- type mismatch ---

def test_type_mismatch(v):
    ok, reason = v.verify_object_match(1, "1")
    assert not ok
    assert "Type mismatch" in reason
    assert "int" in reason
    assert "str" in reason


# --- primitives ---

def test_primitives_equal(v):
    assert v.verify_object_match(42, 42) == (True, "")
    assert v.verify_object_match("hello", "hello") == (True, "")
    assert v.verify_object_match(True, True) == (True, "")
    assert v.verify_object_match(3.14, 3.14) == (True, "")

def test_primitives_not_equal(v):
    ok, reason = v.verify_object_match(1, 2)
    assert not ok
    assert "Value mismatch" in reason
    assert "1" in reason and "2" in reason


# --- dicts ---

def test_dict_equal(v):
    assert v.verify_object_match({"a": 1, "b": 2}, {"a": 1, "b": 2}) == (True, "")

def test_dict_size_mismatch(v):
    ok, reason = v.verify_object_match({"a": 1}, {"a": 1, "b": 2})
    assert not ok
    assert "Dict size mismatch" in reason

def test_dict_missing_key(v):
    ok, reason = v.verify_object_match({"a": 1}, {"b": 1})
    assert not ok
    assert "missing" in reason.lower()

def test_dict_value_mismatch_path(v):
    ok, reason = v.verify_object_match({"a": 1}, {"a": 2})
    assert not ok
    assert reason.startswith(".a ->")

def test_dict_nested_path(v):
    actual   = {"outer": {"inner": 1}}
    expected = {"outer": {"inner": 2}}
    ok, reason = v.verify_object_match(actual, expected)
    assert not ok
    assert ".outer -> .inner ->" in reason


# --- lists ---

def test_list_equal(v):
    assert v.verify_object_match([1, 2, 3], [1, 2, 3]) == (True, "")

def test_list_length_mismatch(v):
    ok, reason = v.verify_object_match([1, 2], [1])
    assert not ok
    assert "length mismatch" in reason.lower()

def test_list_element_mismatch_path(v):
    ok, reason = v.verify_object_match([1, 99, 3], [1, 2, 3])
    assert not ok
    assert reason.startswith("[1] ->")


# --- tuples ---

def test_tuple_equal(v):
    assert v.verify_object_match((1, 2), (1, 2)) == (True, "")

def test_tuple_mismatch(v):
    ok, reason = v.verify_object_match((1, 2), (1, 3))
    assert not ok
    assert "[1] ->" in reason


# --- sets ---

def test_set_equal(v):
    assert v.verify_object_match({1, 2, 3}, {1, 2, 3}) == (True, "")

def test_set_not_equal(v):
    ok, reason = v.verify_object_match({1, 2}, {1, 3})
    assert not ok
    assert "Sets" in reason


# --- custom objects with .dict ---

class Model:
    def __init__(self, data: dict):
        self.dict = data


def test_custom_object_equal(v):
    a = Model({"x": 1})
    b = Model({"x": 1})
    assert v.verify_object_match(a, b) == (True, "")

def test_custom_object_mismatch(v):
    a = Model({"x": 1})
    b = Model({"x": 2})
    ok, reason = v.verify_object_match(a, b)
    assert not ok
    assert ".x ->" in reason


# --- deeply nested composition ---

def test_dict_containing_list_containing_dict(v):
    actual   = {"items": [{"id": 1}, {"id": 99}]}
    expected = {"items": [{"id": 1}, {"id": 2}]}
    ok, reason = v.verify_object_match(actual, expected)
    assert not ok
    assert ".items -> [1] -> .id ->" in reason


# --- ignore_empty_strings wildcard ---

def test_ignore_empty_strings_off_by_default(v):
    # An empty string in expected is a normal value unless the flag is set.
    ok, reason = v.verify_object_match("hello", "")
    assert not ok
    assert "Value mismatch" in reason

def test_ignore_empty_strings_matches_any_string(v):
    assert v.verify_object_match("hello", "", ignore_empty_strings=True) == (True, "")

def test_ignore_empty_strings_matches_across_types(v):
    # The wildcard is checked before the type comparison, so it spans types.
    assert v.verify_object_match(42, "", ignore_empty_strings=True) == (True, "")
    assert v.verify_object_match([1, 2], "", ignore_empty_strings=True) == (True, "")
    assert v.verify_object_match(None, "", ignore_empty_strings=True) == (True, "")

def test_ignore_empty_strings_in_dict_value(v):
    actual   = {"name": "Alice", "id": 7}
    expected = {"name": "",      "id": 7}
    assert v.verify_object_match(actual, expected, ignore_empty_strings=True) == (True, "")

def test_ignore_empty_strings_only_wildcards_empties(v):
    # Non-empty expected strings must still match exactly.
    actual   = {"name": "Alice", "city": "Paris"}
    expected = {"name": "",      "city": "London"}
    ok, reason = v.verify_object_match(actual, expected, ignore_empty_strings=True)
    assert not ok
    assert ".city ->" in reason

def test_ignore_empty_strings_nested(v):
    actual   = {"user": {"name": "Bob", "token": "abc123"}}
    expected = {"user": {"name": "Bob", "token": ""}}
    assert v.verify_object_match(actual, expected, ignore_empty_strings=True) == (True, "")

def test_ignore_empty_strings_in_list(v):
    assert v.verify_object_match(
        ["a", "b", "c"], ["a", "", "c"], ignore_empty_strings=True
    ) == (True, "")

def test_actual_empty_string_is_not_wildcard(v):
    # Only empties in the *expected* object are wildcards, not the actual one.
    ok, reason = v.verify_object_match("", "something", ignore_empty_strings=True)
    assert not ok
    assert "Value mismatch" in reason
