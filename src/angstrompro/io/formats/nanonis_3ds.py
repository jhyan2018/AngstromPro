# -*- coding: utf-8 -*-
"""
Reader for Nanonis .3ds grid spectroscopy files.

Header is ASCII key=value pairs terminated by ':HEADER_END:\n'.
Data is big-endian float32.

Sweep channels produce a stack with one layer per sweep point. Experiment
parameters produce a single-layer spatial map with one value per grid pixel.
The two binary sources are selected independently.
"""
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

import numpy as np

from angstrompro.core.data.uds_data import (
    Axis,
    AxisType,
    UdsDataStru,
    file_source,
)
from angstrompro.io.angstrom_io import register_io


@dataclass(frozen=True)
class GridField:
    """A .3ds value's source and zero-based index within that source."""

    source: Literal["channel", "experiment_parameter"]
    index: int


def _header_names(header: dict, key: str) -> list[str]:
    raw = header.get(key, "")
    if not raw:
        return []
    names = [name.strip() for name in raw.split(";")]
    while names and not names[-1]:
        names.pop()
    if any(not name for name in names):
        raise ValueError(f"Empty name in .3ds {key!r} list")
    return names


def field_names(header: dict) -> tuple[list[str], list[str]]:
    """Return sweep channels and per-pixel experiment parameters separately."""
    return (
        _header_names(header, "channels"),
        _header_names(header, "experiment parameters") or
        _header_names(header, "experimental parameters"),
    )


def _field_stem(name: str) -> str:
    """Normalise a header field name while ignoring a trailing unit."""
    stem = re.sub(r"\s*\([^()]*\)\s*$", "", name.strip().casefold())
    return stem.rsplit(">", 1)[-1].strip()


def _find_sweep_channel(channels: list[str], sweep_signal: str) -> int | None:
    """Find a sweep channel without arbitrarily taking an ambiguous match."""
    signal = sweep_signal.strip().casefold()
    exact = [i for i, channel in enumerate(channels)
             if channel.strip().casefold() == signal]
    if len(exact) == 1:
        return exact[0]

    signal_stem = _field_stem(sweep_signal)
    stem_matches = [i for i, channel in enumerate(channels)
                    if _field_stem(channel) == signal_stem]
    if len(stem_matches) == 1:
        return stem_matches[0]

    # Retain compatibility with qualified channel names, but only when the
    # loose relation identifies exactly one channel.
    loose = [i for i, channel in enumerate(channels)
             if signal in channel.casefold() or channel.casefold() in signal]
    return loose[0] if len(loose) == 1 else None


def _find_fixed_parameter(fixed_parameters: list[str], name: str) -> int | None:
    target = _field_stem(name)
    return next((i for i, parameter in enumerate(fixed_parameters)
                 if _field_stem(parameter) == target), None)


