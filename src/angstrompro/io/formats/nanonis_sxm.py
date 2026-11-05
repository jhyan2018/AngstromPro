# -*- coding: utf-8 -*-
"""
Reader for Nanonis .sxm scan image files.

The file contains a text header terminated by :SCANIT_END: followed by two
blank lines, then big-endian float32 binary data.

For ``both`` channels, the forward raster is loaded.  Explicit forward-only
and backward-only channels are also supported; backward rasters are reversed
along X to match the forward orientation.
"""
import logging
import re
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import (
    Axis,
    AxisType,
    UdsDataStru,
    file_source,
)
from angstrompro.io.angstrom_io import register_io


log = logging.getLogger(__name__)

_DIRECTION_ALIASES = {
    "both": "both",
    "forward": "forward",
    "fwd": "forward",
    "backward": "backward",
    "bwd": "backward",
}


def _normalise_direction(value: str) -> str:
    direction = str(value or "").strip().lower()
    try:
        return _DIRECTION_ALIASES[direction]
    except KeyError as exc:
        supported = ", ".join(sorted(_DIRECTION_ALIASES))
        raise ValueError(
            f"Unsupported DATA_INFO direction {value!r}; expected one of "
            f"{supported}."
        ) from exc


def _resolve_channel_directions(
    declared: list[str],
    actual_layers: int,
) -> tuple[list[str], bool, str]:
    """Reconcile DATA_INFO directions with the number of stored rasters.

    Some third-party 3DS-to-SXM exporters leave every direction as ``both``
    while writing only one raster per channel.  That layout is unambiguous in
    layer count but does not say whether the raster originated from a forward
    or backward scan.  Preserve it as stored using the internal ``single``
    direction and record the inference rather than inventing an X reversal.
    """
    resolved = [_normalise_direction(value) for value in declared]
    expected_layers = sum(
        2 if direction == "both" else 1 for direction in resolved)
    if actual_layers == expected_layers:
        return resolved, False, ""

    if (resolved and all(direction == "both" for direction in resolved)
            and actual_layers == len(resolved)):
        warning = (
            "DATA_INFO declares every channel as 'both', but the binary "
            "payload contains one raster per channel. Loading each raster "
            "as stored with direction 'single'; forward/backward origin "
            "cannot be inferred from this file."
        )
        return ["single"] * len(resolved), True, warning

    raise ValueError(
        "DATA_INFO declares "
        f"{expected_layers} raster layer(s) for {len(resolved)} channel(s), "
        f"but the binary payload contains {actual_layers}. The missing or "
        "extra channel directions cannot be inferred safely."
    )


def _parse_header(path: Path) -> tuple[dict, int]:
    """Return (header_dict, data_byte_offset)."""
    header = {}
    caption_re = re.compile(r'^:.+:$')
    current_key = ""
    current_val = ""

    with open(path, "rb") as f:
        while True:
            raw = f.readline()
            line = raw.decode("latin-1").strip()

            if line == ":SCANIT_END:":
                f.readline()  # blank line 1
                f.readline()  # blank line 2
                data_offset = f.tell()
                # store last key
                if current_key:
                    header[current_key] = current_val.strip()
                break

            if caption_re.match(line):
                if current_key:
                    header[current_key] = current_val.strip()
                current_key = line[1:-1]
                current_val = ""
            else:
                current_val += line + "\n"

    return header, data_offset


