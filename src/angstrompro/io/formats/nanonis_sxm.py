# -*- coding: utf-8 -*-
"""
Reader for Nanonis .sxm scan image files.

The file contains a text header terminated by :SCANIT_END: followed by two
blank lines, then big-endian float32 binary data.

Only the forward-scan channels are loaded (even indices in the interleaved
channel list, since each channel is stored fwd then bwd when direction='both').
"""
import re
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.io.angstrom_io import register_io


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
        channel_dirs = []
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) > 3:
                channel_names.append(parts[1].strip())
                channel_dirs.append(parts[3].strip())

        # Count total stored layers (fwd + bwd per channel when 'both')
        total_layers = sum(2 if d == "both" else 1 for d in channel_dirs)

        # Load raw binary data (big-endian float32)
        with open(path, "rb") as f:
            f.seek(data_offset + 2)  # skip 2-byte pad (as in old code)
            raw = np.fromfile(f, dtype=">f4")

        # Nanonis stores rows top→bottom: shape is (layers, y, x)
        data_all = raw.astype(np.float32).reshape(
            (total_layers, y_pixels, x_pixels)
        )
        data_all = np.nan_to_num(data_all, nan=0.0)

        # Flip backward-scan columns (x axis reversed for bwd pass)
        layer = 0
        for d in channel_dirs:
            if d == "both":
                data_all[layer + 1, :, :] = data_all[layer + 1, :, ::-1]
                layer += 2
            else:
                layer += 1

        # Nanonis stores first row at top of image; flip Y so row 0 = bottom
        data_all = data_all[:, ::-1, :]

        # Extract only forward channels
        fwd_indices = []
        layer = 0
        for d in channel_dirs:
            fwd_indices.append(layer)
            layer += 2 if d == "both" else 1

        data_fwd = data_all[fwd_indices, :, :]  # shape (n_channels, y, x)
        n_ch = len(channel_names)

        # Build axes — each channel loaded as (1, y, x): axis[0]=bias, axis[1]=y, axis[2]=x
        bias_v = float(info.get("bias_v", 0.0))
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
            "source_format": "nanonis_sxm",
            "channels": channel_names,
            "x_pixels": x_pixels,
            "y_pixels": y_pixels,
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

    except Exception as exc:
        raise ValueError(f"Error reading {path.name}: {exc}") from exc

    def _make_item(ch_idx: int) -> UdsDataStru:
        ci = max(0, min(ch_idx, n_ch - 1))
        single = data_fwd[ci:ci+1, :, :]   # keep ndim=3: (1, y, x)
        ch_info = {**info, "channel_loaded": channel_names[ci], "channel_index": ci}
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
        data=data_fwd.astype(np.float64),
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
    description="Nanonis STM scan image, multi-channel (forward scan only).",
    writable=False,
)
