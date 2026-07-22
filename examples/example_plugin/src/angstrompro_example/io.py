"""Read-only JSON format used by the example plugin."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.io.angstrom_io import register_ext_loader


def load_apdemo(path: Path) -> UdsDataStru:
    """Load a small synthetic image stack from an `.apdemo` JSON file."""
    path = Path(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        data = np.asarray(document["data"], dtype=np.float64)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Cannot load {path.name} as an APDemo file: {exc}") from exc

    if data.ndim != 3:
        raise ValueError(
            f"APDemo data must have three dimensions (layers, rows, columns); "
            f"received shape {data.shape}."
        )

    layers, rows, columns = data.shape
    return UdsDataStru(
        name=str(document.get("name") or path.stem),
        data=data,
        axes=[
            Axis(np.arange(layers, dtype=np.float64), "Layer", "", AxisType.INDEX),
            Axis(np.arange(rows, dtype=np.float64), "Y", "px", AxisType.SPATIAL_Y),
            Axis(np.arange(columns, dtype=np.float64), "X", "px", AxisType.SPATIAL_X),
        ],
        info={"_source_format": "apdemo", "source_path": str(path)},
    )


register_ext_loader(".apdemo", load_apdemo)
