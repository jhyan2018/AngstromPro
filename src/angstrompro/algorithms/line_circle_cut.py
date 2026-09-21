# -*- coding: utf-8 -*-
"""
Line-cut and circle-cut processes for AngstromPro.

Registered processes
--------------------
    spectral.line_cut
        Extract intensity along a straight line through a 3-D stack.
        Requires a 'line_cut' annotation (LineData, p1/p2 in row/col).
        Output is a 2-D UDS (ndim=2):
            layer_vs_distance -> (L, N): axis[0]=energy, axis[1]=distance
            distance_vs_layer -> (N, L): axis[0]=distance, axis[1]=energy
        Name suffix: _lc

    spectral.circle_cut
        Extract intensity along a circular arc through a 3-D stack.
        Requires a 'circle_cut_points' annotation (PointSetData, 2 points:
        [0] = centre, [1] = edge point that defines the radius).
        Output is a 2-D UDS (ndim=2):
            layer_vs_theta -> (L, N): axis[0]=energy, axis[1]=theta in [0, 2pi]
            theta_vs_layer -> (N, L): axis[0]=theta, axis[1]=energy
        Name suffix: _cc
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)
from angstrompro.core.processes.param_schema import AnnotationSpec


# ---------------------------------------------------------------------------
# Internal helpers – ported from ScienceY/ImageProcess/LineAndCircleCut.py
# ---------------------------------------------------------------------------

_MAP_COORDINATES = None


def _map_coordinates(*args, **kwargs):
    """Load SciPy interpolation only when a cut is evaluated."""
    global _MAP_COORDINATES
    if _MAP_COORDINATES is None:
        from scipy.ndimage import map_coordinates
        _MAP_COORDINATES = map_coordinates
    return _MAP_COORDINATES(*args, **kwargs)


class _LineCut:
    """Compute intensity along a straight line segment."""

    def __init__(self, data3d, x1, y1, x2, y2, order=1, num_points=None):
        self.data3d = data3d
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.order = order
        dist = np.hypot(x2 - x1, y2 - y1)
        self.num_points = num_points if num_points else int(np.ceil(dist / np.sqrt(2))) + 1

    def bresenham_line(self):
        x1, y1, x2, y2 = int(self.x1), int(self.y1), int(self.x2), int(self.y2)
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx, sy = (1 if x1 < x2 else -1), (1 if y1 < y2 else -1)
        err = dx - dy
        points = []
        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
        points = np.array(points)
        values = np.array([self.data3d[:, y, x] for x, y in points])  # (N, L)
        return values.T, points  # (L, N)

    def linecut_interpolated(self):
        xc = np.linspace(self.x1, self.x2, self.num_points)
        yc = np.linspace(self.y1, self.y2, self.num_points)
        values = np.zeros((self.data3d.shape[0], self.num_points))
        for i in range(self.data3d.shape[0]):
            values[i] = _map_coordinates(self.data3d[i], [yc, xc], order=self.order)
        return values  # (L, N)

    def linecut_with_width_average(self, W):
        values = self.linecut_interpolated()                   # (L, N)
        xc = np.linspace(self.x1, self.x2, self.num_points)
        yc = np.linspace(self.y1, self.y2, self.num_points)
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        length = np.hypot(dx, dy)
        if length == 0:
            return values
        perp_dx = -dy / length
        perp_dy = dx / length
        n_perp = int(W)
        offsets = np.linspace(-W / 2, W / 2, n_perp)
        averaged = np.zeros_like(values)
        for i in range(self.num_points):
            px = xc[i] + offsets * perp_dx
            py = yc[i] + offsets * perp_dy
            for j in range(self.data3d.shape[0]):
                averaged[j, i] = _map_coordinates(
                    self.data3d[j], [py, px], order=self.order).mean()
        return averaged  # (L, N)


class _CircleCut:
    """Compute intensity along a circular arc."""

    def __init__(self, data3d, cx, cy, ex, ey, order=1, num_points=None):
        self.data3d = data3d
        self.cx, self.cy = cx, cy
        radius = np.hypot(ex - cx, ey - cy)
        self.radius = radius
        self.order = order
        self.num_points = num_points if num_points else int(2 * np.pi * radius)

    def circlecut_interpolated(self):
        theta = np.linspace(0, 2 * np.pi, self.num_points)
        xc = self.cx + self.radius * np.cos(theta)
        yc = self.cy + self.radius * np.sin(theta)
        values = np.zeros((self.data3d.shape[0], self.num_points))
        for i in range(self.data3d.shape[0]):
            values[i] = _map_coordinates(self.data3d[i], [yc, xc], order=self.order)
        return values  # (L, N)

    def circlecut_with_width_average(self, W):
        values = self.circlecut_interpolated()  # (L, N)
        theta = np.linspace(0, 2 * np.pi, self.num_points)
        xc = self.cx + self.radius * np.cos(theta)
        yc = self.cy + self.radius * np.sin(theta)
        n_perp = int(W)
        offsets = np.linspace(-W / 2, W / 2, n_perp)
        averaged = np.zeros_like(values)
        for i in range(self.num_points):
            dx = xc[i] - self.cx
            dy = yc[i] - self.cy
            length = np.hypot(dx, dy)
            if length == 0:
                averaged[:, i] = values[:, i]
                continue
            rdx, rdy = dx / length, dy / length
            px = xc[i] + offsets * rdx
            py = yc[i] + offsets * rdy
            for j in range(self.data3d.shape[0]):
                averaged[j, i] = _map_coordinates(
                    self.data3d[j], [py, px], order=self.order).mean()
        return averaged  # (L, N)


_OUT_2D = [OutputSpec(
    type_id="uds",
    ndim=2,
    label="Curve Stack",
    description="ndim=2 UDS (curves × points).",
)]


def build_point_spectra_uds(
    src: UdsDataStru,
    points,
    *,
    name: str | None = None,
) -> UdsDataStru:
    """Build a temporary curve stack from spatial points in a 3-D UDS.

    ``points`` are ``(row, col)`` coordinates.  Each output row is the
    spectrum through every layer at one point, so the final axis is always
    the source layer/energy axis used by CurveStackViewer.
    """
    data = np.asarray(src.data)
    if data.ndim != 3:
        raise ValueError(
            f"Point spectra require 3-D data; got {data.ndim}-D data.")

    coords = np.asarray(points, dtype=float)
    if coords.ndim != 2 or coords.shape[1] != 2 or len(coords) == 0:
        raise ValueError("Point spectra require at least one (row, col) point.")
    if not np.all(np.isfinite(coords)):
        raise ValueError("Point coordinates must be finite.")

    # ImageStackViewer annotations use pixel coordinates.  Keep preview
    # sampling consistent with the permanent point annotations by selecting
    # the containing integer pixel.
    rows = coords[:, 0].astype(int)
    cols = coords[:, 1].astype(int)
    height, width = data.shape[-2:]
    if (np.any(rows < 0) or np.any(rows >= height)
            or np.any(cols < 0) or np.any(cols >= width)):
        raise ValueError("One or more picked points lie outside the image.")

    spectra = np.real(data[:, rows, cols].T).astype(np.float64, copy=False)
    if src.axes and len(src.axes[0].values) == data.shape[0]:
        layer_axis = copy.deepcopy(src.axes[0])
    else:
        layer_axis = Axis(
            values=np.arange(data.shape[0], dtype=float),
            label="Layer",
            axis_type=AxisType.INDEX,
        )
    point_axis = Axis(
        values=np.arange(len(coords), dtype=float),
        label="Point",
        axis_type=AxisType.INDEX,
        ticks={float(i): f"P{i}" for i in range(len(coords))},
    )
    return UdsDataStru(
        name=name or src.name + "_points",
        data=spectra,
        axes=[point_axis, layer_axis],
        info=copy.deepcopy(src.info),
    )


def build_line_cut_uds(
    src: UdsDataStru,
    p1: tuple[float, float],
    p2: tuple[float, float],
    *,
    orientation: str = "layer_vs_distance",
    method: str = "interpolated",
    interpolation_order: int = 1,
    line_width: int = 1,
    num_points: int = 0,
    name: str | None = None,
    copy_process_history: bool = True,
) -> UdsDataStru:
    """Build the line-cut UDS used by both preview and registered process.

    Points use the annotation convention ``(row, col)``.  Keeping UDS
    construction here ensures that the live preview and permanent process
    output use identical sampling, axes, and orientation rules.
    """
    data = np.asarray(src.data)
    if data.ndim != 3:
        raise ValueError(f"Line cut requires 3-D data; got {data.ndim}-D data.")
    if orientation not in {"layer_vs_distance", "distance_vs_layer"}:
        raise ValueError(f"Unknown line-cut orientation: {orientation!r}")
    if method not in {"interpolated", "bresenham"}:
        raise ValueError(f"Unknown line-cut sampling method: {method!r}")
    if not 0 <= int(interpolation_order) <= 3:
        raise ValueError("Interpolation order must be between 0 and 3.")
    if int(line_width) < 1:
        raise ValueError("Line width must be at least 1 pixel.")
    if int(num_points) < 0:
        raise ValueError("Number of points cannot be negative.")

    y1, x1 = map(float, p1)
    y2, x2 = map(float, p2)
    if not all(np.isfinite((x1, y1, x2, y2))):
        raise ValueError("Line-cut endpoints must be finite.")

    cut = _LineCut(
        data, x1, y1, x2, y2,
        order=int(interpolation_order),
        num_points=int(num_points) or None,
    )
    if method == "bresenham":
        values, _ = cut.bresenham_line()
    elif int(line_width) > 1:
        values = cut.linecut_with_width_average(int(line_width))
    else:
        values = cut.linecut_interpolated()
    values = np.real(values).astype(np.float64, copy=False)  # (L, N)

    if src.axes and len(src.axes[0].values) == data.shape[0]:
        layer_axis = copy.deepcopy(src.axes[0])
    else:
        layer_axis = Axis(
            values=np.arange(data.shape[0], dtype=float),
            label="Layer",
            axis_type=AxisType.INDEX,
        )
    distance = np.hypot(x2 - x1, y2 - y1)
    distance_axis = Axis(
        values=np.linspace(0.0, distance, values.shape[1]),
        label="Distance",
        units="px",
    )

    if orientation == "layer_vs_distance":
        output_data = values
        axes = [layer_axis, distance_axis]
    else:
        output_data = values.T
        axes = [distance_axis, layer_axis]

    return UdsDataStru(
        name=name or src.name + "_lc",
        data=output_data,
        axes=axes,
        info=copy.deepcopy(src.info),
        proc_history=(
            [copy.deepcopy(record) for record in src.proc_history]
            if copy_process_history else []
        ),
    )


def build_circle_cut_uds(
    src: UdsDataStru,
    centre: tuple[float, float],
    edge: tuple[float, float],
    *,
    orientation: str = "layer_vs_theta",
    interpolation_order: int = 1,
    line_width: int = 1,
    num_points: int = 0,
    name: str | None = None,
    copy_process_history: bool = True,
) -> UdsDataStru:
    """Build the circle-cut UDS used by preview and registered process.

    ``centre`` and ``edge`` use the annotation convention ``(row, col)``.
    The edge point sets the radius; sampling begins on the positive X side
    and covers a complete circle from 0 to 2π.
    """
    data = np.asarray(src.data)
    if data.ndim != 3:
        raise ValueError(
            f"Circle cut requires 3-D data; got {data.ndim}-D data.")
    if orientation not in {"layer_vs_theta", "theta_vs_layer"}:
        raise ValueError(f"Unknown circle-cut orientation: {orientation!r}")
    if not 0 <= int(interpolation_order) <= 3:
        raise ValueError("Interpolation order must be between 0 and 3.")
    if int(line_width) < 1:
        raise ValueError("Radial width must be at least 1 pixel.")
    if int(num_points) < 0:
        raise ValueError("Number of points cannot be negative.")

    cy, cx = map(float, centre)
    ey, ex = map(float, edge)
    if not all(np.isfinite((cx, cy, ex, ey))):
        raise ValueError("Circle centre and edge points must be finite.")
    if np.hypot(ex - cx, ey - cy) == 0:
        raise ValueError("Circle centre and edge points must be different.")

    cut = _CircleCut(
        data, cx, cy, ex, ey,
        order=int(interpolation_order),
        num_points=int(num_points) or None,
    )
    if int(line_width) > 1:
        values = cut.circlecut_with_width_average(int(line_width))
    else:
        values = cut.circlecut_interpolated()
    values = np.real(values).astype(np.float64, copy=False)  # (L, N)

    if src.axes and len(src.axes[0].values) == data.shape[0]:
        layer_axis = copy.deepcopy(src.axes[0])
    else:
        layer_axis = Axis(
            values=np.arange(data.shape[0], dtype=float),
            label="Layer",
            axis_type=AxisType.INDEX,
        )
    theta_axis = Axis(
        values=np.linspace(0.0, 2 * np.pi, values.shape[1]),
        label="θ",
        units="rad",
    )

    if orientation == "layer_vs_theta":
        output_data = values
        axes = [layer_axis, theta_axis]
    else:
        output_data = values.T
        axes = [theta_axis, layer_axis]

    return UdsDataStru(
        name=name or src.name + "_cc",
        data=output_data,
        axes=axes,
        info=copy.deepcopy(src.info),
        proc_history=(
            [copy.deepcopy(record) for record in src.proc_history]
            if copy_process_history else []
        ),
    )

# ---------------------------------------------------------------------------
# Registered process: spectral.line_cut
# ---------------------------------------------------------------------------

@register_process(
    name        = "spectral.line_cut_2d",
    label       = "Line Cut 2D",
    category    = "Spectroscopy & Profiles",
    schema      = ProcessSchema(
        outputs=_OUT_2D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack to sample along a line.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "orientation",
                type        = str,
                default     = "layer_vs_distance",
                label       = "Orientation",
                description = (
                    "layer_vs_distance: shape (L, N) — axis[0]=energy, axis[1]=distance. "
                    "distance_vs_layer: shape (N, L) — axis[0]=distance, axis[1]=energy."
                ),
                choices     = ["layer_vs_distance", "distance_vs_layer"],
            ),
            ParameterSpec(
                name        = "method",
                type        = str,
                default     = "interpolated",
                label       = "Sampling method",
                description = (
                    "interpolated: scipy map_coordinates (order 0–3). "
                    "bresenham: integer pixel walk, no interpolation."
                ),
                choices     = ["interpolated", "bresenham"],
            ),
            ParameterSpec(
                name        = "interpolation_order",
                type        = int,
                default     = 1,
                label       = "Interpolation order",
                description = "scipy map_coordinates order: 0=nearest, 1=bilinear, 2=biquadratic, 3=bicubic. Ignored when method=bresenham.",
                min         = 0,
                max         = 3,
            ),
            ParameterSpec(
                name        = "line_width",
                type        = int,
                default     = 1,
                label       = "Line width (px)",
                description = "Average over this many perpendicular pixels (1 = single line).",
                min         = 1,
            ),
            ParameterSpec(
                name        = "num_points",
                type        = int,
                default     = 0,
                label       = "Number of points (0=auto)",
                description = "Spatial sampling points along the line. 0 = auto (ceil(dist/√2)+1).",
                min         = 0,
            ),
        ],
        annotations=[
            AnnotationSpec(
                name     = "line_cut",
                role     = "line_cut",
                type_id  = "line",
                required = True,
            ),
        ],
    ),
    description = (
        "Sample a 3-D stack along the line defined by the 'line_cut' annotation. "
        "Output is a 2-D UDS: either (L, N) with axis[0]=energy, axis[1]=distance, "
        "or transposed (N, L). Supports interpolated and Bresenham sampling."
    ),
)
def line_cut(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]
    ann = (annotations or {}).get("line_cut")

    if ann is None or not (hasattr(ann, "p1") and hasattr(ann, "p2")):
        raise ValueError(
            "spectral.line_cut_2d: 'line_cut' annotation is missing or invalid. "
            "Set a line annotation on the item first."
        )

    return build_line_cut_uds(
        src,
        ann.p1,
        ann.p2,
        orientation=params["orientation"],
        method=params["method"],
        interpolation_order=params["interpolation_order"],
        line_width=params["line_width"],
        num_points=params["num_points"],
    )


# ---------------------------------------------------------------------------
# Registered process: spectral.circle_cut
# ---------------------------------------------------------------------------

@register_process(
    name        = "spectral.circle_cut_2d",
    label       = "Circle Cut 2D",
    category    = "Spectroscopy & Profiles",
    schema      = ProcessSchema(
        outputs=_OUT_2D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack to sample along a circular arc.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "orientation",
                type        = str,
                default     = "layer_vs_theta",
                label       = "Orientation",
                description = (
                    "layer_vs_theta: shape (L, N) — axis[0]=energy, axis[1]=θ. "
                    "theta_vs_layer: shape (N, L) — axis[0]=θ, axis[1]=energy."
                ),
                choices     = ["layer_vs_theta", "theta_vs_layer"],
            ),
            ParameterSpec(
                name        = "interpolation_order",
                type        = int,
                default     = 1,
                label       = "Interpolation order",
                description = "scipy map_coordinates order: 0=nearest, 1=bilinear, 2=biquadratic, 3=bicubic.",
                min         = 0,
                max         = 3,
            ),
            ParameterSpec(
                name        = "line_width",
                type        = int,
                default     = 1,
                label       = "Radial width (px)",
                description = "Average over this many radial pixels (1 = single circle).",
                min         = 1,
            ),
            ParameterSpec(
                name        = "num_points",
                type        = int,
                default     = 0,
                label       = "Number of points (0=auto)",
                description = "Angular sampling points. 0 = auto (floor(2π·radius)).",
                min         = 0,
            ),
        ],
        annotations=[
            AnnotationSpec(
                name     = "circle_cut_points",
                role     = "circle_cut_points",
                type_id  = "point_set",
                required = True,
            ),
        ],
    ),
    description = (
        "Sample a 3-D stack along the circle defined by two 'circle_cut_points' "
        "annotations: point [0] is the centre, point [1] is the radius endpoint. "
        "Output is a 2-D UDS: either (L, N) with axis[0]=energy, axis[1]=θ, "
        "or transposed (N, L)."
    ),
)
def circle_cut(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]
    ann = (annotations or {}).get("circle_cut_points")

    if ann is None or not hasattr(ann, "coords"):
        raise ValueError(
            "spectral.circle_cut_2d: 'circle_cut_points' annotation is missing or invalid. "
            "Set two points (centre + edge) on the item first."
        )
    if ann.coords.shape[0] < 2:
        raise ValueError(
            f"spectral.circle_cut_2d: need exactly 2 points (centre + edge); "
            f"got {ann.coords.shape[0]}."
        )

    return build_circle_cut_uds(
        src,
        ann.coords[0],
        ann.coords[1],
        orientation=params["orientation"],
        interpolation_order=params["interpolation_order"],
        line_width=params["line_width"],
        num_points=params["num_points"],
    )
