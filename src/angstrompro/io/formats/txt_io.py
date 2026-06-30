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

    if data.ndim == 1:
        data = data.reshape(1, -1)

    axes = [Axis(values=np.arange(data.shape[i], dtype=float), label="index")
            for i in range(data.ndim)]

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
)
