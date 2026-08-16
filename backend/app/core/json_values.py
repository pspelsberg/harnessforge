"""Bounded JSON value validation shared by public feature contracts."""
from __future__ import annotations
from math import isfinite
from typing import Any

def validate_json_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 8: raise ValueError("value nesting is too deep")
    if value is None or isinstance(value, (bool, int)): return value
    if isinstance(value, str):
        if len(value.encode("utf-8")) > 128*1024: raise ValueError("string value is too large")
        return value
    if isinstance(value, float):
        if not isfinite(value): raise ValueError("numbers must be finite")
        return value
    if isinstance(value, list):
        if len(value) > 128: raise ValueError("list is too large")
        for item in value: validate_json_value(item, depth=depth + 1)
        return value
    if isinstance(value, dict):
        if len(value) > 64: raise ValueError("object has too many keys")
        if not all(isinstance(k, str) and len(k) <= 128 for k in value): raise ValueError("keys must be bounded strings")
        for item in value.values(): validate_json_value(item, depth=depth + 1)
        return value
    raise ValueError("value must contain JSON values only")
