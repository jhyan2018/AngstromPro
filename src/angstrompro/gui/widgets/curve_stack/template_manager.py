# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Scene template manager for CurveStackViewer.

Templates are stored as JSON in <UserDataFolder>/scene_templates/.
Each file contains:
  - "version": int
  - "rcparams_delta": dict of rcParam keys that differ from mpl defaults
  - "widget_style": dict of widget-specific style keys that differ from WIDGET_DEFAULTS

Only changed values are saved (delta pattern, same as angstrompro config system).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_VERSION = 1

# rcParam prefixes that represent visual appearance
_STYLE_PREFIXES = {
    "lines.", "axes.", "xtick.", "ytick.",
    "legend.", "font.", "image.", "figure.",
    "grid.", "patch.", "text.", "hatch.",
}

# rcParams that conflict with Qt layout or are irrelevant to appearance
_EXCLUDED_RCPARAMS = {
    "figure.figsize",
    "figure.dpi",
    "figure.max_open_warning",
    "figure.raise_window",
    "backend",
    "backend_fallback",
    "interactive",
    "toolbar",
    "savefig.dpi",
    "savefig.directory",
    "savefig.format",
    "path.simplify",
    "path.simplify_threshold",
    "path.snap",
    "path.sketch",
    "agg.path.chunksize",
    "animation.html",
    "animation.embed_limit",
    "animation.writer",
    "animation.codec",
    "animation.bitrate",
    "animation.frame_format",
    "animation.ffmpeg_path",
    "animation.convert_path",
    "webagg.open_in_browser",
    "webagg.port",
    "webagg.port_retries",
}

# Widget-specific style keys and their defaults
WIDGET_DEFAULTS: dict[str, object] = {
    "colormap":   "RdBu_r",
    "show_grid":  False,
    "line_width": 1.0,
}


def _tracked_keys() -> frozenset[str]:
    """Return the set of rcParam keys this template system controls."""
    import matplotlib as mpl
    return frozenset(
        k for k in mpl.rcParamsDefault
        if any(k.startswith(p) for p in _STYLE_PREFIXES)
        and k not in _EXCLUDED_RCPARAMS
    )


def templates_dir() -> Path:
    from angstrompro.app.user_data_folder import user_data_subpath
    d = user_data_subpath("scene_templates")
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_templates() -> list[str]:
    """Return template names (without extension), sorted alphabetically."""
    try:
        return sorted(p.stem for p in templates_dir().glob("*.scet"))
    except Exception:
        return []


def save_template(name: str, rcparams: dict, widget_style: dict) -> Path:
    """
    Save a template file.  Only keys differing from defaults are written.

    Parameters
    ----------
    name         : template name (filename stem)
    rcparams     : current matplotlib rcParams snapshot
    widget_style : current widget style dict (colormap, show_grid, line_width, …)
    """
    import matplotlib as mpl

    tracked = _tracked_keys()
    rcparams_delta = {
        k: rcparams[k]
        for k in tracked
        if k in rcparams and rcparams[k] != mpl.rcParamsDefault.get(k)
    }

    widget_delta = {
        k: v
        for k, v in widget_style.items()
        if v != WIDGET_DEFAULTS.get(k)
    }

    payload = {
        "version":       _VERSION,
        "rcparams_delta": rcparams_delta,
        "widget_style":  widget_delta,
    }

    path = templates_dir() / f"{name}.scet"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Template saved: %s", path)
    return path


def load_template(name: str) -> tuple[dict, dict]:
    """
    Load a template by name.

    Returns
    -------
    (rcparams_full, widget_style_full)
    Both are complete dicts starting from defaults, with the saved delta overlaid.
    """
    import matplotlib as mpl

    path = templates_dir() / f"{name}.scet"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    rcparams_delta = raw.get("rcparams_delta", {})
    widget_delta   = raw.get("widget_style", {})

    rcparams_full = {k: mpl.rcParamsDefault[k]
                     for k in _tracked_keys() if k in mpl.rcParamsDefault}
    rcparams_full.update(rcparams_delta)

    widget_style_full = dict(WIDGET_DEFAULTS)
    widget_style_full.update(widget_delta)

    return rcparams_full, widget_style_full


def apply_rcparams(rcparams: dict) -> None:
    """Apply a rcparams dict to the current matplotlib session."""
    import matplotlib as mpl
    tracked = _tracked_keys()
    for k, v in rcparams.items():
        if k in tracked:
            try:
                mpl.rcParams[k] = v
            except Exception as exc:
                log.debug("Could not set rcParam %r = %r: %s", k, v, exc)
