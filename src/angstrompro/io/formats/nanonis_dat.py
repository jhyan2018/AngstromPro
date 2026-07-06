# -*- coding: utf-8 -*-
"""
Reader for Nanonis .dat point spectroscopy files.

Header is tab-separated key/value pairs, terminated by a [DATA] section.
Data rows follow after a column-header line.
"""
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.io.angstrom_io import register_io


def _parse_header(path: Path) -> tuple[dict, list[str], int]:
    """Return (header_dict, column_names, data_byte_offset)."""
    header: dict = {}
    column_names: list[str] = []
    with open(path, "rb") as f:
        while True:
            raw = f.readline()
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line == "[DATA]":
                col_line = f.readline().decode("utf-8", errors="replace").strip()
                column_names = col_line.split("\t")
                data_offset = f.tell()
                break
            parts = line.split("\t")
            key = parts[0].strip()
            val = parts[-1].strip() if len(parts) > 1 else ""
            header[key] = val
    return header, column_names, data_offset


def load(path: Path) -> UdsDataStru:
    path = Path(path)
    try:
        header, column_names, data_offset = _parse_header(path)
    except Exception as exc:
        raise ValueError(f"Cannot parse header of {path.name}: {exc}") from exc

    try:
        with open(path, "rb") as f:
            f.seek(data_offset)
            data = np.loadtxt(f, dtype=np.float64, encoding="utf-8")
    except Exception as exc:
        raise ValueError(f"Error reading data from {path.name}: {exc}") from exc

    if data.ndim == 1:
        data = data.reshape(1, -1)

    n_rows, n_cols = data.shape

    ax_row = Axis(values=np.arange(n_rows, dtype=float), label="index")
    ax_col = Axis(values=np.arange(n_cols, dtype=float), label="channel index")

    info: dict = {
        "source_format": "nanonis_dat",
        "column_names": column_names,
    }
    for k, v in header.items():
        info[k] = v

    return UdsDataStru(
        name=path.stem,
        data=data,
        axes=[ax_row, ax_col],
        info=info,
        proc_history=[],
        landmarks={},
    )


def _no_write(path, data):
    raise NotImplementedError("Writing .dat is not supported")


register_io(
    type_id="nanonis_dat",
    reader=load,
    writer=_no_write,
    extension=".dat",
    display_name="Nanonis Point Spectroscopy (.dat)",
    description="Nanonis ASCII point spectroscopy; rows=points, cols=channels.",
    writable=False,
)
