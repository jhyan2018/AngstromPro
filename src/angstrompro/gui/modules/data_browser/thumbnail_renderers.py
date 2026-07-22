# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

Built-in headless thumbnail renderers for the Data Browser.

Each renderer takes a payload and returns a fully drawn matplotlib Figure
(Agg-compatible, no Qt).  Registered in the core thumbnail_registry at
import time; plugins register their own payload types the same way.

Payload → thumbnail mapping
---------------------------
uds ndim=2   n_curves <= stack_threshold → overlaid curves with auto offset
             n_curves >  stack_threshold → pcolormesh colormap
uds ndim=3   image of one layer (axis 0 = sweep/layer), default layer 0
scene_plot   full scene via scene_plot_renderer under its own rc delta

Options dict (all optional)
---------------------------
    layer            int   3D layer index                     (default 0)
    channel_id       str   logical ChannelManager display name
    subtract_z_background bool flatten logical Z image thumbnails
    stack_threshold  int   max curves before colormap mode    (default 20)
    offset           float explicit stack offset; None = auto
    colormap         str   cmap for colormap/image mode       (default "RdBu_r")
    widget_extras    dict  template extras (color_mode, colormap, rt anchors…)
"""
from __future__ import annotations

import logging

import numpy as np
from matplotlib.figure import Figure

from angstrompro.core.data.thumbnail_registry import register_thumbnail_renderer
from angstrompro.gui.widgets.curve_stack.template_manager import rc_overlay

log = logging.getLogger(__name__)

_DEFAULT_FIGSIZE = (2.6, 2.6)


# ── helpers ───────────────────────────────────────────────────────────────────

def payload_type_and_ndim(payload) -> tuple[str, int | None]:
    """Return (type_id, ndim) key for the thumbnail registry lookup."""
    type_id = getattr(payload, "type_id", None) or type(payload).__name__
    data = getattr(payload, "data", None)
    ndim = getattr(data, "ndim", None) if data is not None else None
    return type_id, ndim


# ── uds ndim=2 — curve stack / colormap ──────────────────────────────────────

def _rt_cmap(extras: dict):
    if extras.get("use_rt_cmap") and extras.get("rt_anchors"):
        from angstrompro.gui.widgets.curve_stack.rt_cmap import cmap_from_anchors
        return cmap_from_anchors(extras["rt_anchors"])
    return None


def render_uds_2d(payload, *, rcparams_delta: dict | None = None,
                  options: dict | None = None,
                  figsize: tuple[float, float] = _DEFAULT_FIGSIZE) -> Figure:
    """No hardcoded style: everything comes from the rcparams delta and the
    template's per-mode widget_extras (options["widget_extras"]).  One
    template serves both branches — extras["stack"] styles the few-curves
    case, extras["colormap"] the many-curves case."""
    import matplotlib as mpl
    from angstrompro.gui.widgets.curve_stack.prepare import prepare_entry

    options = options or {}
    extras_all = options.get("widget_extras") or {}
    entry = prepare_entry(getattr(payload, "name", ""), payload)
    x, y_arr = entry["x"], entry["y"]
    n = y_arr.shape[0]
    threshold = int(options.get("stack_threshold", 10))

    with rc_overlay(rcparams_delta or {}):
        fig = Figure(figsize=figsize)
        ax = fig.add_subplot(111)

        if n <= threshold:
            ex = extras_all.get("stack", {})
            offset = float(ex.get("offset", 0.0))   # template only; 0 = overlay
            mode = ex.get("color_mode", "auto")
            cmap = _rt_cmap(ex)
            if cmap is None and mode.startswith(("cmap:", "cmap_value")):
                name = mode.split(":", 1)[-1] or "viridis"
                cmap = mpl.colormaps.get(name)
            for i in range(n):
                kw = {}
                if cmap is not None:
                    kw["color"] = cmap(i / max(n - 1, 1))
                ax.plot(x, y_arr[i] + i * offset, **kw)
        else:
            ex = extras_all.get("colormap", {})
            cmap = _rt_cmap(ex) or ex.get("colormap") \
                or mpl.rcParams["image.cmap"]
            z = y_arr
            if ex.get("symmetric", True):
                vmax = float(np.nanmax(np.abs(z))) or 1.0
                vmin = -vmax
            else:
                vmin = float(np.nanmin(z))
                vmax = float(np.nanmax(z))
            ax.pcolormesh(z, cmap=cmap, vmin=vmin, vmax=vmax, shading="auto")

        ax.set_xlabel(entry.get("x_label", ""))
        ax.set_ylabel(entry.get("y_label", ""))
        fig.tight_layout(pad=0.3)
    return fig


# ── uds ndim=3 — image of one layer ──────────────────────────────────────────

def render_uds_3d(payload, *, rcparams_delta: dict | None = None,
                  options: dict | None = None,
                  figsize: tuple[float, float] = _DEFAULT_FIGSIZE) -> Figure:
    options = options or {}
    data = np.asarray(payload.data, dtype=float)
    layer = int(options.get("layer", 0))
    layer = max(0, min(layer, data.shape[0] - 1))
    # Match ImageStackViewer exactly: array rows run vertically, columns run
    # horizontally, and row 0 is displayed at the top.  Do not transpose here;
    # doing so makes Nanonis SXM/3DS thumbnails appear rotated by 90 degrees.
    img = data[layer]
    if options.get("subtract_z_background", False) \
            and options.get("channel_id") == "Z":
        # Presentation-only preprocessing.  The renderer operates on the
        # selected 2D slice and never mutates the source UDS payload.
        # Degenerate line scans and non-finite images retain their raw display
        # rather than allowing an optional preview operation to fail the card.
        if img.ndim == 2 and min(img.shape) > 1 and np.isfinite(img).all():
            from angstrompro.algorithms.background_subtract import (
                _bg_subtract_2d_plane)
            img = _bg_subtract_2d_plane(img, order=1)

    with rc_overlay(rcparams_delta or {}):
        fig = Figure(figsize=figsize)
        ax = fig.add_subplot(111)
        # cmap=None → matplotlib's own default (rcParams "image.cmap",
        # overridable via the template delta)
        ax.imshow(img, cmap=options.get("colormap"), origin="upper",
                  aspect="equal", interpolation="nearest")
        fig.tight_layout(pad=0.1)
    return fig


# ── scene_plot — full scene render ───────────────────────────────────────────

def render_scene_plot(payload, *, rcparams_delta: dict | None = None,
                      options: dict | None = None,
                      figsize: tuple[float, float] = _DEFAULT_FIGSIZE) -> Figure:
    """Render a ScenePlot thumbnail.  The scene's own rcparams_delta wins;
    the caller-supplied delta (browser template) is ignored for scenes."""
    from angstrompro.gui.widgets.scene_plot_renderer import (
        render_scene_to_axes, scene_rc_context)

    fig_cfg = payload.figure
    with scene_rc_context(payload):
        fig = Figure(figsize=figsize)
        gs = fig.add_gridspec(
            fig_cfg.nrows, fig_cfg.ncols,
            hspace=fig_cfg.hspace, wspace=fig_cfg.wspace)
        axes_map: dict = {}
        for idx, ax_spec in enumerate(fig_cfg.axes_list):
            if ax_spec.twin_of >= 0:
                continue   # twins created inside render_scene_to_axes
            axes_map[idx] = fig.add_subplot(
                gs[ax_spec.row: ax_spec.row + ax_spec.rowspan,
                   ax_spec.col: ax_spec.col + ax_spec.colspan],
                projection=ax_spec.projection)
        render_scene_to_axes(payload, axes_map)
        if fig_cfg.suptitle:
            fig.suptitle(fig_cfg.suptitle, fontsize=8)
        for ax in axes_map.values():
            ax.tick_params(labelsize=6)
        fig.tight_layout(pad=0.3)
    return fig


# ── PNG entry point ───────────────────────────────────────────────────────────

def render_payload_to_png(payload, png_path: str, *,
                          rcparams_delta: dict | None = None,
                          options: dict | None = None,
                          figsize: tuple[float, float] = _DEFAULT_FIGSIZE,
                          dpi: int = 100) -> bool:
    """Render *payload* to *png_path* via the registry.  Returns False when
    no renderer is registered for the payload's (type_id, ndim)."""
    from angstrompro.core.data.thumbnail_registry import get_thumbnail_renderer

    type_id, ndim = payload_type_and_ndim(payload)
    renderer = get_thumbnail_renderer(type_id, ndim)
    if renderer is None:
        return False
    fig = renderer(payload, rcparams_delta=rcparams_delta,
                   options=options, figsize=figsize)
    try:
        fig.savefig(png_path, dpi=dpi, facecolor=fig.get_facecolor())
    finally:
        # break the renderer's figure references so Agg buffers are freed
        fig.clear()
    return True


# ── registration ──────────────────────────────────────────────────────────────

register_thumbnail_renderer("uds", 2, render_uds_2d)
register_thumbnail_renderer("uds", 3, render_uds_3d)
register_thumbnail_renderer("scene_plot", None, render_scene_plot)
