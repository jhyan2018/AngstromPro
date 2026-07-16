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


def _auto_offset(y_arr: np.ndarray) -> float:
    """Median peak-to-peak per curve — gives a readable waterfall."""
    if y_arr.shape[0] < 2:
        return 0.0
    ptps = np.nanmax(y_arr, axis=1) - np.nanmin(y_arr, axis=1)
    med = float(np.nanmedian(ptps))
    return med if np.isfinite(med) else 0.0


# ── uds ndim=2 — curve stack / colormap ──────────────────────────────────────

def render_uds_2d(payload, *, rcparams_delta: dict | None = None,
                  options: dict | None = None,
                  figsize: tuple[float, float] = _DEFAULT_FIGSIZE) -> Figure:
    from angstrompro.gui.widgets.curve_stack.prepare import prepare_entry

    options = options or {}
    entry = prepare_entry(getattr(payload, "name", ""), payload)
    x, y_arr = entry["x"], entry["y"]
    n = y_arr.shape[0]
    threshold = int(options.get("stack_threshold", 20))

    with rc_overlay(rcparams_delta or {}):
        fig = Figure(figsize=figsize)
        ax = fig.add_subplot(111)

        if n <= threshold:
            offset = options.get("offset")
            if offset is None:
                offset = _auto_offset(y_arr)
            for i in range(n):
                ax.plot(x, y_arr[i] + i * offset, linewidth=0.8)
        else:
            cmap = options.get("colormap", "RdBu_r")
            z = y_arr
            vmax = float(np.nanmax(np.abs(z))) or 1.0
            ax.pcolormesh(z, cmap=cmap, vmin=-vmax, vmax=vmax,
                          shading="auto", rasterized=True)

        ax.set_xlabel(entry.get("x_label", ""), fontsize=7)
        ax.set_ylabel(entry.get("y_label", ""), fontsize=7)
        ax.tick_params(labelsize=6, direction="in")
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
    # 3D uds layout is (sweep/layer, x, y) — transpose so x runs horizontally
    img = data[layer].T

    with rc_overlay(rcparams_delta or {}):
        fig = Figure(figsize=figsize)
        ax = fig.add_subplot(111)
        cmap = options.get("colormap", "gray")
        ax.imshow(img, cmap=cmap, origin="lower", aspect="equal",
                  interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
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
