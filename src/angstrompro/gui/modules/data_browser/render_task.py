# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

render_file_task — the Data Browser's whole-file render job.

Runs on an io pool thread: reads the file ONCE (headlessly — never any
channel-picker or alias dialog), renders a thumbnail PNG per selected
logical channel, and returns a plain result dict for the main thread to
write into the ThumbnailCache.  Alias learning stays in the interactive
open path; this task only consumes the aliases that already exist.

Channel selection comes in as plain data (list of dicts derived from the
workbench ChannelManager's FormatChannelConfig) so the task has no live
references to main-thread objects::

    channel_cfg = [{"display_name": "dI/dV",
                    "aliases": ["LI Demod 1 X", ...],
                    "load_by_default": True}, ...]

Result dict::

    {"file_path": str, "mtime": float, "format": str,
     "channels": [raw channel names in the file],
     "thumbs": [{"channel_id": str, "png_path": str,
                 "layer_count": int, "thumbnail_layer": int,
                 "status": "ok" | "not_found" | "no_renderer"}, ...]}

Raising propagates to TaskHandle.error; the module records the failure
(retry-capped) in the cache.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

# formats with multiple channels per file → workbench ChannelManager format id
MULTI_CHANNEL_FORMATS = {
    ".3ds": "nanonis_3ds",
    ".sxm": "nanonis_sxm",
    ".dat": "nanonis_dat",
}

def previewable_exts() -> set[str]:
    """All readable extensions from the IO registry.  Whether a payload is
    actually renderable is decided per payload at render time (three-tier
    rule: no renderer → icon-only card), so every readable format may be
    watched."""
    from angstrompro.io import uds_io, scene_plot_io  # noqa: F401 — ensure registered
    from angstrompro.io.angstrom_io import registered_formats
    return {f.extension.lower() for f in registered_formats()
            if f.readable and f.extension}


def channel_cfg_to_plain(fmt_cfg) -> list[dict]:
    """FormatChannelConfig → plain data for task kwargs."""
    if fmt_cfg is None:
        return []
    return [{"display_name": cc.display_name,
             "aliases": list(cc.aliases),
             "load_by_default": cc.load_by_default}
            for cc in fmt_cfg.channels]


def _resolve(channel_cfg: list[dict],
             file_channels: list[str]) -> list[tuple[dict, int | None]]:
    """Exact-match alias resolution (mirrors FormatChannelConfig.resolve)."""
    results = []
    for cc in channel_cfg:
        matched = None
        for alias in cc["aliases"]:
            for idx, fch in enumerate(file_channels):
                if alias == fch:
                    matched = idx
                    break
            if matched is not None:
                break
        results.append((cc, matched))
    return results


# ── headless per-format loading ───────────────────────────────────────────────

def _load_3ds(path: Path, channel_cfg: list[dict]):
    from angstrompro.io.formats.nanonis_3ds import parse_header, load as load_3ds
    header, _ = parse_header(path)
    channels = [c.strip() for c in header.get("channels", "").split(";") if c.strip()]
    resolved = _resolve(channel_cfg, channels)
    matched = [(cc, i) for cc, i in resolved if cc["load_by_default"] and i is not None]
    missing = [cc for cc, i in resolved if cc["load_by_default"] and i is None]
    payloads = []
    if matched:
        result = load_3ds(path, channel_indices=[i for _, i in matched])
        items = result if isinstance(result, list) else [result]
        payloads = list(zip((cc["display_name"] for cc, _ in matched), items))
    return channels, payloads, [cc["display_name"] for cc in missing]


def _load_sxm(path: Path, channel_cfg: list[dict]):
    from angstrompro.io.formats.nanonis_sxm import _parse_header, load as load_sxm
    header, _ = _parse_header(path)
    lines = [ln for ln in header.get("DATA_INFO", "").strip().split("\n") if ln.strip()]
    channels = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) > 1:
            channels.append(parts[1].strip())
    resolved = _resolve(channel_cfg, channels)
    matched = [(cc, i) for cc, i in resolved if cc["load_by_default"] and i is not None]
    missing = [cc for cc, i in resolved if cc["load_by_default"] and i is None]
    payloads = []
    if matched:
        result = load_sxm(path, channel_indices=[i for _, i in matched])
        items = result if isinstance(result, list) else [result]
        payloads = list(zip((cc["display_name"] for cc, _ in matched), items))
    return channels, payloads, [cc["display_name"] for cc in missing]


