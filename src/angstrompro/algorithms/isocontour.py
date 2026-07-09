# -*- coding: utf-8 -*-
"""
Created on Wed Jul 09 2026

@author: jiahaoYan

Isocontour extraction processes for UdsDataStru.

Convention
----------
axis[0] is always the "layer" axis (mathematically generic — no physics meaning
attached here).  The remaining axes are the spatial axes used for extraction.
Higher-level processes (e.g. in myplugin) may interpret layer_index as band
index, spin channel, orbital, etc.

Registered processes
--------------------
  isocontour.isopoint_1D
      ndim=2  (layer, x)
      For each layer: find x positions where f(x) = level.
      Appends one IsopointResult per (layer, level).

  isocontour.isoline_2D
      ndim=3  (layer, y, x)
      For each layer: extract iso-contour polylines where f(y,x) = level.
      Appends one IsolineResult per (layer, level).

  isocontour.isosurface_3D
      ndim=4  (layer, z, y, x)
      For each layer: extract iso-surface mesh where f(z,y,x) = level.
      Appends one IsosurfaceResult per (layer, level).

Parameters (shared)
-------------------
  levels        str   comma-separated float values, e.g. "0.0, 0.5, -0.5"
  interpolate   bool  upsample spatial axes before extraction
  interp_factor int   upsampling factor when interpolate=True (default 4)
  method        str   algorithm (depends on process — see individual docs)
"""
from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.data.isocontour_data import (
    IsopointResult,
    IsolineResult,
    IsosurfaceResult,
)
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_levels(levels_str: str) -> list[float]:
    parts = [s.strip() for s in levels_str.split(",") if s.strip()]
    if not parts:
        raise ValueError(
            f"'levels' must be one or more comma-separated numbers, got: {levels_str!r}")
    try:
        return [float(p) for p in parts]
    except ValueError as exc:
        raise ValueError(
            f"Could not parse levels {levels_str!r} — use scientific notation "
            f"e.g. '0.0, 1.5e-9, -0.5'") from exc


def _copy_uds(src: UdsDataStru, suffix: str) -> UdsDataStru:
    dst = copy.copy(src)
    dst.name         = src.name + suffix
    dst.axes         = [copy.copy(ax) for ax in src.axes]
    dst.info         = dict(src.info)
    dst.landmarks    = dict(src.landmarks)
    dst.isocontours  = list(src.isocontours)
    dst.proc_history = [copy.copy(r) for r in src.proc_history]
    return dst


def _upsample_1d(data: np.ndarray, ax: np.ndarray,
                 factor: int) -> tuple[np.ndarray, np.ndarray]:
    from scipy.interpolate import interp1d
    x_new = np.linspace(ax[0], ax[-1], len(ax) * factor)
    return interp1d(ax, data, kind="cubic", assume_sorted=True)(x_new), x_new


