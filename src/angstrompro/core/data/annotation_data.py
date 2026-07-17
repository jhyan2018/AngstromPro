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
ANNOTATION_ROLES = ("bragg_peaks", "interest_region", "line_cut", "mask_center", "lockin_peak",
                    "register_points", "register_reference_points",
                    "circle_cut_points")


def serialize_annotation(ann: AnnotationData) -> dict:
    """Convert an annotation object to a plain JSON-safe dict for storage in ProcRecord."""
    if isinstance(ann, PointSetData):
        return {"type": "point_set", "coords": ann.coords.tolist()}
    if isinstance(ann, RegionData):
        return {"type": "region",
                "row_min": ann.row_min, "col_min": ann.col_min,
                "row_max": ann.row_max, "col_max": ann.col_max}
    if isinstance(ann, LineData):
        return {"type": "line",
                "p1": list(ann.p1), "p2": list(ann.p2), "n_points": ann.n_points}
    raise TypeError(f"serialize_annotation: unknown annotation type {type(ann)!r}")


def deserialize_annotation(d: dict) -> AnnotationData:
    """Reconstruct an annotation object from a serialized dict."""
    t = d.get("type")
    if t == "point_set":
        return PointSetData(coords=np.array(d["coords"]))
    if t == "region":
        return RegionData(row_min=d["row_min"], col_min=d["col_min"],
                          row_max=d["row_max"], col_max=d["col_max"])
    if t == "line":
        return LineData(p1=tuple(d["p1"]), p2=tuple(d["p2"]), n_points=d["n_points"])
    raise ValueError(f"deserialize_annotation: unknown type {t!r}")
