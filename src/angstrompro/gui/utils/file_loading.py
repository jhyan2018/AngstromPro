# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Standalone helpers for loading files with optional channel-picker dialogs.
These were extracted from AGuiModule to keep format-specific IO logic out of
the generic module base class.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext
    from PyQt6 import QtWidgets

_CHANNEL_PICKER_EXTS = {".3ds", ".sxm", ".dat"}


def load_with_channel_picker(path: Path, context: "AppContext",
                              parent: "QtWidgets.QWidget | None" = None):
    """
    Load *path*, showing a channel-picker dialog for multi-channel formats.

    Returns a UdsDataStru or list thereof, or None if the user cancelled.
    """
    from angstrompro.io import load

    ext = path.suffix.lower()
    if ext not in _CHANNEL_PICKER_EXTS:
        return load(path)

    # ------------------------------------------------------------------ .3ds
    if ext == ".3ds":
        from angstrompro.io.formats.nanonis_3ds import parse_header, load as load_3ds
        from angstrompro.gui.dialogs.channel_picker_dialog import ChannelPickerDialog
        header, _ = parse_header(path)
        channels = [c.strip() for c in header.get("channels", "").split(";") if c.strip()]
        if not channels:
            return load(path)
        fmt_cfg = context.channel_manager.get("nanonis_3ds")
        resolved = fmt_cfg.resolve(channels) if fmt_cfg else []
        if fmt_cfg and fmt_cfg.auto_load:
            pairs = _resolve_auto_load(fmt_cfg, resolved, channels, context, parent)
            if pairs is None:
                return None
            indices = [idx for _, idx in pairs]
            result = load_3ds(path, channel_indices=indices or [0])
            return _apply_display_names(result, pairs, path.stem)
        grid_dim = header.get("grid dim", "1x1").split("x")
        file_info = {
            "x_pixels": int(grid_dim[0]) if len(grid_dim) > 0 else "?",
            "y_pixels": int(grid_dim[1]) if len(grid_dim) > 1 else "?",
            "n_points": header.get("points", ""),
        }
        dlg = ChannelPickerDialog(parent, path, channels, file_info, fmt_cfg)
        if dlg.exec() != _accepted():
            return None
        indices = dlg.selected_indices()
        if not indices:
            return None
        idx_to_display = {idx: cc.display_name for cc, idx in resolved if idx is not None}
        result = load_3ds(path, channel_indices=indices)
        pairs = [(None, idx) for idx in indices]
        return _apply_display_names(result, pairs, path.stem, idx_to_display)

    # ------------------------------------------------------------------ .sxm
    if ext == ".sxm":
        from angstrompro.io.formats.nanonis_sxm import _parse_header, load as load_sxm
        from angstrompro.gui.dialogs.channel_picker_dialog import ChannelPickerDialog
        header, _ = _parse_header(path)
        data_info = header.get("DATA_INFO", "")
        lines = [ln for ln in data_info.strip().split("\n") if ln.strip()]
        channels = []
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) > 1:
                channels.append(parts[1].strip())
        if not channels:
            return load(path)
        fmt_cfg = context.channel_manager.get("nanonis_sxm")
        resolved = fmt_cfg.resolve(channels) if fmt_cfg else []
        if fmt_cfg and fmt_cfg.auto_load:
            pairs = _resolve_auto_load(fmt_cfg, resolved, channels, context, parent)
            if pairs is None:
                return None
            indices = [idx for _, idx in pairs]
            result = load_sxm(path, channel_indices=indices or [0])
            return _apply_display_names(result, pairs, path.stem)
        pixels = header.get("SCAN_PIXELS", "? ?").split()
        file_info = {
            "x_pixels": pixels[0] if len(pixels) > 0 else "?",
            "y_pixels": pixels[1] if len(pixels) > 1 else "?",
        }
        dlg = ChannelPickerDialog(parent, path, channels, file_info, fmt_cfg)
        if dlg.exec() != _accepted():
            return None
        indices = dlg.selected_indices()
        if not indices:
            return None
        idx_to_display = {idx: cc.display_name for cc, idx in resolved if idx is not None}
        result = load_sxm(path, channel_indices=indices)
        pairs = [(None, idx) for idx in indices]
        return _apply_display_names(result, pairs, path.stem, idx_to_display)

    # ------------------------------------------------------------------ .dat
    if ext == ".dat":
        from angstrompro.io.formats.nanonis_dat import _parse_header, load as load_dat
        from angstrompro.gui.dialogs.channel_picker_dialog import ChannelPickerDialog
        header, column_names, _ = _parse_header(path)
        if not column_names or len(column_names) < 2:
            return load(path)
        data_channels = column_names[1:]
        fmt_cfg = context.channel_manager.get("nanonis_dat")
        resolved = fmt_cfg.resolve(data_channels) if fmt_cfg else []
        if fmt_cfg and fmt_cfg.auto_load:
            pairs = _resolve_auto_load(fmt_cfg, resolved, data_channels, context, parent)
            if pairs is None:
                return None
            pairs_offset = [(cc, idx + 1) for cc, idx in pairs]
            return _extract_dat_channels(load_dat(path), column_names, pairs_offset, path.stem)
        file_info = {"n_points": header.get("Points", "?"),
                     "n_channels": len(data_channels)}
        dlg = ChannelPickerDialog(parent, path, data_channels, file_info, fmt_cfg)
        if dlg.exec() != _accepted():
            return None
        indices = dlg.selected_indices()
        if not indices:
            return None
        idx_to_display = {idx: cc.display_name for cc, idx in resolved if idx is not None}
        pairs_offset = [(None, idx + 1) for idx in indices]
        return _extract_dat_channels(load_dat(path), column_names, pairs_offset,
                                     path.stem, idx_to_display)

    return load(path)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _accepted():
    from PyQt6.QtWidgets import QDialog
    return QDialog.DialogCode.Accepted