def _upsample_2d(data: np.ndarray, ax0: np.ndarray, ax1: np.ndarray,
                 factor: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from scipy.interpolate import RectBivariateSpline
    y_new = np.linspace(ax0[0], ax0[-1], len(ax0) * factor)
    x_new = np.linspace(ax1[0], ax1[-1], len(ax1) * factor)
    return RectBivariateSpline(ax0, ax1, data)(y_new, x_new), y_new, x_new


def _upsample_3d(data: np.ndarray, ax0: np.ndarray, ax1: np.ndarray, ax2: np.ndarray,
                 factor: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    from scipy.interpolate import RegularGridInterpolator
    z_new = np.linspace(ax0[0], ax0[-1], len(ax0) * factor)
    y_new = np.linspace(ax1[0], ax1[-1], len(ax1) * factor)
    x_new = np.linspace(ax2[0], ax2[-1], len(ax2) * factor)
    rgi   = RegularGridInterpolator((ax0, ax1, ax2), data, method="linear")
    ZZ, YY, XX = np.meshgrid(z_new, y_new, x_new, indexing="ij")
    pts = np.stack([ZZ.ravel(), YY.ravel(), XX.ravel()], axis=-1)
    return rgi(pts).reshape(len(z_new), len(y_new), len(x_new)), z_new, y_new, x_new


# ---------------------------------------------------------------------------
# Shared param specs
# ---------------------------------------------------------------------------

_LEVELS_PARAM = ParameterSpec(
    name="levels", type=str, default="0.0",
    label="Iso-levels",
    description=(
        "Comma-separated list of iso-values to extract, e.g. '0.0, 0.5, -0.5'. "
        "Scientific notation supported: '1.22e-9'."
    ),
)

_INTERP_PARAMS = [
    ParameterSpec(
        name="interpolate", type=bool, default=False,
        label="Interpolate before extraction",
        description="Upsample the spatial axes before extraction for smoother results.",
    ),
    ParameterSpec(
        name="interp_factor", type=int, default=4, min=2, max=16,
        label="Interpolation factor",
        description="Spatial grid upsampling factor when interpolate=True.",
    ),
]

_OUT = OutputSpec(type_id="uds", label="UDS + isocontours",
                  description="Input UDS with isocontour results appended.")


# ---------------------------------------------------------------------------
# isocontour.isopoint_1D   ndim=2  (layer, x)
# ---------------------------------------------------------------------------

@register_process(
    name        = "isocontour.isopoint_1D",
    label       = "Iso-point 1-D",
    category    = "Isocontour",
    description = (
        "Find x positions where f(x) = level, for each layer in a 2-D UDS.\n\n"
        "Input shape: (n_layers, nx)  —  axis[0] = layer, axis[1] = x.\n\n"
        "Appends one IsopointResult per (layer_index, level) to uds.isocontours. "
        "Output name: input_name + '_isoc'."
    ),
    schema=ProcessSchema(
        inputs  = [InputSpec(name="data", type_id="uds", ndim=2, label="2-D data (layer, x)")],
        outputs = [_OUT],
        params  = [_LEVELS_PARAM] + _INTERP_PARAMS,
    ),
)
def isopoint_1d(inputs: dict, params: dict,
                *, annotations: dict | None = None) -> UdsDataStru:
    src    = inputs["data"]
    levels = _parse_levels(params["levels"])
    interp = bool(params["interpolate"])
    factor = int(params["interp_factor"])

    raw_data = src.data.astype(np.float64)          # (n_layers, nx)
    ax_x     = src.axes[1].values.astype(np.float64)

    dst = _copy_uds(src, "_isoc")

    for layer_i in range(raw_data.shape[0]):
        data = raw_data[layer_i]
        ax   = ax_x
        if interp:
            data, ax = _upsample_1d(data, ax, factor)

        for level in levels:
            diff  = data - level
            cross = np.where(np.diff(np.sign(diff)) != 0)[0]
            pts   = []
            for i in cross:
                d0, d1 = diff[i], diff[i + 1]
                t = d0 / (d0 - d1)
                pts.append(ax[i] + t * (ax[i + 1] - ax[i]))
            dst.isocontours.append(IsopointResult(
                level       = level,
                method      = "linear_interp",
                source_axes = (1,),
                layer_index = layer_i,
                points      = np.array(pts, dtype=np.float64),
            ))

    return dst


# ---------------------------------------------------------------------------
# isocontour.isoline_2D    ndim=3  (layer, y, x)
# ---------------------------------------------------------------------------

@register_process(
    name        = "isocontour.isoline_2D",
    label       = "Iso-line 2-D",
    category    = "Isocontour",
    description = (
        "Extract iso-contour polylines where f(y,x) = level, for each layer in a 3-D UDS.\n\n"
        "Input shape: (n_layers, ny, nx)  —  axis[0] = layer, axis[1] = y, axis[2] = x.\n\n"
        "Methods:\n"
        "  'marching_squares' (default) — sub-pixel accurate via skimage\n"
        "  'contour'                    — matplotlib contour path extraction\n\n"
        "Appends one IsolineResult per (layer_index, level) to uds.isocontours. "
        "Output name: input_name + '_isoc'."
    ),
    schema=ProcessSchema(
        inputs  = [InputSpec(name="data", type_id="uds", ndim=3, label="3-D data (layer, y, x)")],
        outputs = [_OUT],
        params  = [
            _LEVELS_PARAM,
            ParameterSpec(
                name="method", type=str, default="marching_squares",
                label="Method",
                choices=["marching_squares", "contour"],
                description="Algorithm for iso-line extraction.",
            ),
        ] + _INTERP_PARAMS,
    ),
)
def isoline_2d(inputs: dict, params: dict,
               *, annotations: dict | None = None) -> UdsDataStru:
    src    = inputs["data"]
    levels = _parse_levels(params["levels"])
    method = params["method"]
    interp = bool(params["interpolate"])
    factor = int(params["interp_factor"])

    raw_data = src.data.astype(np.float64)           # (n_layers, ny, nx)
    ax_y     = src.axes[1].values.astype(np.float64)
    ax_x     = src.axes[2].values.astype(np.float64)

    dst = _copy_uds(src, "_isoc")

    for layer_i in range(raw_data.shape[0]):
        data = raw_data[layer_i]
        ay, ax = ax_y, ax_x
        if interp:
            data, ay, ax = _upsample_2d(data, ay, ax, factor)

        for level in levels:
            contours = _extract_isolines(data, ay, ax, level, method)
            dst.isocontours.append(IsolineResult(
                level       = level,
                method      = method,
                source_axes = (1, 2),
                layer_index = layer_i,
                contours    = contours,
            ))

    return dst


def _extract_isolines(data: np.ndarray, ax0: np.ndarray, ax1: np.ndarray,
                      level: float, method: str) -> list[np.ndarray]:
    if method == "marching_squares":
        try:
            from skimage.measure import find_contours
        except ImportError:
            raise ImportError(
                "scikit-image is required for method='marching_squares'. "
                "Install with: pip install scikit-image")
        raw = find_contours(data, level=level)
        result = []
        for c in raw:
            rows = np.interp(c[:, 0], np.arange(len(ax0)), ax0)
            cols = np.interp(c[:, 1], np.arange(len(ax1)), ax1)
            result.append(np.column_stack([cols, rows]))   # (N, 2): x, y
        return result

    elif method == "contour":
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        cs = ax.contour(ax1, ax0, data, levels=[level])
        result = []
        for collection in cs.collections:
            for path in collection.get_paths():
                result.append(path.vertices.copy())
        plt.close(fig)
        return result

    else:
        raise ValueError(f"Unknown method: {method!r}. "
                         f"Choose 'marching_squares' or 'contour'.")


# ---------------------------------------------------------------------------
# isocontour.isosurface_3D  ndim=4  (layer, z, y, x)
# ---------------------------------------------------------------------------

@register_process(
    name        = "isocontour.isosurface_3D",
    label       = "Iso-surface 3-D",
    category    = "Isocontour",
    description = (
        "Extract a triangulated iso-surface where f(z,y,x) = level, "
        "for each layer in a 4-D UDS.\n\n"
        "Input shape: (n_layers, nz, ny, nx)  —  axis[0] = layer, "
        "axis[1] = z, axis[2] = y, axis[3] = x.\n\n"
        "Method: 'marching_cubes' (skimage) — sub-voxel accurate triangulation.\n\n"
        "Appends one IsosurfaceResult per (layer_index, level) to uds.isocontours. "
        "Output name: input_name + '_isoc'."
    ),
    schema=ProcessSchema(
        inputs  = [InputSpec(name="data", type_id="uds", ndim=4,
                             label="4-D data (layer, z, y, x)")],
        outputs = [_OUT],
        params  = [
            _LEVELS_PARAM,
            ParameterSpec(
                name="method", type=str, default="marching_cubes",
                label="Method",
                choices=["marching_cubes"],
                description="Algorithm for iso-surface extraction.",
            ),
        ] + _INTERP_PARAMS,
    ),
)
def isosurface_3d(inputs: dict, params: dict,
                  *, annotations: dict | None = None) -> UdsDataStru:
    src    = inputs["data"]
    levels = _parse_levels(params["levels"])
    interp = bool(params["interpolate"])
    factor = int(params["interp_factor"])

    try:
        from skimage.measure import marching_cubes
    except ImportError:
        raise ImportError(
            "scikit-image is required for isocontour.isosurface_3D. "
            "Install with: pip install scikit-image")

    raw_data = src.data.astype(np.float64)           # (n_layers, nz, ny, nx)
    ax_z     = src.axes[1].values.astype(np.float64)
    ax_y     = src.axes[2].values.astype(np.float64)
    ax_x     = src.axes[3].values.astype(np.float64)

    dst = _copy_uds(src, "_isoc")

    for layer_i in range(raw_data.shape[0]):
        data = raw_data[layer_i]
        az, ay, ax = ax_z, ax_y, ax_x
        if interp:
            data, az, ay, ax = _upsample_3d(data, az, ay, ax, factor)

        spacing = (
            float(np.abs(az[1] - az[0])) if len(az) > 1 else 1.0,
            float(np.abs(ay[1] - ay[0])) if len(ay) > 1 else 1.0,
            float(np.abs(ax[1] - ax[0])) if len(ax) > 1 else 1.0,
        )

        for level in levels:
            verts, faces, normals, _ = marching_cubes(data, level=level, spacing=spacing)
            verts[:, 0] += az[0]
            verts[:, 1] += ay[0]
            verts[:, 2] += ax[0]
            dst.isocontours.append(IsosurfaceResult(
                level       = level,
                method      = "marching_cubes",
                source_axes = (1, 2, 3),
                layer_index = layer_i,
                vertices    = verts.astype(np.float64),
                faces       = faces.astype(np.int32),
                normals     = normals.astype(np.float64),
            ))

    return dst
