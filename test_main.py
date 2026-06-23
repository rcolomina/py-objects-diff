import pytest
from main import verify_object_match, MatchOptions


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


# --- ignore_types (compare values only, down to the leaves) ---

def test_ignore_types_off_by_default(v):
    ok, reason = v.verify_object_match([1, 2], (1, 2))
    assert not ok
    assert "Type mismatch" in reason

def test_ignore_types_list_vs_tuple(v):
    assert v.verify_object_match([1, 2], (1, 2), ignore_types=True) == (True, "")

def test_ignore_types_int_vs_float_leaf(v):
    assert v.verify_object_match(1, 1.0, ignore_types=True) == (True, "")

def test_ignore_types_nested_container_kinds(v):
    actual   = {"nums": [1, 2, 3]}
    expected = {"nums": (1, 2, 3)}
    assert v.verify_object_match(actual, expected, ignore_types=True) == (True, "")

def test_ignore_types_still_reports_value_mismatch(v):
    # Types are ignored, but leaf *values* must still match.
    ok, reason = v.verify_object_match([1, 2], (1, 99), ignore_types=True)
    assert not ok
    assert "[1] ->" in reason

def test_ignore_types_incompatible_structure(v):
    # A dict vs a list is a structure mismatch, not a match.
    ok, reason = v.verify_object_match({"a": 1}, [1], ignore_types=True)
    assert not ok
    assert "Structure mismatch" in reason

def test_ignore_types_with_ignore_empty_strings(v):
    # The two flags compose: wildcard empties + type-agnostic comparison.
    actual   = {"id": 5, "tags": ["a", "b"]}
    expected = {"id": "", "tags": ("a", "b")}
    assert v.verify_object_match(
        actual, expected, ignore_empty_strings=True, ignore_types=True
    ) == (True, "")


# --- ignore_extra_keys (subset dict matching) ---

def test_extra_keys_fail_without_flag(v):
    actual   = {"a": 1, "b": 2, "c": 3}
    expected = {"a": 1, "b": 2}
    ok, reason = v.verify_object_match(actual, expected)
    assert not ok
    assert "Dict size mismatch" in reason

def test_ignore_extra_keys_accepts_superset(v):
    actual   = {"a": 1, "b": 2, "c": 3}
    expected = {"a": 1, "b": 2}
    assert v.verify_object_match(actual, expected, ignore_extra_keys=True) == (True, "")

def test_ignore_extra_keys_still_requires_expected_keys(v):
    actual   = {"a": 1}
    expected = {"a": 1, "b": 2}
    ok, reason = v.verify_object_match(actual, expected, ignore_extra_keys=True)
    assert not ok
    assert "missing" in reason.lower() and "b" in reason

def test_ignore_extra_keys_still_checks_values(v):
    actual   = {"a": 1, "b": 2, "c": 3}
    expected = {"a": 1, "b": 99}
    ok, reason = v.verify_object_match(actual, expected, ignore_extra_keys=True)
    assert not ok
    assert ".b ->" in reason

def test_ignore_extra_keys_nested(v):
    actual   = {"user": {"name": "Bob", "age": 5, "extra": "x"}}
    expected = {"user": {"name": "Bob", "age": 5}}
    assert v.verify_object_match(actual, expected, ignore_extra_keys=True) == (True, "")


# --- ignore_keys (skip named keys at any depth) ---

def test_ignore_keys_skips_volatile_field(v):
    actual   = {"id": 999, "name": "Alice"}
    expected = {"id": 1,   "name": "Alice"}
    assert v.verify_object_match(actual, expected, ignore_keys={"id"}) == (True, "")

def test_ignore_keys_balances_sizes(v):
    # The ignored key is excluded from the size check too.
    actual   = {"id": 1, "name": "Alice"}
    expected = {"name": "Alice"}
    assert v.verify_object_match(actual, expected, ignore_keys={"id"}) == (True, "")

def test_ignore_keys_applies_at_depth(v):
    actual   = {"user": {"name": "Bob", "updated_at": 111}}
    expected = {"user": {"name": "Bob", "updated_at": 222}}
    assert v.verify_object_match(actual, expected, ignore_keys={"updated_at"}) == (True, "")

