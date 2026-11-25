"""Check a JSON value against a TypedDict-based annotation, recursively and strictly.

Missing keys, extra keys and wrong types are all reported, so the SDK types cannot drift
from what the Courthouse really returns.
"""

from __future__ import annotations

import types
import typing
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints, is_typeddict


def check(value: Any, tp: Any, path: str = "$") -> list[str]:
    origin = get_origin(tp)
    if is_typeddict(tp):
        if not isinstance(value, dict):
            return [f"{path}: expected object, got {type(value).__name__}"]
        hints = get_type_hints(tp)
        errs = [f"{path}.{k}: missing" for k in hints if k not in value]
        errs += [f"{path}.{k}: unexpected key" for k in value if k not in hints]
        for k, t in hints.items():
            if k in value:
                errs += check(value[k], t, f"{path}.{k}")
        return errs
    if origin is Literal:
        return [] if value in get_args(tp) else [f"{path}: {value!r} not in {get_args(tp)}"]
    if origin in (Union, types.UnionType):
        options = get_args(tp)
        if any(not check(value, t, path) for t in options):
            return []
        return [f"{path}: {value!r} matches none of {options}"]
    if origin is list:
        if not isinstance(value, list):
            return [f"{path}: expected list"]
        errs: list[str] = []
        for i, v in enumerate(value):
            errs += check(v, get_args(tp)[0], f"{path}[{i}]")
        return errs
    if origin is dict:
        if not isinstance(value, dict):
            return [f"{path}: expected object"]
        errs = []
        for k, v in value.items():
            errs += check(v, get_args(tp)[1], f"{path}.{k}")
        return errs
    if tp is type(None):
        return [] if value is None else [f"{path}: expected null"]
    if tp is float:
        ok = isinstance(value, int | float) and not isinstance(value, bool)
    elif tp is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    else:
        ok = isinstance(value, tp)
    return [] if ok else [f"{path}: expected {getattr(tp, '__name__', tp)}, got {value!r}"]


def assert_shape(value: Any, tp: Any) -> None:
    errs = check(value, tp)
    assert not errs, "\n".join(errs[:20])


__all__ = ["assert_shape", "check", "typing"]
