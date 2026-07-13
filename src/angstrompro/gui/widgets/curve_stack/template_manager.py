# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Scene template manager for CurveStackViewer.

Template file format (.scet, JSON):
  {
    "version": 1,
    "rcparams_delta": { <key>: <value>, ... },
    "widget_extras": {
      "stack":    { "color_mode": "...", "offset": 0.0 },
      "colormap": { "colormap": "RdBu_r", "symmetric": false },
      ...
    }
  }

Save is always a merge: only the current widget type's widget_extras section is
replaced; other widget types' sections are preserved from the existing file.
Missing sections at load time fall back to widget defaults silently.
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
    "figure.figsize", "figure.dpi", "figure.max_open_warning",
    "figure.raise_window", "backend", "backend_fallback",
    "interactive", "toolbar", "savefig.dpi", "savefig.directory",
    "savefig.format", "path.simplify", "path.simplify_threshold",
    "path.snap", "path.sketch", "agg.path.chunksize",
    "animation.html", "animation.embed_limit", "animation.writer",
    "animation.codec", "animation.bitrate", "animation.frame_format",
    "animation.ffmpeg_path", "animation.convert_path",
    "webagg.open_in_browser", "webagg.port", "webagg.port_retries",
}

# Per-widget-type default extras (used as fallback on load)
WIDGET_EXTRA_DEFAULTS: dict[str, dict] = {
    "stack":    {"color_mode": "auto", "offset": 0.0},
    "colormap": {"colormap": "RdBu_r", "symmetric": False},
}


def _tracked_keys() -> frozenset[str]:
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
    try:
        return sorted(p.stem for p in templates_dir().glob("*.scet"))
    except Exception:
        return []


def save_template(name: str,
                  widget_type: str,
                  widget_extra: dict) -> Path:
    """
    Merge-save a template file.

    Only the rcparams delta (vs matplotlib defaults) and the current
    widget_type's widget_extra are written.  Other widget types' sections
    from an existing file are preserved unchanged.

    Parameters
    ----------
    name         : template name (filename stem)
    widget_type  : "stack" | "colormap" | …
    widget_extra : current widget-specific extras for widget_type
    """
    import matplotlib as mpl

    path = templates_dir() / f"{name}.scet"

    # load existing file to preserve other widget types' sections
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    else:
        existing = {}

    tracked = _tracked_keys()
    rcparams_delta = {
        k: mpl.rcParams[k]
        for k in tracked
        if k in mpl.rcParams and mpl.rcParams[k] != mpl.rcParamsDefault.get(k)
    }

    widget_extras = existing.get("widget_extras", {})
    widget_extras[widget_type] = dict(widget_extra)

    payload = {
        "version":        _VERSION,
        "rcparams_delta": rcparams_delta,
        "widget_extras":  widget_extras,
    }

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Template saved: %s", path)
    return path


def load_template(name: str) -> tuple[dict, dict[str, dict]]:
    """
    Load a template by name.

    Returns
    -------
    (rcparams_delta, widget_extras)
    rcparams_delta : dict of keys differing from mpl defaults (apply with overlay)
    widget_extras  : dict keyed by widget_type → extras dict
                     missing widget types fall back to WIDGET_EXTRA_DEFAULTS
    """
    path = templates_dir() / f"{name}.scet"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    rcparams_delta = raw.get("rcparams_delta", {})
    widget_extras  = raw.get("widget_extras", {})

    return rcparams_delta, widget_extras


def apply_rcparams(delta: dict) -> None:
    """Apply rcparams_delta: rcdefaults() then overlay."""
    import matplotlib as mpl
    mpl.rcdefaults()
    tracked = _tracked_keys()
    for k, v in delta.items():
        if k in tracked:
            try:
                mpl.rcParams[k] = v
            except Exception as exc:
                log.debug("Could not set rcParam %r = %r: %s", k, v, exc)


def get_widget_extra(widget_extras: dict[str, dict],
                     widget_type: str) -> dict:
    """Return extras for the given widget type, falling back to defaults."""
    defaults = WIDGET_EXTRA_DEFAULTS.get(widget_type, {})
    saved    = widget_extras.get(widget_type, {})
    return {**defaults, **saved}
