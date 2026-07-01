# -*- coding: utf-8 -*-
"""
Annotation data types for AngstromPro workspace items.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class PointSetData:
    """Bragg peaks or any set of 2D points. coords shape: (N, 2) [row, col]."""
    coords: np.ndarray = field(default_factory=lambda: np.empty((0, 2)))


@dataclass
class RegionData:
    """Rectangular crop/analysis region in pixel coords."""
    row_min: int = 0
    col_min: int = 0
    row_max: int = 0
    col_max: int = 0


@dataclass
class LineData:
    """Line profile between two points."""
    p1: tuple[float, float] = (0.0, 0.0)
    p2: tuple[float, float] = (0.0, 0.0)
    n_points: int = 256


AnnotationData = PointSetData | RegionData | LineData
ANNOTATION_ROLES = ("bragg_peaks", "interest_region", "line_profile", "mask_center")
