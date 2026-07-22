# -*- coding: utf-8 -*-
"""
Reader for Nanonis .dat point spectroscopy files.

Header is tab-separated key/value pairs, terminated by a [DATA] section.
Data rows follow after a column-header line.
"""
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
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


def _infer_sweep_axis_type(col_name: str) -> AxisType:
    """Infer AxisType from the sweep column name."""
    name_lower = col_name.lower()
    if "bias" in name_lower:
        return AxisType.BIAS
    if "z" in name_lower:
        return AxisType.SPATIAL_Z
    return AxisType.UNKNOWN


def load(path: Path) -> UdsDataStru:
    """Return a single UdsDataStru with the full raw data matrix (n_points × n_cols).

    Column splitting per channel-manager config is handled by
    file_loading._extract_dat_channels; this function just loads the raw table.
    """
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

    sweep_col  = column_names[0] if column_names else "sweep"
    sweep_type = _infer_sweep_axis_type(sweep_col)

    # Axes: one per column — sweep axis is axis 0, channels follow
    axes = [
        Axis(values=data[:, i].copy(),
             label=column_names[i] if i < len(column_names) else f"col{i}",
             units="",
             axis_type=sweep_type if i == 0 else AxisType.UNKNOWN)
        for i in range(data.shape[1])
    ]

    return UdsDataStru(
        name         = path.stem,
        data         = data,          # shape (n_points, n_cols) — sliced by _extract_dat_channels
        axes         = axes,
        info         = {
            "_source_format": "nanonis_dat",
            "_column_names": column_names,
            "sweep_column":  sweep_col,
            **{k: v for k, v in header.items()},
        },
        proc_history = [],
        landmarks    = {},
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