def _resolve_auto_load(fmt_cfg, resolved, file_channels, context: "AppContext",
                       parent: "QtWidgets.QWidget | None"):
    """
    For auto-load: collect matched default pairs; if any default channel is
    unmatched, show UnmatchedChannelsDialog.  Returns list of (cc, idx) pairs
    ready for loading, or None if user cancelled.
    """
    from angstrompro.gui.dialogs.unmatched_channels_dialog import UnmatchedChannelsDialog

    matched   = [(cc, idx) for cc, idx in resolved if cc.load_by_default and idx is not None]
    unmatched = [cc for cc, idx in resolved if cc.load_by_default and idx is None]

    if unmatched:
        dlg = UnmatchedChannelsDialog(parent, unmatched, file_channels)
        if dlg.exec() != _accepted():
            return None
        new_aliases: dict[str, str] = {}
        for res in dlg.resolutions():
            if res.file_index is not None:
                matched.append((res.channel_config, res.file_index))
            if res.save_alias and res.file_channel:
                new_aliases[res.channel_config.display_name] = res.file_channel
        if new_aliases:
            _save_new_aliases(fmt_cfg, new_aliases, context)

    return matched if matched else None


def _save_new_aliases(fmt_cfg, new_aliases: dict[str, str], context: "AppContext") -> None:
    """Prepend newly discovered file channel names to the matching ChannelConfig alias lists."""
    from angstrompro.io.channel_manager import ChannelConfig
    updated = []
    for cc in fmt_cfg.channels:
        if cc.display_name in new_aliases:
            new_alias = new_aliases[cc.display_name]
            aliases = [new_alias] + [a for a in cc.aliases if a != new_alias]
            updated.append(ChannelConfig(cc.display_name, aliases, cc.load_by_default))
        else:
            updated.append(cc)
    context.channel_manager.save_format(fmt_cfg.format_id, updated, auto_load=fmt_cfg.auto_load)


def _apply_display_names(result, pairs, stem: str, idx_to_display: dict | None = None):
    """Rename each UdsDataStru to stem_DisplayName."""
    items = result if isinstance(result, list) else [result]
    for payload, (cc, idx) in zip(items, pairs):
        if cc is not None:
            display = cc.display_name
        elif idx_to_display and idx in idx_to_display:
            display = idx_to_display[idx]
        else:
            display = getattr(payload, "name", stem)
        payload.name = f"{stem}_{display}"
        if hasattr(payload, "info") and isinstance(payload.info, dict):
            payload.info["channel_display_name"] = display
    return result


def _extract_dat_channels(full_uds, column_names: list[str],
                           pairs: list, stem: str,
                           idx_to_display: dict | None = None) -> list:
    """
    Split a fully-loaded .dat UDS into one 1D UdsDataStru per selected column.

    Column 0 is always the x-axis (Bias).  ``pairs`` contains
    (cc_or_None, col_index_in_full_array) with col_index >= 1.
    """
    import re
    from angstrompro.core.data.uds_data import Axis, UdsDataStru

    data_2d  = full_uds.data
    x_values = data_2d[:, 0]
    raw_x_label = column_names[0] if column_names else "Bias"
    # split "Bias calc (V)" → label="Bias calc", units="V"
    _m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", raw_x_label)
    x_label = _m.group(1) if _m else raw_x_label
    x_units = _m.group(2) if _m else ""
    base_info = {k: v for k, v in full_uds.info.items() if k not in ("column_names",)}

    results = []
    for cc, col_idx in pairs:
        if col_idx <= 0 or col_idx >= data_2d.shape[1]:
            continue
        if cc is not None:
            display = cc.display_name
        elif idx_to_display and (col_idx - 1) in idx_to_display:
            display = idx_to_display[col_idx - 1]
        else:
            display = (column_names[col_idx]
                       if col_idx < len(column_names) else f"col{col_idx}")

        y_values = data_2d[:, col_idx].copy()

        uds = UdsDataStru(
            name=f"{stem}_{display}",
            data=y_values,
            axes=[Axis(values=x_values.copy(), label=x_label, units=x_units)],
            info={**base_info,
                  "channel_display_name": display,
                  "column_name": column_names[col_idx]
                                 if col_idx < len(column_names) else ""},
            proc_history=[],
            landmarks={},
        )
        results.append(uds)

    return results if len(results) != 1 else results[0]
