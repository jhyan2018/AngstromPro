# -*- coding: utf-8 -*-
"""
Reader for Nanonis .3ds grid spectroscopy files.

Header is ASCII key=value pairs terminated by ':HEADER_END:\n'.
Data is big-endian float32.

The loaded data has shape (n_points, y_pixels, x_pixels) using only the first
spectroscopy channel (dI/dV or whichever appears first in 'channels').
All channel names are available via the internal ``info['_channels']`` entry.
"""
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.io.angstrom_io import register_io


def parse_header(path: Path) -> tuple[dict, int]:
    """Parse the ASCII header of a .3ds file.  Returns (header_dict, data_offset)."""
    header: dict = {}
    with open(path, "rb") as f:
        while True:
            raw = f.readline()
            line = raw.decode("latin-1").strip().replace('"', "")
            if line == ":HEADER_END:":
                data_offset = f.tell()
                break
            if "=" in line:
                k, v = line.split("=", 1)
                header[k.lower().strip()] = v.strip()
    return header, data_offset


# Keep the private alias for any internal callers
_parse_header = parse_header


def load(path: Path, channel_index: int = 0,
         channel_indices: list[int] | None = None) -> UdsDataStru | list[UdsDataStru]:
    path = Path(path)
    try:
        header, data_offset = parse_header(path)
    except Exception as exc:
        raise ValueError(f"Cannot parse header of {path.name}: {exc}") from exc

    try:
        grid_dim = list(map(int, header["grid dim"].split("x")))
        x_pixels, y_pixels = grid_dim[0], grid_dim[1]

        par_num = int(header["# parameters (4 byte)"])
        n_points = int(header["points"])
        channels = [c.strip() for c in header["channels"].split(";")]
        n_channels = len(channels)

        grid_settings = dict(zip(
            ("cx", "cy", "w", "h", "angle_deg"),
            map(float, header["grid settings"].split(";")),
        ))
        x_range = grid_settings["w"]
        y_range = grid_settings["h"]

        sweep_signal = header.get("sweep signal", "Bias (V)").strip()

        # Load raw data
        stride = par_num + n_channels * n_points
        with open(path, "rb") as f:
            f.seek(data_offset)
            raw = np.fromfile(f, dtype=">f4")

        total_pixels = x_pixels * y_pixels
        expected = total_pixels * stride
        if raw.size < expected:
            raw = np.pad(raw, (0, expected - raw.size))
        else:
            raw = raw[:expected]

        data2D = raw.astype(np.float32).reshape(-1, stride)

        # Build 3D volume: (stride, x_pixels, y_pixels)
        data3D = np.zeros((stride, x_pixels, y_pixels), dtype=np.float32)
        if y_pixels == 1:
            # data2D rows are the x_pixels spectra; columns are stride values
            data3D[:, :, 0] = data2D[:x_pixels, :].T
        else:
            rows_per_line = data2D.shape[0] // x_pixels
            last = data2D.shape[0] % x_pixels
            for i in range(stride):
                for j in range(rows_per_line):
                    data3D[i, j, :] = data2D[j * x_pixels:(j + 1) * x_pixels, i]
                if last:
                    data3D[i, j + 1, :last] = data2D[(j + 1) * x_pixels:, i]

        data3D = np.flip(data3D, axis=1)

        # Read sweep axis: prefer the sweep-signal channel stored in the data block
        # (present when Nanonis records the swept variable explicitly, e.g. non-linear sweeps).
        # Fall back to linspace(sweep_start, sweep_end, n_points) for standard linear sweeps.
        channels_lower = [c.lower() for c in channels]
        sweep_signal_lower = sweep_signal.lower()
        sweep_ch_idx = next(
            (i for i, c in enumerate(channels_lower)
             if sweep_signal_lower in c or c in sweep_signal_lower),
            None,
        )
        if sweep_ch_idx is not None:
            start = par_num + sweep_ch_idx * n_points
            sweep_vals = data3D[start:start + n_points, 0, 0].astype(np.float64)
        else:
            # Standard linear sweep: read start/end from fixed parameters
            fixed_params = [p.strip() for p in header.get("fixed parameters", "").split(";")]
            fixed_params_lower = [p.lower() for p in fixed_params]
            sweep_start, sweep_end = 0.0, 0.0
            if "sweep start" in fixed_params_lower:
                sweep_start = float(data3D[fixed_params_lower.index("sweep start"), 0, 0])
            if "sweep end" in fixed_params_lower:
                sweep_end = float(data3D[fixed_params_lower.index("sweep end"), 0, 0])
            sweep_vals = np.linspace(sweep_start, sweep_end, n_points)

        sweep_units = sweep_signal.split("(")[-1].rstrip(")").strip() if "(" in sweep_signal else ""
        ax_bias = Axis(values=sweep_vals, label=sweep_signal, units=sweep_units,
                       axis_type=AxisType.BIAS)
        ax_y = Axis(values=np.linspace(0.0, y_range, y_pixels), label="Y (m)", units="m",
                    axis_type=AxisType.SPATIAL_Y)
        ax_x = Axis(values=np.linspace(0.0, x_range, x_pixels), label="X (m)", units="m",
                    axis_type=AxisType.SPATIAL_X)

        base_info: dict = {
            "_source_format": "nanonis_3ds",
            "_channels":      channels,
            "_n_points":      n_points,
            "_x_pixels":      x_pixels,
            "_y_pixels":      y_pixels,
            "sweep_signal":   sweep_signal,
            "grid_settings":  grid_settings,
        }
        if "bias>bias (v)" in header:
            try:
                base_info["bias_v"] = float(header["bias>bias (v)"])
            except ValueError:
                pass
        if "current>current (a)" in header:
            try:
                base_info["current_a"] = float(header["current>current (a)"])
            except ValueError:
                pass

        def _extract(ch_idx: int) -> UdsDataStru:
            ci = max(0, min(ch_idx, n_channels - 1))
            start = par_num + ci * n_points
            ch_data = data3D[start:start + n_points, :, :]   # (n_pts, x, y)
            info = {**base_info, "channel_loaded": channels[ci], "_channel_index": ci}
            # Line-cut special case: y_pixels=1 means a single spatial line.
            # Squeeze the degenerate y-axis → 2D (n_pts, x_pixels) for CurveStackViewer.
            if y_pixels == 1:
                ch_data = ch_data[:, :, 0].T   # (n_pts, x_pixels) → (x_pixels, n_pts)
                axes = [ax_x, ax_bias]
            else:
                axes = [ax_bias, ax_x, ax_y]
            return UdsDataStru(
                name=f"{path.stem}_{channels[ci]}",
                data=ch_data.astype(np.float64),
                axes=axes,
                info=info,
                proc_history=[],
                landmarks={},
            )

    except Exception as exc:
        raise ValueError(f"Error reading {path.name}: {exc}") from exc

    # Multi-channel load
    if channel_indices is not None:
        results = [_extract(i) for i in channel_indices]
        # Single item: unwrap for convenience; caller can also check isinstance
        return results[0] if len(results) == 1 else results

    return _extract(channel_index)


def _no_write(path, data):
    raise NotImplementedError("Writing .3ds is not supported")


register_io(
    type_id="nanonis_3ds",
    reader=load,
    writer=_no_write,
    extension=".3ds",
    display_name="Nanonis Grid Spectroscopy (.3ds)",
    description="Nanonis 3D spectroscopy grid; loads first channel as (n_points, y, x).",
    writable=False,
)