def test_ignore_keys_does_not_hide_other_diffs(v):
    actual   = {"id": 1, "name": "Alice"}
    expected = {"id": 2, "name": "Bob"}
    ok, reason = v.verify_object_match(actual, expected, ignore_keys={"id"})
    assert not ok
    assert ".name ->" in reason


# --- rel_tol / abs_tol (approximate numeric comparison) ---

def test_float_exact_fails_without_tolerance(v):
    ok, reason = v.verify_object_match(1.0, 1.0001)
    assert not ok
    assert "Value mismatch" in reason

def test_abs_tol_matches_close_floats(v):
    assert v.verify_object_match(1.0, 1.0001, abs_tol=1e-3) == (True, "")

def test_rel_tol_matches_close_floats(v):
    # |100 - 101| = 1 <= 0.02 * 101
    assert v.verify_object_match(100.0, 101.0, rel_tol=0.02) == (True, "")

def test_tolerance_still_rejects_far_floats(v):
    ok, reason = v.verify_object_match(1.0, 2.0, abs_tol=1e-3)
    assert not ok
    assert "Value mismatch" in reason

def test_tolerance_applies_in_nested_structures(v):
    actual   = {"coords": [1.0, 2.0]}
    expected = {"coords": [1.00001, 2.00001]}
    assert v.verify_object_match(actual, expected, abs_tol=1e-3) == (True, "")

def test_tolerance_does_not_apply_to_bool(v):
    # bool is an int subclass but must not be compared numerically.
    ok, reason = v.verify_object_match(True, False, abs_tol=10)
    assert not ok
    assert "Value mismatch" in reason


# --- collect_all (report every difference) ---

def test_collect_all_returns_list(v):
    actual   = {"a": 1, "b": 2, "c": 3}
    expected = {"a": 9, "b": 2, "c": 8}
    ok, diffs = v.verify_object_match(actual, expected, collect_all=True)
    assert not ok
    assert isinstance(diffs, list)
    assert len(diffs) == 2
    assert any(".a ->" in d for d in diffs)
    assert any(".c ->" in d for d in diffs)

def test_collect_all_match_is_empty_list(v):
    ok, diffs = v.verify_object_match({"a": 1}, {"a": 1}, collect_all=True)
    assert ok
    assert diffs == []

def test_collect_all_nested_list(v):
    actual   = [{"id": 1}, {"id": 2}, {"id": 3}]
    expected = [{"id": 9}, {"id": 2}, {"id": 8}]
    ok, diffs = v.verify_object_match(actual, expected, collect_all=True)
    assert not ok
    assert len(diffs) == 2
    assert any("[0] -> .id ->" in d for d in diffs)
    assert any("[2] -> .id ->" in d for d in diffs)

def test_collect_all_off_returns_single_string(v):
    ok, reason = v.verify_object_match({"a": 1, "b": 2}, {"a": 9, "b": 8})
    assert not ok
    assert isinstance(reason, str)


# --- MatchOptions object + composition ---

def test_options_object_accepted(v):
    opts = MatchOptions(ignore_extra_keys=True, ignore_keys={"id"})
    actual   = {"id": 7, "name": "Alice", "extra": True}
    expected = {"name": "Alice"}
    assert v.verify_object_match(actual, expected, options=opts) == (True, "")

def test_options_and_flags_are_mutually_exclusive(v):
    with pytest.raises(TypeError):
        v.verify_object_match(1, 1, options=MatchOptions(), ignore_types=True)

def test_combined_flags(v):
    # extra keys ignored, id wildcarded, float within tolerance, collect all
    actual   = {"id": 42, "score": 0.1 + 0.2, "tags": ["x", "y"], "debug": True}
    expected = {"id": "", "score": 0.3, "tags": ["x", "z"]}
    ok, diffs = v.verify_object_match(
        actual, expected,
        ignore_empty_strings=True, ignore_extra_keys=True,
        abs_tol=1e-9, collect_all=True,
    )
    assert not ok
    assert len(diffs) == 1
    assert ".tags -> [1] ->" in diffs[0]
