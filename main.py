from typing import Any, Tuple


def verify_object_match(
    self,
    actual_obj: Any,
    expected_obj: Any,
    ignore_empty_strings: bool = False,
    ignore_types: bool = False,
) -> Tuple[bool, str]:
    """
    Deeply compares two Python objects, including dictionaries, lists, and custom classes.
    Returns (True, "") if equal, or (False, "Reason why") if different.

    If ``ignore_empty_strings`` is True, any empty string ("") found in the
    expected object is treated as a wildcard "don't care": the corresponding
    value in the actual object is accepted regardless of its type or value.

    If ``ignore_types`` is True, the exact-type check is skipped at every level,
    so only the leaf values are compared. Structurally-equivalent objects then
    match even when their types differ (e.g. a list vs a tuple, or an int vs a
    float). Incompatible container kinds (e.g. a dict vs a list) still report a
    clean structure mismatch rather than matching.
    """
    # 0. Treat an empty string in the expected object as a wildcard.
    #    Checked before the type comparison so it matches across any type.
    if ignore_empty_strings and isinstance(expected_obj, str) and expected_obj == "":
        return True, ""

    # 1. Check if they have the same data type (unless types are ignored).
    if not ignore_types and type(actual_obj) != type(expected_obj):
        return (
            False,
            f"Type mismatch: {type(actual_obj).__name__} vs {type(expected_obj).__name__}",
        )

    # 2. Compare Dictionaries
    if isinstance(actual_obj, dict):
        if not isinstance(expected_obj, dict):
            return (
                False,
                f"Structure mismatch: dict vs {type(expected_obj).__name__}",
            )
        if len(actual_obj) != len(expected_obj):
            return (
                False,
                f"Dict size mismatch: {len(actual_obj)} items vs {len(expected_obj)} items",
            )
        for key in actual_obj:
            if key not in expected_obj:
                return False, f"Key '{key}' is missing in the second object"
            is_match, reason = self.verify_object_match(
                actual_obj=actual_obj[key],
                expected_obj=expected_obj[key],
                ignore_empty_strings=ignore_empty_strings,
                ignore_types=ignore_types,
            )
            if not is_match:
                return False, f".{key} -> {reason}"
        return True, ""

    # 3. Compare Lists or Tuples
    elif isinstance(actual_obj, (list, tuple)):
        if not isinstance(expected_obj, (list, tuple)):
            return (
                False,
                f"Structure mismatch: {type(actual_obj).__name__} vs {type(expected_obj).__name__}",
            )
        if len(actual_obj) != len(expected_obj):
            return False, f"List length mismatch: {len(actual_obj)} vs {len(expected_obj)}"
        for index, (item1, item2) in enumerate(zip(actual_obj, expected_obj)):
            is_match, reason = self.verify_object_match(
                actual_obj=item1,
                expected_obj=item2,
                ignore_empty_strings=ignore_empty_strings,
                ignore_types=ignore_types,
            )
            if not is_match:
                return False, f"[{index}] -> {reason}"
        return True, ""

    # 4. Compare Sets
    elif isinstance(actual_obj, set):
        if actual_obj != expected_obj:
            return False, "Sets do not have the same items"
        return True, ""

    # 5. Compare Custom Class Objects (checks their variables)
    elif hasattr(actual_obj, "dict") and hasattr(expected_obj, "dict"):
        return self.verify_object_match(
            actual_obj=actual_obj.dict,
            expected_obj=expected_obj.dict,
            ignore_empty_strings=ignore_empty_strings,
            ignore_types=ignore_types,
        )

    # 6. Compare Simple Values (Strings, Numbers, Booleans)
    else:
        if actual_obj != expected_obj:
            return False, f"Value mismatch: {actual_obj} != {expected_obj}"
        return True, ""
