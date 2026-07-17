# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Scene template manager for CurveStackViewer.

Delta model: the viewer's RuntimeScene owns a live ``rcparams_delta`` dict
(JSON-safe, style-prefixed keys only).  Global ``mpl.rcParams`` is never
mutated — rendering wraps in ``rc_context(to_rc(delta))``.

Template file format (.scet, JSON):
  {
    "version": 2,
    "rcparams_delta": { <key>: <value>, ... },
    "widget_extras": {
      "stack":    { "color_mode": "...", "offset": 0.0 },
      "colormap": { "colormap": "RdBu_r", "symmetric": false },
      ...
    }
  }

Save is a full snapshot of both dicts (all modes' widget_extras).
Load replaces both wholesale.  The active plot mode is never stored.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_VERSION = 2

# rcParam prefixes that represent visual appearance
_STYLE_PREFIXES = {
    "lines.", "axes.", "xtick.", "ytick.",
    "legend.", "font.", "image.", "figure.",
    "grid.", "patch.", "text.", "hatch.",
}

# rcParams that conflict with the harness or are irrelevant to appearance.
# figure.figsize / figure.dpi are TRACKED: meaningless on the embedded Qt
# canvas (Qt owns the pixel size) but honored on export and by modules that
# build fresh Figures (SubplotViewer, FigureCompositor).
_EXCLUDED_RCPARAMS = {
    "figure.max_open_warning", "figure.raise_window",
    "backend", "backend_fallback",
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
    "stack":    {"color_mode": "auto", "offset": 0.0,
                 "use_rt_cmap": False, "rt_anchors": []},
    "colormap": {"colormap": "RdBu_r", "symmetric": False,
                 "use_rt_cmap": False, "rt_anchors": []},
}


def _tracked_keys() -> frozenset[str]:
    import matplotlib as mpl
    return frozenset(
        k for k in mpl.rcParamsDefault
        if any(k.startswith(p) for p in _STYLE_PREFIXES)
        and k not in _EXCLUDED_RCPARAMS
    )


# ── Delta helpers ─────────────────────────────────────────────────────────────

def sanitize_delta(delta: dict) -> dict:
    """Drop non-style keys; keep the delta JSON-safe and template-legal."""
    tracked = _tracked_keys()
    return {k: v for k, v in delta.items() if k in tracked}


def to_rc(delta: dict) -> dict:
    """Convert a JSON-safe delta into rc-appliable values.

    ``axes.prop_cycle`` is stored as a plain list of color strings; matplotlib
    wants a Cycler.  All other values pass through unchanged.
    """
    out = dict(delta)
    cyc = out.get("axes.prop_cycle")
    if isinstance(cyc, (list, tuple)):
        from cycler import cycler
        out["axes.prop_cycle"] = cycler(color=list(cyc))
    return out


def rc_overlay(delta: dict):
    """Context manager applying the delta on top of current rcParams.

    Usage::

        with rc_overlay(scene.rcparams_delta):
            ax.clear(); ax.plot(...)
    """
    import matplotlib as mpl
    return mpl.rc_context(to_rc(sanitize_delta(delta)))


# ── Template files ────────────────────────────────────────────────────────────

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
                  rcparams_delta: dict,
                  widget_extras: dict[str, dict]) -> Path:
    """
    Full-snapshot save of a template file.

    Parameters
    ----------
    name           : template name (filename stem)
    rcparams_delta : the viewer's live delta (sanitized here)
    widget_extras  : ALL modes' extras {mode: extras dict}
    """
    path = templates_dir() / f"{name}.scet"

    payload = {
        "version":        _VERSION,
        "rcparams_delta": sanitize_delta(rcparams_delta),
        "widget_extras":  {m: dict(e) for m, e in widget_extras.items()},
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
    rcparams_delta : sanitized style delta — replace the scene's delta with it
    widget_extras  : dict keyed by widget_type → extras dict
                     missing widget types fall back to WIDGET_EXTRA_DEFAULTS
    """
    path = templates_dir() / f"{name}.scet"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    rcparams_delta = sanitize_delta(raw.get("rcparams_delta", {}))
    widget_extras  = raw.get("widget_extras", {})

    return rcparams_delta, widget_extras


def get_widget_extra(widget_extras: dict[str, dict],
                     widget_type: str) -> dict:
    """Return extras for the given widget type, falling back to defaults."""
    defaults = WIDGET_EXTRA_DEFAULTS.get(widget_type, {})
    saved    = widget_extras.get(widget_type, {})
    return {**defaults, **saved}
