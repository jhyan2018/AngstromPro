# -*- coding: utf-8 -*-
"""
Reader for LF STM binary files (.1fl / .tfr).

Binary format layout (from LFDataProcess.py):
  offset 406:  xSize (int32)
  offset 410:  ySize (int32)
  offset 480:  zSize (int16)
  offset 1046: bias_mv (float32) — multiply by 1e-3 to get V
  offset 1050: current_na (float32) — multiply by 1e-9 to get A
  offset 1058: scan_range_angstrom (float32) — multiply by 1e-10 to get m
  offset 1280: sweep_start_v (float32)
  offset 1284: sweep_stop_v (float32)
  offset 2112: data (uint16, count = xSize * ySize * zSize)
               reshape to (zSize, ySize, xSize)
"""
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.io.angstrom_io import register_io


def load(path: Path) -> UdsDataStru:
    path = Path(path)
    suffix = path.suffix.lower()

    try:
        with open(path, "rb") as f:
            # xSize at 406 (int32)
            f.seek(406)
            x_size = int(np.frombuffer(f.read(4), dtype=np.int32)[0])
            # ySize at 410 (int32)
            y_size = int(np.frombuffer(f.read(4), dtype=np.int32)[0])

            # zSize at 480 (int16)
            f.seek(480)
            z_size = int(np.frombuffer(f.read(2), dtype=np.int16)[0])

            # bias_v at 1024+22 = 1046 (float32, stored in mV)
            f.seek(1024 + 22)
            bias_v = float(np.frombuffer(f.read(4), dtype=np.float32)[0]) * 1e-3

            # current_a at 1024+26 = 1050 (float32, stored in nA)
            current_a = float(np.frombuffer(f.read(4), dtype=np.float32)[0]) * 1e-9

            # scan_range_m at 1024+34 = 1058 (float32, stored in Angstrom)
            f.seek(1024 + 34)
            scan_range_m = float(np.frombuffer(f.read(4), dtype=np.float32)[0]) * 1e-10

            # sweep start/stop at 1280
            f.seek(1280)
            sweep_start_v = float(np.frombuffer(f.read(4), dtype=np.float32)[0])
            sweep_stop_v = float(np.frombuffer(f.read(4), dtype=np.float32)[0])

            # Data at 2112
            f.seek(2112)
            count = x_size * y_size * z_size
            raw = np.frombuffer(f.read(count * 2), dtype=np.uint16).copy()

    except Exception as exc:
        raise ValueError(f"Cannot read {path.name}: {exc}") from exc

    try:
        data3D = raw.reshape((z_size, y_size, x_size)).astype(np.float64)
    except Exception as exc:
        raise ValueError(
            f"Shape mismatch in {path.name}: "
            f"expected ({z_size}, {y_size}, {x_size}), got {raw.size} elements: {exc}"
        ) from exc

    # Build axes
    if suffix == ".1fl":
        bias_axis_vals = np.linspace(sweep_start_v, sweep_stop_v, z_size)
        ax_z = Axis(values=bias_axis_vals, label="Bias (V)", units="V")
    else:
        # .tfr is a single-layer topo; z axis is just the bias setpoint
        ax_z = Axis(values=np.array([bias_v]), label="Bias (V)", units="V")

    ax_y = Axis(
        values=np.linspace(0.0, scan_range_m, y_size),
        label="Y (m)", units="m",
    )
    ax_x = Axis(
        values=np.linspace(0.0, scan_range_m, x_size),
        label="X (m)", units="m",
    )

    info: dict = {
        "source_format": "lf_" + suffix[1:],
        "bias_v": bias_v,
        "current_a": current_a,
        "scan_range_m": scan_range_m,
        "sweep_start_v": sweep_start_v,
        "sweep_stop_v": sweep_stop_v,
        "x_size": x_size,
        "y_size": y_size,
        "z_size": z_size,
    }

    return UdsDataStru(
        name=path.stem,
        data=data3D,
        axes=[ax_z, ax_y, ax_x],
        info=info,
        proc_history=[],
        landmarks={},
    )


def _no_write(path, data):
    raise NotImplementedError("Writing .1fl/.tfr is not supported")


register_io(
    type_id="lf_1fl",
    reader=load,
    writer=_no_write,
    extension=".1fl",
    display_name="LF dI/dV Map (.1fl)",
    description="LF STM binary dI/dV spectroscopy map.",
    writable=False,
)

register_io(
    type_id="lf_tfr",
    reader=load,
    writer=_no_write,
    extension=".tfr",
    display_name="LF Topo Map (.tfr)",
    description="LF STM binary topography map.",
    writable=False,
)
