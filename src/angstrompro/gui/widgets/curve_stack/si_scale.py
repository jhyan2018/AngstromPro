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


def si_scale(values: np.ndarray) -> tuple[str, float]:
    """Return (SI prefix string, multiplicative scale factor) for an array."""
    abs_max = float(np.max(np.abs(values)))
    if abs_max == 0:
        return '', 1.0
    exp = int(3 * math.floor(math.log10(abs_max) / 3))
    exp = max(-18, min(12, exp))
    prefix, e = _SI[exp]
    return prefix, 10 ** (-e)
