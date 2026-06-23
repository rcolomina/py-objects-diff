# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single utility function `verify_object_match` for deep comparison of Python objects in test scenarios. It returns `(True, "")` on match or `(False, "<path to difference>")` on mismatch, with dot-notation paths like `.field -> [0] -> nested_key` showing exactly where objects diverge.

## Architecture

The logic lives in `main.py`. `verify_object_match` stays a thin method (`self` parameter) so it can be embedded in a test base class; it builds a `MatchOptions` and delegates to the module-level recursive helper `_diffs`, which carries the path prefix and returns a list of difference descriptions (empty == match). The recursion handles:

- **Dicts** — size/key-presence check + recursive value comparison
- **Lists/Tuples** — length check + index-by-index recursive comparison
- **Sets** — direct equality
- **Pydantic-style objects** — dispatches via `.dict` attribute to the dict branch
- **Primitives** — `!=` comparison (or `math.isclose` when a tolerance is set)

## Comparison options

Tuned via keyword flags on `verify_object_match` (or a pre-built `options=MatchOptions(...)`):

- `ignore_empty_strings` — an empty string in the expected object is a wildcard matching any actual value
- `ignore_types` — skip the exact-type check so only leaf values are compared (list vs tuple, int vs float)
- `ignore_extra_keys` — actual dicts may carry keys absent from expected (subset matching)
- `ignore_keys` — set of key names skipped at any depth (e.g. `id`, `created_at`)
- `rel_tol` / `abs_tol` — approximate numeric leaf comparison via `math.isclose`
- `collect_all` — report every difference; the second tuple element becomes a `list` of strings instead of one string

Flags and `options=` are mutually exclusive (passing both raises `TypeError`).

## Notes

- The custom-object branch reads `.dict` as an attribute (no call). This suits objects that store a dict attribute and Pydantic v1 callers passing `.dict()` results; a raw Pydantic v2 model whose `.dict` is a bound method would not compare meaningfully.
