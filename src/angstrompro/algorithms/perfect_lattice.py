"""Unified Perfect Lattice 2D registration and its shared input contract."""

from __future__ import annotations

import numpy as np

from angstrompro.core.data.annotation_data import PointSetData
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    AnnotationSpec,
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

from .lattice.correction import perfect_lattice_hexagonal, perfect_lattice_square


# Add future corrections with the same contract here; this also supplies the
# schema's dropdown choices. Calculations themselves are not registered entries.
_LATTICE_CORRECTIONS = {
    "hexagonal": perfect_lattice_hexagonal,
    "square": perfect_lattice_square,
}

_SCHEMA = ProcessSchema(
    inputs=[
        InputSpec(
            name="data",
            type_id="uds",
            label="Real-space Image Stack",
            description="Real-space UDS (layers × rows × cols). Bragg peaks use "
            "shifted-FFT pixel coordinates but remain annotations on their "
            "existing owner; workflows may bind that owner separately.",
            ndim=3,
        ),
    ],
    outputs=[
        OutputSpec(
            type_id="uds",
            ndim=3,
            label="Image Stack",
            description="Affine-corrected real-space image stack.",
        ),
    ],
    params=[
        ParameterSpec(
            name="lattice_type",
            type=str,
            default="hexagonal",
            label="Lattice type",
            choices=list(_LATTICE_CORRECTIONS),
            description="Hexagonal: equal Q-vector magnitudes at 60 degrees "
            "(Q2 clockwise from Q1). Square: equal magnitudes at 90 degrees.",
        ),
        ParameterSpec(
            name="interpolate_method",
            type=str,
            default="bilinear",
            label="Interpolation",
            description="Pixel interpolation method used during the affine remap.",
            choices=["bilinear"],
        ),
        ParameterSpec(
            name="pad_method",
            type=str,
            default="constant",
            label="Padding",
            description="Edge padding mode passed to numpy.pad.",
            choices=["constant", "reflect", "edge", "wrap", "symmetric"],
        ),
    ],
    annotations=[
        AnnotationSpec("bragg_peaks", "bragg_peaks", "point_set", required=True),
    ],
)


def _read_bragg_peaks(annotations: dict | None):
    peaks = (annotations or {}).get("bragg_peaks")
    if peaks is None:
        raise ValueError(
            "Perfect Lattice 2D requires a 'bragg_peaks' annotation with at least "
            "2 points. Set Bragg Peaks in the viewer or bind an annotation source "
            "in the workflow."
        )
    if not isinstance(peaks, PointSetData):
        raise ValueError("The 'bragg_peaks' annotation must be a point set.")
    coords = np.asarray(peaks.coords)
    if coords.ndim != 2 or coords.shape[1] != 2 or coords.shape[0] < 2:
        raise ValueError(
            "Perfect Lattice 2D requires at least 2 Bragg peaks [row, col]."
        )
    if not np.isfinite(coords[:2]).all():
        raise ValueError("The first 2 Bragg peaks must have finite coordinates.")
    # The algorithms take (column, row); annotation coordinates are (row, column).
    return (
        float(coords[0, 1]),
        float(coords[0, 0]),
        float(coords[1, 1]),
        float(coords[1, 0]),
    )


@register_process(
    name="spatial.perfect_lattice_2d",
    label="Perfect Lattice 2D",
    category="Lattice & Registration",
    schema=_SCHEMA,
    description="Correct a real-space image stack using the first two bragg_peaks "
    "points in shifted-FFT pixel coordinates. Choose hexagonal or square lattice; "
    "for hexagonal, Q2 must be clockwise from Q1 at approximately 60 degrees.",
)
def perfect_lattice(
    inputs: dict, params: dict, *, annotations: dict | None = None
) -> UdsDataStru:
    src = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(
            f"spatial.perfect_lattice_2d requires ndim=3; got {src.data.shape}."
        )
    values = {**_SCHEMA.defaults(), **params}
    # Enforce the same choices for headless/workflow callers as for GUI controls.
    for spec in _SCHEMA.params:
        value = values[spec.name]
        if not isinstance(value, str) or value not in spec.choices:
            raise ValueError(
                f"{spec.label} must be one of {spec.choices}; got {value!r}."
            )
    peaks = _read_bragg_peaks(annotations)
    correction = _LATTICE_CORRECTIONS[values["lattice_type"]]
    return correction(src, *peaks, values["interpolate_method"], values["pad_method"])
