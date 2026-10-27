"""Typed, process-generated geometry drawn over UDS image layers.

Image overlays are derived results, not editable workspace annotations.  They
travel with the UDS that owns the image data, so nested UDS payloads (for
example inside SpectrumData) retain their geometry without cross-item links.
Coordinates use image order ``(row, column)`` and are currently stored in
fractional pixel units.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np


@dataclass
class ImageOverlay:
    """Common metadata for one geometric feature on an image layer."""

    kind: str = ""
    overlay_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    layer_index: int = 0
    layer_value: float | None = None
    source_axes: tuple[int, int] = (-2, -1)
    coordinate_space: str = "pixel"
    method: str = ""
    style: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        if self.coordinate_space != "pixel":
            raise ValueError("Image overlays currently require pixel coordinates.")
        if len(self.source_axes) != 2 or self.source_axes[0] == self.source_axes[1]:
            raise ValueError("source_axes must contain two distinct image axes.")


@dataclass
class CircleOverlay(ImageOverlay):
    """Circle with ``center=(row, column)`` and radius in pixels."""

    kind: str = "circle"
    center: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.0


@dataclass
class EllipseOverlay(ImageOverlay):
    """Ellipse in image coordinates, with clockwise rotation in degrees."""

    kind: str = "ellipse"
    center: tuple[float, float] = (0.0, 0.0)
    radius_row: float = 0.0
    radius_column: float = 0.0
    rotation_degrees: float = 0.0


@dataclass
class PolylineOverlay(ImageOverlay):
    """Open or closed polyline with vertices shaped ``(N, 2)`` [row, column]."""

    kind: str = "polyline"
    vertices: np.ndarray = field(
        default_factory=lambda: np.empty((0, 2), dtype=np.float64)
    )
    closed: bool = False


@dataclass
class PointOverlay(ImageOverlay):
    """Derived point geometry shaped ``(N, 2)`` [row, column]."""

    kind: str = "points"
    points: np.ndarray = field(
        default_factory=lambda: np.empty((0, 2), dtype=np.float64)
    )


IMAGE_OVERLAY_KIND_MAP: dict[str, type[ImageOverlay]] = {
    "circle": CircleOverlay,
    "ellipse": EllipseOverlay,
    "polyline": PolylineOverlay,
    "points": PointOverlay,
}


__all__ = [
    "ImageOverlay",
    "CircleOverlay",
    "EllipseOverlay",
    "PolylineOverlay",
    "PointOverlay",
    "IMAGE_OVERLAY_KIND_MAP",
]
