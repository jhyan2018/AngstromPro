# -*- coding: utf-8 -*-
"""
N-fold rotational symmetrisation process for AngstromPro.

Registered processes
--------------------
    spatial.symmetrize
        Average a stack over all N rotations of 360/N degrees, enforcing
        N-fold rotational symmetry.  Typically applied to FFT magnitude maps
        to impose the crystal point-group symmetry.
        Name suffix: _{n_fold}fs  (inserted before _fft if present)
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)


_ROTATE = None


def _rotate(*args, **kwargs):
    global _ROTATE
    if _ROTATE is None:
        from scipy.ndimage import rotate
        _ROTATE = rotate
    return _ROTATE(*args, **kwargs)


def _symmetrize_layer(layer: np.ndarray, n_fold: int) -> np.ndarray:
    acc = np.zeros_like(layer, dtype=np.float64)
    for i in range(n_fold):
        angle = i * (360.0 / n_fold)
        acc += _rotate(layer, angle=angle, reshape=False,
                       order=3, mode="constant", cval=0.0, prefilter=True)
    return acc / n_fold


def _build_name(src_name: str, n_fold: int) -> str:
    suffix = f"_{n_fold}fs"
    if src_name.endswith("_fft"):
        return src_name[:-4] + suffix + "_fft"
    return src_name + suffix


_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]


@register_process(
    name        = "spatial.symmetrize_2d",
    label       = "N-fold Symmetrize 2D",
    category    = "Fourier & Wavevector",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack to symmetrise. Each layer is rotated and averaged independently.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "n_fold",
                type        = int,
                default     = 6,
                label       = "N-fold",
                description = "Number of rotational symmetry folds (e.g. 6 for hexagonal).",
                min         = 2,
            ),
            ParameterSpec(
                name        = "apply_abs",
                type        = bool,
                default     = True,
                label       = "Apply |·| first",
                description = "Take the absolute value of each layer before symmetrising. "
                              "Required for complex FFT data; optional for real-valued maps.",
            ),
        ],
    ),
    description = (
        "Enforce N-fold rotational symmetry by averaging each layer over all "
        "N rotations of 360/N degrees. Typically used on FFT magnitude maps "
        "to impose crystal point-group symmetry."
    ),
)
def symmetrize(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src    = inputs["data"]
    n_fold = params["n_fold"]
    do_abs = params["apply_abs"]

    L   = src.data.shape[0]
    out = np.zeros_like(src.data, dtype=np.float64)
    for i in range(L):
        layer  = np.abs(src.data[i]) if do_abs else src.data[i].astype(np.float64)
        out[i] = _symmetrize_layer(layer, n_fold)

    return UdsDataStru(
        name         = _build_name(src.name, n_fold),
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
