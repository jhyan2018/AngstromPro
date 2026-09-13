"""Convert ordinary raster image files into one-layer UDS image stacks."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from angstrompro.core.data.base import ProcRecord
from angstrompro.core.data.uds_data import (
    Axis,
    AxisType,
    UdsDataStru,
    file_source,
)


_GRAYSCALE_MODES = frozenset({"L", "I", "F", "I;16", "I;16L", "I;16B"})
_LUMA_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float64)


def _grayscale_array(image) -> tuple[np.ndarray, str]:
    """Return a float64 grayscale array and a description of the conversion."""
    if image.mode == "1":
        return (
            np.asarray(image.convert("L"), dtype=np.float64),
            "1-bit grayscale expanded to 0-255",
        )

    if image.mode in _GRAYSCALE_MODES:
        data = np.asarray(image)
        if data.ndim == 2:
            return (
                np.asarray(data, dtype=np.float64),
                f"native grayscale ({image.mode})",
            )

    # RGBA also normalises palette, CMYK, and grayscale-with-alpha images.
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float64)
    alpha = rgba[..., 3:4] / 255.0
    rgb_on_white = rgba[..., :3] * alpha + 255.0 * (1.0 - alpha)
    grayscale = np.sum(rgb_on_white * _LUMA_WEIGHTS, axis=2)
    return grayscale, "BT.601 luma; transparency composited on white"


def load_image_as_uds(path: Path) -> UdsDataStru:
    """Load the first frame of a raster image as shape ``(1, H, W)`` UDS."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    path = Path(path)
    try:
        with Image.open(path) as source:
            source.seek(0)
            original_mode = source.mode
            frame_count = int(getattr(source, "n_frames", 1))
            oriented = ImageOps.exif_transpose(source)
            grayscale, method = _grayscale_array(oriented)
    except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Cannot import {path.name} as an image: {exc}") from exc

    if grayscale.ndim != 2 or grayscale.size == 0:
        raise ValueError(f"{path.name} does not contain a non-empty 2-D image")

    grayscale = np.ascontiguousarray(grayscale, dtype=np.float64)
    height, width = grayscale.shape
    axes = [
        Axis(
            values=np.array([0.0]),
            label="Layer",
            axis_type=AxisType.INDEX,
        ),
        Axis(
            values=np.arange(height, dtype=np.float64),
            label="Y (pixel)",
            units="pixel",
            axis_type=AxisType.SPATIAL_Y,
        ),
        Axis(
            values=np.arange(width, dtype=np.float64),
            label="X (pixel)",
            units="pixel",
            axis_type=AxisType.SPATIAL_X,
        ),
    ]
    info = {
        "source": file_source(path),
        "_image_original_mode": original_mode,
        "_image_width": width,
        "_image_height": height,
        "_image_frame_count": frame_count,
        "_image_imported_frame": 0,
        "_image_origin": "top-left",
        "_image_grayscale_method": method,
    }
    history = [ProcRecord(
        step="Import image as grayscale",
        params={
            "source_file": path.name,
            "original_mode": original_mode,
            "grayscale_method": method,
            "frame": 0,
        },
    )]
    return UdsDataStru(
        name=path.stem,
        data=grayscale[np.newaxis, :, :],
        axes=axes,
        info=info,
        proc_history=history,
    )


__all__ = ["load_image_as_uds"]
