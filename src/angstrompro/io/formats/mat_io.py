# -*- coding: utf-8 -*-
"""
Reader for MATLAB .mat files.
"""
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.io.angstrom_io import register_io


def load(path: Path) -> UdsDataStru:
    path = Path(path)
    try:
        import scipy.io as sio
        mat_dict = sio.loadmat(str(path))
    except Exception as exc:
        raise ValueError(f"Cannot load {path.name} as .mat: {exc}") from exc

    keys = [k for k in mat_dict.keys() if not k.startswith("__")]
    if not keys:
        raise ValueError(f"No valid data keys found in {path.name}")

    mat_key = keys[0]
    data = mat_dict[mat_key]

    if not isinstance(data, np.ndarray):
        raise ValueError(f"Key '{mat_key}' in {path.name} is not a numpy array")

    data = np.atleast_2d(data).astype(np.float64)

    axes = [Axis(values=np.arange(data.shape[i], dtype=float), label="index")
            for i in range(data.ndim)]

    return UdsDataStru(
        name=path.stem,
        data=data,
        axes=axes,
        info={"source_format": "mat", "mat_key": mat_key},
        proc_history=[],
        landmarks={},
    )


def _no_write(path, data):
    raise NotImplementedError("Writing .mat is not supported")


register_io(
    type_id="mat",
    reader=load,
    writer=_no_write,
    extension=".mat",
    display_name="MATLAB Data (.mat)",
    description="MATLAB binary data file.",
    writable=False,
)