def load(path: Path,
         channel_indices: list[int] | None = None) -> UdsDataStru | list[UdsDataStru]:
    path = Path(path)
    try:
        header, data_offset = _parse_header(path)
    except Exception as exc:
        raise ValueError(f"Cannot parse header of {path.name}: {exc}") from exc

    try:
        # Pixel dimensions
        pixels = header.get("SCAN_PIXELS", "").split()
        x_pixels = int(pixels[0])
        y_pixels = int(pixels[1])

        # Scan range in metres
        scan_range = header.get("SCAN_RANGE", "0 0").split()
        x_range = float(scan_range[0])
        y_range = float(scan_range[1])

        # Parse DATA_INFO to get channels and directions
        data_info_text = header.get("DATA_INFO", "")
        lines = data_info_text.strip().split("\n")
        # first line is the header row: Channel Name Unit Direction Calibration Offset
        channel_names = []
        channel_dirs_declared = []
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) > 3:
                channel_names.append(parts[1].strip())
                channel_dirs_declared.append(parts[3].strip())
        if not channel_names:
            raise ValueError("DATA_INFO contains no readable channel rows.")

        # Load raw binary data (big-endian float32)
        with open(path, "rb") as f:
            f.seek(data_offset + 2)  # skip 2-byte pad (as in old code)
            raw = np.fromfile(f, dtype=">f4")

        pixels_per_layer = x_pixels * y_pixels
        if pixels_per_layer <= 0:
            raise ValueError(
                f"Invalid SCAN_PIXELS dimensions: {x_pixels} x {y_pixels}.")
        if raw.size % pixels_per_layer:
            raise ValueError(
                f"Binary payload contains {raw.size} float values, which is "
                f"not divisible by one {x_pixels} x {y_pixels} raster "
                f"({pixels_per_layer} values)."
            )
        actual_layers = raw.size // pixels_per_layer
        channel_dirs, direction_inferred, direction_warning = (
            _resolve_channel_directions(
                channel_dirs_declared, actual_layers))
        if direction_warning:
            log.warning("%s: %s", path.name, direction_warning)

        # Nanonis stores rows top→bottom: shape is (layers, y, x)
        data_all = raw.astype(np.float32).reshape(
            (actual_layers, y_pixels, x_pixels)
        )
        data_all = np.nan_to_num(data_all, nan=0.0)

        # Select one raster per channel. Backward scans are acquired in the
        # opposite X direction, so reverse their columns before exposing them.
        selected_indices = []
        selected_directions = []
        layer = 0
        for d in channel_dirs:
            if d == "both":
                data_all[layer + 1, :, :] = data_all[layer + 1, :, ::-1]
                selected_indices.append(layer)
                selected_directions.append("forward")
                layer += 2
            elif d == "backward":
                data_all[layer, :, :] = data_all[layer, :, ::-1]
                selected_indices.append(layer)
                selected_directions.append("backward")
                layer += 1
            else:
                selected_indices.append(layer)
                selected_directions.append(d)
                layer += 1

        # Nanonis stores first row at top of image; flip Y so row 0 = bottom
        data_all = data_all[:, ::-1, :]

        data_selected = data_all[selected_indices, :, :]
        n_ch = len(channel_names)

        # Build axes — each channel loaded as (1, y, x): axis[0]=bias, axis[1]=y, axis[2]=x
        try:
            bias_v = float(header.get("BIAS", 0.0))
        except (ValueError, TypeError):
            bias_v = 0.0
        ax_bias = Axis(
            values=np.array([bias_v]),
            label="Bias (V)",
            units="V",
            axis_type=AxisType.BIAS,
        )
        ax_y = Axis(
            values=np.linspace(0.0, y_range, y_pixels),
            label="Y (m)",
            units="m",
            axis_type=AxisType.SPATIAL_Y,
        )
        ax_x = Axis(
            values=np.linspace(0.0, x_range, x_pixels),
            label="X (m)",
            units="m",
            axis_type=AxisType.SPATIAL_X,
        )

        # Metadata
        info: dict = {
            "source": file_source(path),
            "_channels": channel_names,
            "channel_directions_declared": list(channel_dirs_declared),
            "channel_directions_loaded": list(selected_directions),
            "direction_inferred": direction_inferred,
            "_x_pixels": x_pixels,
            "_y_pixels": y_pixels,
            "scan_range_x_m": x_range,
            "scan_range_y_m": y_range,
        }
        scan_offset = header.get("SCAN_OFFSET", "")
        if scan_offset:
            info["scan_offset"] = scan_offset
        scan_angle = header.get("SCAN_ANGLE", "")
        if scan_angle:
            info["scan_angle_deg"] = scan_angle
        if "BIAS" in header:
            try:
                info["bias_v"] = float(header["BIAS"])
            except ValueError:
                info["bias_v"] = header["BIAS"]
        if "Z-CONTROLLER" in header:
            zc = header["Z-CONTROLLER"]
            lines_zc = zc.strip().split("\n")
            if len(lines_zc) >= 2:
                keys_zc = lines_zc[0].split("\t")
                vals_zc = lines_zc[1].split("\t")
                info["z_controller"] = dict(zip(keys_zc, vals_zc))
        if direction_warning:
            info["direction_warning"] = direction_warning

    except Exception as exc:
        raise ValueError(f"Error reading {path.name}: {exc}") from exc

    def _make_item(ch_idx: int) -> UdsDataStru:
        ci = max(0, min(ch_idx, n_ch - 1))
        single = data_selected[ci:ci+1, :, :]
        ch_info = {
            **info,
            "channel_loaded": channel_names[ci],
            "channel_direction_declared": channel_dirs_declared[ci],
            "channel_direction_loaded": selected_directions[ci],
            "_channel_index": ci,
        }
        return UdsDataStru(
            name=f"{path.stem}_{channel_names[ci]}",
            data=single.astype(np.float64),
            axes=[ax_bias, ax_y, ax_x],
            info=ch_info,
            proc_history=[],
            landmarks={},
        )

    if channel_indices is not None:
        results = [_make_item(i) for i in channel_indices]
        return results[0] if len(results) == 1 else results

    # Default: return all channels stacked
    return UdsDataStru(
        name=path.stem,
        data=data_selected.astype(np.float64),
        axes=[ax_bias, ax_y, ax_x],
        info=info,
        proc_history=[],
        landmarks={},
    )


def _no_write(path, data):
    raise NotImplementedError("Writing .sxm is not supported")


register_io(
    type_id="nanonis_sxm",
    reader=load,
    writer=_no_write,
    extension=".sxm",
    display_name="Nanonis Map (.sxm)",
    description="Nanonis STM scan image, multi-channel.",
    writable=False,
)
