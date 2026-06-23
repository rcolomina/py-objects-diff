from dataclasses import dataclass, field
from math import isclose
from typing import Any, Iterable, List, Tuple, Union


@dataclass
class MatchOptions:
    """
    Tunable knobs for :func:`verify_object_match`.

    Relaxing:
      * ``ignore_empty_strings`` - an empty string ("") in the expected object
        is a wildcard that matches any actual value, regardless of type.
      * ``ignore_types`` - skip the exact-type check at every level so only the
        leaf values are compared (e.g. a list matches a tuple, an int a float).
      * ``ignore_extra_keys`` - a dict in the actual object may carry keys that
        are absent from the expected object; only the expected keys are checked.
      * ``ignore_keys`` - key names to skip entirely, at any depth (handy for
        volatile fields such as ``id`` or ``created_at``).
      * ``rel_tol`` / ``abs_tol`` - compare numeric leaves approximately with
        :func:`math.isclose` instead of exact equality.

    Thoroughness:
      * ``collect_all`` - report every difference instead of stopping at the
        first. When True the second element of the result is a ``list`` of
        path/reason strings rather than a single string.
    """

    ignore_empty_strings: bool = False
    ignore_types: bool = False
    ignore_extra_keys: bool = False
    ignore_keys: Iterable[str] = field(default_factory=frozenset)
    rel_tol: float = 0.0
    abs_tol: float = 0.0
    collect_all: bool = False

    def __post_init__(self) -> None:
        # Normalise to a frozenset so membership tests are cheap and the
        # default is not a shared mutable.
        self.ignore_keys = frozenset(self.ignore_keys)


def _join(path: str, segment: str) -> str:
    """Append a path segment, using ``->`` as the separator."""
    return segment if not path else f"{path} -> {segment}"


def _leaf_differs(actual_obj: Any, expected_obj: Any, opts: MatchOptions) -> bool:
    """Compare two scalar leaves, honouring the numeric tolerances."""
    if (opts.rel_tol or opts.abs_tol) \
            and isinstance(actual_obj, (int, float)) and not isinstance(actual_obj, bool) \
            and isinstance(expected_obj, (int, float)) and not isinstance(expected_obj, bool):
        return not isclose(actual_obj, expected_obj, rel_tol=opts.rel_tol, abs_tol=opts.abs_tol)
    return actual_obj != expected_obj


def _diffs(actual_obj: Any, expected_obj: Any, opts: MatchOptions, path: str) -> List[str]:
    """
    Recursively collect the differences between two objects.

    Returns a list of human-readable diff descriptions (empty == match). When
    ``opts.collect_all`` is False the walk short-circuits on the first diff, so
    the list holds at most one entry.
    """
    out: List[str] = []

    def report(msg: str) -> None:
        out.append(f"{path} -> {msg}" if path else msg)

    # 0. An empty string in the expected object is a wildcard "don't care".
    #    Checked before the type comparison so it matches across any type.
    if opts.ignore_empty_strings and isinstance(expected_obj, str) and expected_obj == "":
        return out

    # 1. Check that the data types match (unless types are ignored).
    if not opts.ignore_types and type(actual_obj) != type(expected_obj):
        report(f"Type mismatch: {type(actual_obj).__name__} vs {type(expected_obj).__name__}")
        return out

    # 2. Dictionaries
    if isinstance(actual_obj, dict):
        if not isinstance(expected_obj, dict):
            report(f"Structure mismatch: dict vs {type(expected_obj).__name__}")
            return out

        ignore = opts.ignore_keys
        a_keys = [k for k in actual_obj if k not in ignore]
        e_keys = [k for k in expected_obj if k not in ignore]

        # With exact-key matching, size parity + "every expected key present"
        # guarantees the key sets are equal, so no separate extra-key pass is
        # needed. When ignore_extra_keys is set we drop the size check entirely.
        if not opts.ignore_extra_keys and len(a_keys) != len(e_keys):
            report(f"Dict size mismatch: {len(a_keys)} items vs {len(e_keys)} items")
            return out

        for key in e_keys:
            if key not in actual_obj:
                report(f"Key '{key}' is missing in the actual object")
                if not opts.collect_all:
                    return out
                continue
            child = _diffs(actual_obj[key], expected_obj[key], opts, _join(path, f".{key}"))
            out.extend(child)
            if child and not opts.collect_all:
                return out
        return out

    # 3. Lists or tuples
    if isinstance(actual_obj, (list, tuple)):
        if not isinstance(expected_obj, (list, tuple)):
            report(f"Structure mismatch: {type(actual_obj).__name__} vs {type(expected_obj).__name__}")
            return out
        if len(actual_obj) != len(expected_obj):
            report(f"List length mismatch: {len(actual_obj)} vs {len(expected_obj)}")
            return out
        for index, (item1, item2) in enumerate(zip(actual_obj, expected_obj)):
            child = _diffs(item1, item2, opts, _join(path, f"[{index}]"))
            out.extend(child)
            if child and not opts.collect_all:
                return out
        return out

    # 4. Sets
    if isinstance(actual_obj, set):
        if actual_obj != expected_obj:
            report("Sets do not have the same items")
        return out

    # 5. Custom class objects (compared through their `.dict`)
    if hasattr(actual_obj, "dict") and hasattr(expected_obj, "dict"):
        return _diffs(actual_obj.dict, expected_obj.dict, opts, path)

    # 6. Simple values (strings, numbers, booleans)
    if _leaf_differs(actual_obj, expected_obj, opts):
        report(f"Value mismatch: {actual_obj} != {expected_obj}")
    return out


def verify_object_match(
    self,
    actual_obj: Any,
    expected_obj: Any,
    *,
    options: MatchOptions = None,
    **flags: Any,
) -> Tuple[bool, Union[str, List[str]]]:
    """
    Deeply compares two Python objects, including dictionaries, lists, and custom classes.
    Returns (True, "") if equal, or (False, "Reason why") if different.

    Behaviour is tuned via keyword flags (see :class:`MatchOptions` for the full
    list), e.g. ``ignore_extra_keys=True`` or ``rel_tol=1e-6``. Alternatively
    pass a pre-built ``options=MatchOptions(...)``.

    When ``collect_all`` is enabled the second element of the returned tuple is a
    ``list`` of every difference found, rather than a single string.
    """
    if options is None:
        options = MatchOptions(**flags)
    elif flags:
        raise TypeError("Pass either an `options` object or individual flags, not both")

    diffs = _diffs(actual_obj, expected_obj, options, "")

    if options.collect_all:
        return (not diffs, diffs)
    return (not diffs, diffs[0] if diffs else "")
