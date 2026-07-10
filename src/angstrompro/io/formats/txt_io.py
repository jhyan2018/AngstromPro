# -*- coding: utf-8 -*-
"""
Reader for whitespace-delimited text files (.txt).
"""
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.io.angstrom_io import register_io


def load(path: Path) -> UdsDataStru:
    path = Path(path)
    try:
        data = np.loadtxt(path, dtype=np.float64, encoding="utf-8")
    except Exception as exc:
        raise ValueError(f"Cannot load {path.name} as text: {exc}") from exc

    # Normalise to ndim=3: (1, rows, cols)
    if data.ndim == 1:
        data = data[np.newaxis, np.newaxis, :]   # (1, 1, N)
    elif data.ndim == 2:
        data = data[np.newaxis, :, :]            # (1, rows, cols)

    axes = [
        Axis(values=np.arange(data.shape[0], dtype=float), label="index"),
        Axis(values=np.arange(data.shape[1], dtype=float), label="row"),
        Axis(values=np.arange(data.shape[2], dtype=float), label="col"),
    ]

    return UdsDataStru(
        name=path.stem,
        data=data,
        axes=axes,
        info={"source_format": "txt"},
        proc_history=[],
        landmarks={},
    )


def _no_write(path, data):
    raise NotImplementedError("Writing .txt is not supported")


register_io(
    type_id="txt",
    reader=load,
    writer=_no_write,
    extension=".txt",
    display_name="Text Data (.txt)",
    description="Whitespace-delimited numeric text file.",
    writable=False,
)
