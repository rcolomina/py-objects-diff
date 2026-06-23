# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single utility function `verify_object_match` for deep comparison of Python objects in test scenarios. It returns `(True, "")` on match or `(False, "<path to difference>")` on mismatch, with dot-notation paths like `.field -> [0] -> nested_key` showing exactly where objects diverge.

## Architecture

The entire logic lives in `main.py`. The function is designed as a method (`self` parameter) to be embedded in a test base class. It recursively handles:

- **Dicts** — key presence + recursive value comparison
- **Lists/Tuples** — length check + index-by-index recursive comparison
- **Sets** — direct equality
- **Pydantic-style objects** — dispatches via `.dict` attribute to the dict branch
- **Primitives** — direct `!=` comparison

## Known issues

- Duplicate docstring at lines 2–15 (one should be removed)
- `type(x).__name__` is missing the `__` in the type mismatch message (line 20): `type(actual_obj).name` should be `type(actual_obj).__name__`
- The custom object branch (line 57) calls `.dict` as a property but doesn't call it — works for Pydantic v1 (`.dict` is a method there, not a property), so callers must pass `.dict()` results or the branch silently recurses incorrectly with Pydantic v2
