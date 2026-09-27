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
ANNOTATION_ROLES = ("primary_points", "reference_points",
                    "bragg_peaks", "filter_points", "interest_region",
                    "line_cut", "mask_center", "lockin_peak",
                    "register_points", "register_reference_points",
                    "circle_cut_points")


def _json_native(value):
    """Recursively replace NumPy containers/scalars with JSON-native values."""
    if isinstance(value, np.ndarray):
        return _json_native(value.tolist())
    if isinstance(value, np.generic):
        return _json_native(value.item())
    if isinstance(value, (list, tuple)):
        return [_json_native(item) for item in value]
    if isinstance(value, complex):
        raise TypeError("Annotation coordinates must be real numbers")
    return value


def serialize_annotation(ann: AnnotationData) -> dict:
    """Convert an annotation object to a plain JSON-safe dictionary.

    GUI selections and scientific algorithms commonly produce NumPy scalar
    values.  Normalizing them here keeps every persistence route consistent:
    workspace archives, standalone native files, and process histories.
    """
    if isinstance(ann, PointSetData):
        return {"type": "point_set",
                "coords": _json_native(np.asarray(ann.coords))}
    if isinstance(ann, RegionData):
        return {"type": "region",
                "row_min": int(ann.row_min), "col_min": int(ann.col_min),
                "row_max": int(ann.row_max), "col_max": int(ann.col_max)}
    if isinstance(ann, LineData):
        return {"type": "line",
                "p1": [float(value) for value in ann.p1],
                "p2": [float(value) for value in ann.p2],
                "n_points": int(ann.n_points)}
    raise TypeError(f"serialize_annotation: unknown annotation type {type(ann)!r}")


def deserialize_annotation(d: dict) -> AnnotationData:
    """Reconstruct an annotation object from a serialized dict."""
    t = d.get("type")
    if t == "point_set":
        return PointSetData(coords=np.array(d["coords"]))
    if t == "region":
        return RegionData(row_min=int(d["row_min"]), col_min=int(d["col_min"]),
                          row_max=int(d["row_max"]), col_max=int(d["col_max"]))
    if t == "line":
        return LineData(
            p1=tuple(float(value) for value in d["p1"]),
            p2=tuple(float(value) for value in d["p2"]),
            n_points=int(d["n_points"]),
        )
    raise ValueError(f"deserialize_annotation: unknown type {t!r}")