def match_field(aliases: list[str], channels: list[str],
                parameters: list[str], source: str = "channel") -> GridField | None:
    """Resolve exact aliases without losing the field's binary source."""
    for alias in aliases:
        if source in ("channel", "either") and alias in channels:
            return GridField("channel", channels.index(alias))
        if source in ("experiment_parameter", "either") and alias in parameters:
            return GridField("experiment_parameter", parameters.index(alias))
    return None


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
         channel_indices: list[int] | None = None,
         fields: list[GridField] | None = None) -> UdsDataStru | list[UdsDataStru]:
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
        channels, experiment_parameters = field_names(header)
        n_channels = len(channels)
        fixed_parameters = _header_names(header, "fixed parameters")

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
        payload_floats = int(raw.size)
        complete_pixels = min(total_pixels, payload_floats // stride)
        trailing_floats = payload_floats % stride if payload_floats < expected else 0
        if raw.size < expected:
            # Preserve the historical, plottable zero fill for pixels that
            # were never acquired.  A partially written final record is not a
            # valid pixel and is discarded before padding.
            raw = raw[:complete_pixels * stride]
            raw = np.pad(raw, (0, expected - raw.size))
        else:
            raw = raw[:expected]

        data2D = raw.astype(np.float32).reshape(total_pixels, stride)

        # Pixel records run along X within each Y line.  Keep the established
        # vertical flip while giving the two spatial axes their true sizes.
        # This also handles rectangular grids, unlike the old square-only loop.
        data3D = np.flip(
            data2D.reshape(y_pixels, x_pixels, stride).transpose(2, 0, 1),
            axis=1,
        )  # (record value, y, x)
        if y_pixels == 1:
            # Preserve the old line-cut order, which flipped its X direction.
            data3D = np.flip(data3D, axis=2)

        # Read sweep axis: prefer the sweep-signal channel stored in the data block
        # (present when Nanonis records the swept variable explicitly, e.g. non-linear sweeps).
        # Fall back to linspace(sweep_start, sweep_end, n_points) for standard linear sweeps.
        sweep_ch_idx = _find_sweep_channel(channels, sweep_signal)
        sweep_axis_source = "unavailable"
        sweep_axis_valid = False
        if sweep_ch_idx is not None:
            start = par_num + sweep_ch_idx * n_points
            # Read from a completed acquisition record, not data3D[*, 0, 0]:
            # after the display Y flip that location belongs to the last scan
            # row and is zero-filled in a partial file.
            completed_axes = data2D[:complete_pixels, start:start + n_points]
            usable = next((values for values in completed_axes
                           if np.isfinite(values).all() and np.any(values != 0.0)),
                          None)
            if usable is not None:
                sweep_vals = usable.astype(np.float64)
                sweep_axis_source = "recorded_channel"
                sweep_axis_valid = True
            else:
                sweep_ch_idx = None

        if sweep_ch_idx is None:
            # Standard linear sweep: read start/end from fixed parameters
            sweep_start, sweep_end = 0.0, 0.0
            start_idx = _find_fixed_parameter(fixed_parameters, "sweep start")
            end_idx = _find_fixed_parameter(fixed_parameters, "sweep end")
            # Some writers omit the fixed-parameter names.  In the standard
            # grid layout the first two fixed values are still start and end.
            inferred_fixed_count = par_num - len(experiment_parameters)
            if start_idx is None and inferred_fixed_count >= 2:
                start_idx = 0
            if end_idx is None and inferred_fixed_count >= 2:
                end_idx = 1
            if complete_pixels and start_idx is not None and end_idx is not None:
                sweep_start = float(data2D[0, start_idx])
                sweep_end = float(data2D[0, end_idx])
                sweep_axis_source = "fixed_parameters"
                sweep_axis_valid = True
            sweep_vals = np.linspace(sweep_start, sweep_end, n_points)

        sweep_units = sweep_signal.split("(")[-1].rstrip(")").strip() if "(" in sweep_signal else ""
        ax_bias = Axis(values=sweep_vals, label=sweep_signal, units=sweep_units,
                       axis_type=AxisType.BIAS)
        ax_y = Axis(values=np.linspace(0.0, y_range, y_pixels), label="Y (m)", units="m",
                    axis_type=AxisType.SPATIAL_Y)
        ax_x = Axis(values=np.linspace(0.0, x_range, x_pixels), label="X (m)", units="m",
                    axis_type=AxisType.SPATIAL_X)

        base_info: dict = {
            "source":         file_source(path),
            "_channels":      channels,
            "_experiment_parameters": experiment_parameters,
            "_fixed_parameters": fixed_parameters,
            "_n_points":      n_points,
            "_x_pixels":      x_pixels,
            "_y_pixels":      y_pixels,
            "_complete_pixels": complete_pixels,
            "_expected_pixels": total_pixels,
            "_trailing_floats_discarded": trailing_floats,
            "incomplete_acquisition": complete_pixels < total_pixels,
            "sweep_signal":   sweep_signal,
            "sweep_axis_source": sweep_axis_source,
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
            if not sweep_axis_valid:
                raise ValueError(
                    "Cannot determine the sweep axis from any completed pixel "
                    "record or from Sweep Start/Sweep End parameters"
                )
            ci = max(0, min(ch_idx, n_channels - 1))
            start = par_num + ci * n_points
            ch_data = data3D[start:start + n_points, :, :]   # (n_pts, y, x)
            info = {**base_info, "field_source": "channel",
                    "channel_loaded": channels[ci], "_channel_index": ci}
            # Line-cut special case: y_pixels=1 means a single spatial line.
            # Squeeze the degenerate y-axis → 2D (n_pts, x_pixels) for CurveStackViewer.
            if y_pixels == 1:
                ch_data = ch_data[:, 0, :].T   # (n_pts, x_pixels) → (x_pixels, n_pts)
                axes = [ax_x, ax_bias]
            else:
                axes = [ax_bias, ax_y, ax_x]
            return UdsDataStru(
                name=f"{path.stem}_{channels[ci]}",
                data=ch_data.astype(np.float64),
                axes=axes,
                info=info,
                proc_history=[],
                landmarks={},
            )

        def _extract_parameter(param_idx: int) -> UdsDataStru:
            if not 0 <= param_idx < len(experiment_parameters):
                raise IndexError(f"Experiment parameter index {param_idx} is out of range")
            if par_num < len(experiment_parameters) or (
                fixed_parameters and
                len(fixed_parameters) + len(experiment_parameters) != par_num
            ):
                raise ValueError(
                    "Cannot locate experiment parameters: '# Parameters (4 byte)' "
                    f"is {par_num}, but the header lists {len(fixed_parameters)} "
                    f"fixed and {len(experiment_parameters)} experiment parameters"
                )
            raw_name = experiment_parameters[param_idx]
            # If fixed names are omitted, the remaining parameter slots are
            # still the fixed block preceding the listed experiment values.
            fixed_count = (len(fixed_parameters) if fixed_parameters else
                           par_num - len(experiment_parameters))
            param_pos = fixed_count + param_idx
            values = data3D[param_pos:param_pos + 1, :, :]
            units = raw_name.rsplit("(", 1)[-1].rstrip(")").strip() \
                if "(" in raw_name else ""
            info = {**base_info, "field_source": "experiment_parameter",
                    "experiment_parameter_loaded": raw_name,
                    "experiment_parameter_index": param_idx,
                    "fixed_parameter_count": fixed_count,
                    "parameter_units": units}
            name = f"{path.stem}_{raw_name.replace(':', '_')}"
            return UdsDataStru(
                name=name,
                data=values.astype(np.float64),
                axes=[Axis(values=np.array([0.0]), label="Layer"), ax_y, ax_x],
                info=info,
                proc_history=[],
                landmarks={},
            )

        def _extract_field(field: GridField) -> UdsDataStru:
            if field.source == "channel":
                if not 0 <= field.index < n_channels:
                    raise IndexError(f"Channel index {field.index} is out of range")
                return _extract(field.index)
            if field.source == "experiment_parameter":
                return _extract_parameter(field.index)
            raise ValueError(f"Unknown .3ds field source {field.source!r}")

    except Exception as exc:
        raise ValueError(f"Error reading {path.name}: {exc}") from exc

    if fields is not None:
        results = [_extract_field(field) for field in fields]
        return results[0] if len(results) == 1 else results

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