def _load_dat(path: Path, channel_cfg: list[dict]):
    from angstrompro.io.formats.nanonis_dat import _parse_header, load as load_dat
    from angstrompro.gui.utils.file_loading import _extract_dat_channels
    header, column_names, _ = _parse_header(path)
    channels = column_names[1:] if column_names and len(column_names) > 1 else []
    resolved = _resolve(channel_cfg, channels)
    matched = [(cc, i) for cc, i in resolved if cc["load_by_default"] and i is not None]
    missing = [cc for cc, i in resolved if cc["load_by_default"] and i is None]
    payloads = []
    if matched:
        # _extract_dat_channels expects (cc_obj_or_None, col_idx>=1) pairs
        pairs = [(None, i + 1) for _, i in matched]
        idx_to_display = {i: cc["display_name"] for cc, i in matched}
        result = _extract_dat_channels(load_dat(path), column_names, pairs,
                                       path.stem, idx_to_display)
        items = result if isinstance(result, list) else [result]
        payloads = list(zip((cc["display_name"] for cc, _ in matched), items))
    return channels, payloads, [cc["display_name"] for cc in missing]


_LOADERS = {".3ds": _load_3ds, ".sxm": _load_sxm, ".dat": _load_dat}


def _load_generic(path: Path):
    """Single-channel formats: one payload per file (or a list)."""
    from angstrompro.io import load
    result = load(path)
    items = result if isinstance(result, list) else [result]
    display = getattr(items[0], "info", {}).get("channel_display_name", "") \
        if hasattr(items[0], "info") and isinstance(items[0].info, dict) else ""
    return [(display or "data", p) for p in items]


# ── the task function ─────────────────────────────────────────────────────────

def render_file_task(file_path: str, cache_dir: str,
                     channel_cfg: list[dict] | None = None,
                     rcparams_delta: dict | None = None,
                     options: dict | None = None,
                     cancel_token=None) -> dict:
    """Read one file, render one PNG per selected channel.  Pool thread."""
    from angstrompro.gui.modules.data_browser.thumbnail_renderers import (
        render_payload_to_png)

    path = Path(file_path)
    mtime = os.path.getmtime(file_path)
    ext = path.suffix.lower()
    options = dict(options or {})
    figsize = tuple(options.pop("figsize", (2.6, 2.6)))
    dpi = int(options.pop("dpi", 100))

    if cancel_token is not None and cancel_token.is_cancelled():
        return {}

    loader = _LOADERS.get(ext)
    if loader is not None and channel_cfg:
        channels, payloads, missing = loader(path, channel_cfg)
    else:
        payloads = _load_generic(path)
        channels = [name for name, _ in payloads]
        missing = []

    if cancel_token is not None and cancel_token.is_cancelled():
        return {}

    thumbs: list[dict] = []
    for channel_id, payload in payloads:
        data = getattr(payload, "data", None)
        layer_count = int(data.shape[0]) if data is not None and data.ndim == 3 else 1
        layer = int(options.get("layer", 0))
        png_path = str(Path(cache_dir) / f"{uuid.uuid4().hex}.png")
        opts = {**options, "layer": layer}
        ok = render_payload_to_png(payload, png_path,
                                   rcparams_delta=rcparams_delta,
                                   options=opts, figsize=figsize, dpi=dpi)
        thumbs.append({
            "channel_id": channel_id,
            "png_path": png_path if ok else "",
            "layer_count": layer_count,
            "thumbnail_layer": layer if ok else 0,
            "status": "ok" if ok else "no_renderer",
        })

    for channel_id in missing:
        thumbs.append({"channel_id": channel_id, "png_path": "",
                       "layer_count": 1, "thumbnail_layer": 0,
                       "status": "not_found"})

    return {"file_path": file_path, "mtime": mtime,
            "format": MULTI_CHANNEL_FORMATS.get(ext, ext.lstrip(".")),
            "channels": channels, "thumbs": thumbs}


def render_channel_task(file_path: str, cache_dir: str, channel_id: str,
                        channel_cfg: list[dict] | None = None,
                        rcparams_delta: dict | None = None,
                        options: dict | None = None,
                        cancel_token=None) -> dict:
    """Re-render one channel of a known file (thumbnail-layer change etc.).
    Reads the file once but renders only the requested channel."""
    result = render_file_task(
        file_path, cache_dir,
        channel_cfg=[cc for cc in (channel_cfg or [])
                     if cc["display_name"] == channel_id] or channel_cfg,
        rcparams_delta=rcparams_delta, options=options,
        cancel_token=cancel_token)
    if result:
        result["thumbs"] = [t for t in result["thumbs"]
                            if t["channel_id"] == channel_id]
    return result
