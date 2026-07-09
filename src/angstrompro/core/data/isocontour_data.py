# -*- coding: utf-8 -*-
"""
Created on Wed Jul 09 2026

@author: jiahaoYan

IsocontourResult hierarchy — mathematical extracted features of UdsDataStru.

These are purely geometric/numerical results; they carry no physics meaning.
Physics interpretation (e.g. "Fermi surface") is added via notes by the
caller (e.g. a dispersion-level registered process).

Class hierarchy
---------------
  IsocontourResult          — base, holds level, method, notes, kind tag
    IsopointResult          — ndim=1 f(x)=level  → array of x positions  (0-D result)
    IsolineResult           — ndim=2 f(x,y)=level → list of (N,2) polylines
    IsosurfaceResult        — ndim=3 f(x,y,z)=level → triangulated mesh

kind field
----------
Used by IO to dispatch on load:
  "isopoint" | "isoline" | "isosurface"
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class IsocontourResult:
    """Base class for all isocontour extraction results."""
    kind:         str   = ""       # set by each subclass as class default
    level:        float = 0.0     # the iso-value that was extracted
    method:       str   = ""      # algorithm used, e.g. "marching_squares"
    source_axes:  tuple = ()      # which UDS axis indices were used, e.g. (1, 2)
    layer_index:  int   = 0       # index along axis[0] of the source UDS
    notes:        str   = ""      # free-text; physics meaning added by caller


@dataclass
class IsopointResult(IsocontourResult):
    """
    Isocontour of a 1-D function f(x) = level.
    Result: x positions where f crosses level.

    points : (N,) array of x-axis values
    """
    kind:   str        = "isopoint"
    points: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))


@dataclass
class IsolineResult(IsocontourResult):
    """
    Isocontour of a 2-D function f(x,y) = level.
    Result: list of closed/open polyline loops, each shape (N, 2).

    contours : list of (N, 2) float64 arrays, one per disconnected loop
    """
    kind:     str              = "isoline"
    contours: list[np.ndarray] = field(default_factory=list)


@dataclass
class IsosurfaceResult(IsocontourResult):
    """
    Isocontour of a 3-D function f(x,y,z) = level.
    Result: triangulated mesh from marching cubes.

    vertices : (V, 3) float64 — vertex positions
    faces    : (F, 3) int32   — triangle indices into vertices
    normals  : (V, 3) float64 — vertex normals (optional, may be empty)
    """
    kind:     str        = "isosurface"
    vertices: np.ndarray = field(default_factory=lambda: np.zeros((0, 3), dtype=np.float64))
    faces:    np.ndarray = field(default_factory=lambda: np.zeros((0, 3), dtype=np.int32))
    normals:  np.ndarray = field(default_factory=lambda: np.zeros((0, 3), dtype=np.float64))


# IO dispatch map — used by loaders to reconstruct the correct subclass
ISOCONTOUR_KIND_MAP: dict[str, type[IsocontourResult]] = {
    "isopoint":   IsopointResult,
    "isoline":    IsolineResult,
    "isosurface": IsosurfaceResult,
}
