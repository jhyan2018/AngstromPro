# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

SI prefix helpers shared across all plot widgets.
"""
from __future__ import annotations

import math

import numpy as np

_SI = {
    -18: ('a', -18), -15: ('f', -15), -12: ('p', -12),
     -9: ('n',  -9),  -6: ('µ',  -6),  -3: ('m',  -3),
      0: ('',    0),   3: ('k',   3),   6: ('M',   6),
      9: ('G',   9),  12: ('T',  12),
}

# Display multipliers are the inverse of unit-prefix magnitudes.  Multiplying
# volts by 1e3 displays millivolts; multiplying by 1e-12 displays teravolts.
# Keep the choices on engineering (powers-of-1000) boundaries and clamp to the
# prefixes AngstromPro can name explicitly: tera through atto.
DISPLAY_FACTORS = tuple(10.0 ** exponent for exponent in range(-12, 19, 3))


def si_scale(values: np.ndarray) -> tuple[str, float]:
    """Return (SI prefix string, multiplicative scale factor) for an array."""
    finite = np.asarray(values)[np.isfinite(values)]
    if finite.size == 0:
        return '', 1.0
    abs_max = float(np.max(np.abs(finite)))
    if abs_max == 0:
        return '', 1.0
    exp = int(3 * math.floor(math.log10(abs_max) / 3))
    exp = max(-18, min(12, exp))
    prefix, e = _SI[exp]
    return prefix, 10 ** (-e)


def factor_prefix(factor: float) -> str:
    """Return the unit prefix produced by a supported display multiplier."""
    if not math.isfinite(factor) or factor <= 0:
        return ""
    factor_exp = int(round(math.log10(factor)))
    factor_exp = max(-12, min(18, 3 * round(factor_exp / 3)))
    return _SI[-factor_exp][0]


def nearest_display_factor(factor: float) -> float:
    """Clamp an arbitrary positive factor to the nearest named SI choice."""
    if not math.isfinite(factor) or factor <= 0:
        return 1.0
    return min(DISPLAY_FACTORS, key=lambda candidate: abs(
        math.log10(candidate) - math.log10(factor)))


def format_factor(factor: float) -> str:
    """Return a stable compact string such as ``1e12`` or ``1``."""
    factor = nearest_display_factor(factor)
    if factor == 1.0:
        return "1"
    return f"1e{int(round(math.log10(factor)))}"


def split_label_unit(label: str, units: str = "") -> tuple[str, str]:
    """Separate a possibly unit-suffixed label without duplicating units."""
    import re

    text = str(label or "").strip()
    resolved_units = str(units or "").strip()
    match = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", text)
    if match:
        embedded_units = match.group(2).strip()
        if not resolved_units:
            resolved_units = embedded_units
        if not embedded_units or embedded_units == resolved_units:
            text = match.group(1).strip()
    return text, resolved_units


def scaled_axis_label(base: str, units: str, factor: float) -> str:
    """Build ``Quantity (prefixed-unit)`` for a display multiplier."""
    base, units = split_label_unit(base, units)
    if not units:
        return base
    unit_text = f"{factor_prefix(factor)}{units}"
    return f"{base} ({unit_text})" if base else unit_text
