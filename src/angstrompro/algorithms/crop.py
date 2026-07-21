# -*- coding: utf-8 -*-
"""
Crop a 3-D stack to a rectangular spatial region.

The crop region is read from the "interest_region" annotation (RegionData with
pixel-index bounds) stored on the workspace item.  The layer axis (axis 0) is
always preserved; axes 1 (rows) and 2 (cols) are trimmed.

Registered processes
--------------------
    spatial.crop2d_square
        Crop to a square region with an even side length.
        Shrinks the annotated region to the largest square with an even pixel
        count, anchored at the top-left corner.

    spatial.crop2d   (commented out — ImageStackViewer requires square data)
        Crop to the annotated region without forcing square/even.
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.data.annotation_data import RegionData
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ProcessSchema,
    register_process,
)
from angstrompro.core.processes.param_schema import AnnotationSpec

# ---------------------------------------------------------------------------
# Shared schema
# ---------------------------------------------------------------------------

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

_ANNOTATION = AnnotationSpec(
    name     = "interest_region",
    role     = "interest_region",
    type_id  = "region",
    required = True,
)

_SCHEMA = ProcessSchema(
    outputs=_OUT_3D,
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "3D Stack",
            description = "UdsDataStru with ndim=3 (layers × rows × cols).",
            ndim        = 3,
        ),
    ],
    annotations=[_ANNOTATION],
)


# ---------------------------------------------------------------------------
# Shared implementation
# ---------------------------------------------------------------------------

def _do_crop(src: UdsDataStru, r0: int, r1: int, c0: int, c1: int) -> UdsDataStru:
    """Crop src[:, r0:r1+1, c0:c1+1] and trim axes 1 & 2 accordingly."""
    sr = slice(r0, r1 + 1)
    sc = slice(c0, c1 + 1)

    def _trim_axis(ax: Axis, s: slice) -> Axis:
        vals = ax.values[s].copy()
        return Axis(
            values = vals,
            label  = ax.label,
            units  = ax.units,
            ticks  = {k: v for k, v in ax.ticks.items() if vals[0] <= k <= vals[-1]},
        )

    return UdsDataStru(
        name         = src.name + "_cp",
        data         = src.data[:, sr, sc].copy(),
        axes         = [
            copy.deepcopy(src.axes[0]),
            _trim_axis(src.axes[1], sr),
            _trim_axis(src.axes[2], sc),
        ],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )


def _read_region(annotations: dict | None) -> RegionData:
    if not annotations or "interest_region" not in annotations:
        raise ValueError(
            "spatial.crop_2d requires a 'interest_region' annotation on the input item. "
            "Use Points → 'Set Crop Region from Main' to define it first."
        )
    return annotations["interest_region"]


# ---------------------------------------------------------------------------
# spatial.crop2d  (unregistered — ImageStackViewer requires square data)
# ---------------------------------------------------------------------------

# @register_process(
#     name        = "spatial.crop2d",
#     label       = "Crop 2D",
#     category    = "Spatial",
#     schema      = _SCHEMA,
#     description = "Crop the spatial region of a 3-D stack using the interest_region annotation.",
# )
def crop2d(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"spatial.crop_2d requires ndim=3; got shape {src.data.shape}.")
    region = _read_region(annotations)
    return _do_crop(src, region.row_min, region.row_max, region.col_min, region.col_max)


# ---------------------------------------------------------------------------
# spatial.crop2d_square  (registered)
# ---------------------------------------------------------------------------

@register_process(
    name        = "spatial.crop_square_2d",
    label       = "Crop Square 2D",
    category    = "Geometry & Resampling",
    schema      = _SCHEMA,
    description = "Crop a 3-D stack to a square region with an even side length, "
                  "using the interest_region annotation.",
)
def crop2d_square(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"spatial.crop_square_2d requires ndim=3; got shape {src.data.shape}.")

    region = _read_region(annotations)
    r0, r1 = region.row_min, region.row_max
    c0, c1 = region.col_min, region.col_max

    # Force square and even side length
    side_len = min(r1 - r0, c1 - c0)
    if (side_len + 1) % 2 != 0:
        side_len -= 1
    r1 = r0 + side_len
    c1 = c0 + side_len

    return _do_crop(src, r0, r1, c0, c1)
