# -*- coding: utf-8 -*-
"""
Created on 2026-07-05

@author: jiahaoYan

config_validation — type-check and coerce config dicts against a defaults dict.

Rules
-----
- dict   → recurse
- bool   → coerce int 0/1; accept "true"/"false" strings; reject others
- float  → coerce int; reject str/bool
- int    → coerce whole-number float; reject str/bool
- str    → coerce anything via str() with a warning
- list   → must be list; reject others
- Keys present in cfg but absent in defaults are passed through unchanged
  (forward-compatibility: newer plugin version saved a key the older default
  doesn't know about yet).

Invalid values are dropped (reverted to the default) and a warning is logged.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

log = logging.getLogger(__name__)


def validate_and_coerce(cfg: dict, defaults: dict, _path: str = "") -> dict:
    """Return a new dict with values type-checked and coerced against *defaults*.

    Keys in *cfg* that have no counterpart in *defaults* are passed through.
    """
    result = {}
    for key, value in cfg.items():
        full_key = f"{_path}.{key}" if _path else key
        default_val = defaults.get(key)

        if default_val is None:
            # Key unknown in defaults — pass through (forward-compat)
            result[key] = copy.deepcopy(value)
            continue

        if isinstance(default_val, dict):
            if isinstance(value, dict):
                result[key] = validate_and_coerce(value, default_val, full_key)
            else:
                log.warning("config[%s]: expected dict, got %s — reset to default",
                            full_key, type(value).__name__)
                result[key] = copy.deepcopy(default_val)
            continue

        coerced = _coerce(value, default_val, full_key)
        if coerced is _INVALID:
            log.warning("config[%s]: cannot coerce %r (%s) to %s — reset to default",
                        full_key, value, type(value).__name__, type(default_val).__name__)
            result[key] = copy.deepcopy(default_val)
        else:
            result[key] = coerced

    return result


# sentinel for uncoerceable values
_INVALID = object()


def _coerce(value: Any, default: Any, key: str) -> Any:
    expected = type(default)

    # exact type match — fast path
    if type(value) is expected:
        return value

    # bool is a subclass of int in Python — check bool first
    if expected is bool:
        if isinstance(value, int) and not isinstance(value, bool):
            return bool(value)
        if isinstance(value, str):
            if value.lower() == "true":
                return True
            if value.lower() == "false":
                return False
        return _INVALID

    if expected is float:
        if isinstance(value, int) and not isinstance(value, bool):
            return float(value)
        return _INVALID

    if expected is int:
        if isinstance(value, float) and not isinstance(value, bool) and value == int(value):
            return int(value)
        return _INVALID

    if expected is str:
        log.warning("config[%s]: expected str, got %s — coercing via str()", key, type(value).__name__)
        return str(value)

    if expected is list:
        return _INVALID

    return _INVALID
