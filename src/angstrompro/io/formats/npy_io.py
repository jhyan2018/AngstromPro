# -*- coding: utf-8 -*-
"""
Reader/writer for NumPy .npy files.
"""
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.io.angstrom_io import register_io


def load(path: Path) -> UdsDataStru:
    path = Path(path)
    try:
        data = np.load(path)
    except Exception as exc:
        raise ValueError(f"Cannot load {path.name} as .npy: {exc}") from exc

    if data.ndim == 1:
        data = data.reshape(1, -1)

    data = data.astype(np.float64)
    axes = [Axis(values=np.arange(data.shape[i], dtype=float), label="index")
            for i in range(data.ndim)]

    return UdsDataStru(
        name=path.stem,
        data=data,
        axes=axes,
        info={"_source_format": "npy"},
        proc_history=[],
        landmarks={},
    )


def save(path: Path, uds: UdsDataStru) -> None:
    np.save(path, uds.data)


register_io(
    type_id="npy",
    reader=load,
    writer=save,
    extension=".npy",
    display_name="NumPy Array (.npy)",
    description="NumPy binary array file.",
)
