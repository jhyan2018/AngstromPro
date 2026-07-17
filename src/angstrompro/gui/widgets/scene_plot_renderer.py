# -*- coding: utf-8 -*-
"""
Created on 2026-07-14

@author: jiahaoYan

Standalone renderer: paint a ScenePlot (or a single AxesSpec) onto
existing matplotlib Axes.  Used by SubplotViewer and FigureCompositor;
no Qt dependency, no widget state.

Top-level design
----------------
render_axes_spec(ax_spec, ax)
    reads ax_spec.extra["plot_mode"] and dispatches to:

    _render_stack(ax_spec, ax)       — plot_mode == "stack" (default)
        reads widget_extras["stack"]: color_mode, offset
        for each line artist / row:
            applies cumulative offset
        post-render color assignment:
            auto           → pinned style.color or prop_cycle
            cmap:<name>    → gradient over line index (Line2D)
            cmap_value*    → LineCollection per-point color

    _render_colormap(ax_spec, ax)    — plot_mode == "colormap"
        reads widget_extras["colormap"]: colormap, symmetric
        collects all visible rows → z matrix → pcolormesh + colorbar

Both paths call _apply_axes_config(cfg, ax) at the end.
Non-line artist kinds (scatter, image, …) always go through _render_artist.
"""
from __future__ import annotations

import logging
import numpy as np

log = logging.getLogger(__name__)


# ── Public entry points ───────────────────────────────────────────────────────

def scene_rc_context(scene_plot):
    """rc_context overlaying the scene's rcparams_delta.

    Wrap every render_* call in this so the scene's saved style (fonts,
    tick direction, grid defaults, prop cycle, …) applies without mutating
    global mpl.rcParams::

        with scene_rc_context(scene):
            render_axes_spec(scene.figure.axes_list[0], ax)
    """
    from angstrompro.gui.widgets.curve_stack.template_manager import rc_overlay
    return rc_overlay(getattr(scene_plot, "rcparams_delta", None) or {})


def render_axes_spec(ax_spec, ax) -> None:
    """Draw one AxesSpec onto *ax*, honouring plot_mode and widget_extras."""
    ax.clear()
    plot_mode = ax_spec.extra.get("plot_mode", "stack")
    if plot_mode == "colormap":
        _render_colormap(ax_spec, ax)
    else:
        _render_stack(ax_spec, ax)
    _apply_axes_config(ax_spec.config, ax)


def render_scene_to_axes(scene_plot, axes_map: dict) -> None:
    """Render a ScenePlot onto {axes_index: matplotlib_Axes}.

    Twin axes (twin_of >= 0) are created here via twinx/twiny; the caller
    must not supply a pre-built ax for them.
    """
    for idx, ax_spec in enumerate(scene_plot.figure.axes_list):
        if ax_spec.twin_of >= 0:
            parent_ax = axes_map.get(ax_spec.twin_of)
            if parent_ax is None:
                continue
            twin_fn = parent_ax.twinx if ax_spec.twin_axis == "y" else parent_ax.twiny
            render_axes_spec(ax_spec, twin_fn())
        else:
            target = axes_map.get(idx)
            if target is not None:
                render_axes_spec(ax_spec, target)


# ── Stack mode ────────────────────────────────────────────────────────────────

def _render_stack(ax_spec, ax) -> None:
    """Render all line artists with offset + color_mode, twin-Y, from widget_extras."""
    extras     = ax_spec.extra.get("widget_extras", {}).get("stack", {})
    color_mode = extras.get("color_mode", "auto")
    offset     = float(extras.get("offset", 0.0))
    is_lc_mode = color_mode.startswith("cmap_value")
    rt_cmap    = _rt_cmap_from_extras(extras)   # None unless RT is enabled

    ax2 = None   # right twin-Y axis, created lazily

    # gather entries in order so we know global_idx per row
    entries = []   # (artist, entry, row_i, g_idx, vis, side)
    global_idx = 0
    for artist in ax_spec.artists:
        if artist.kind != "line" or artist.data is None:
            _render_artist(artist, ax)
            continue
        entry   = _prepare(artist)
        y_2d    = entry["y"]
        row_vis = artist.extra.get("row_visibility", None)
        side    = artist.extra.get("y_axis", "left")
        n       = y_2d.shape[0]
        for i in range(n):
            vis = artist.visible
            if row_vis is not None and i < len(row_vis):
                vis = bool(row_vis[i]) and artist.visible
            entries.append((artist, entry, i, global_idx, vis, side))
            global_idx += 1

    # create twin axis only if any artist is on the right
    if any(side == "right" for *_, side in entries):
        ax2 = ax.twinx()

    lines_l = []   # (artist_obj, g_idx) on left  — for color assignment
    lines_r = []   # (artist_obj, g_idx) on right
    x_label = y_label_l = y_label_r = ""

    for artist, entry, row_i, g_idx, vis, side in entries:
        s      = artist.style
        x      = entry["x"]
        y_2d   = entry["y"]
        y_raw  = y_2d[row_i] if y_2d.ndim > 1 else y_2d
        y_row  = y_raw + g_idx * offset
        label  = artist.label if row_i == 0 else "_"
        target = ax2 if (side == "right" and ax2 is not None) else ax
        x_label = x_label or entry.get("x_label", "")
        if side == "right":
            y_label_r = y_label_r or entry.get("y_label", "")
        else:
            y_label_l = y_label_l or entry.get("y_label", "")

        if is_lc_mode:
            lc = _make_lc(x, y_row, y_raw, color_mode,
                          norm=None, lw=None, visible=vis, rt_cmap=rt_cmap)
            target.add_collection(lc)
            (lines_r if side == "right" else lines_l).append((lc, g_idx))
        else:
            kw = dict(label=label, visible=vis)
            if s.color:       kw["color"]      = s.color
            if s.linewidth:   kw["linewidth"]   = s.linewidth
            if s.linestyle:   kw["linestyle"]   = s.linestyle
            if s.marker:      kw["marker"]      = s.marker
            if s.markersize:  kw["markersize"]  = s.markersize
            if artist.alpha:  kw["alpha"]       = artist.alpha
            if artist.zorder: kw["zorder"]      = artist.zorder
            if s.step_where:
                ln, = target.step(x, y_row, where=s.step_where, **kw)
            else:
                ln, = target.plot(x, y_row, **kw)
            (lines_r if side == "right" else lines_l).append((ln, g_idx))

    # axis labels
    if x_label and not ax.get_xlabel():
        ax.set_xlabel(x_label)
    if y_label_l and not ax.get_ylabel():
        ax.set_ylabel(y_label_l)
    if y_label_r and ax2 is not None and not ax2.get_ylabel():
        ax2.set_ylabel(y_label_r)

    all_lines = lines_l + lines_r
    if is_lc_mode:
        ax.autoscale_view()
        if ax2 is not None:
            ax2.autoscale_view()
        _apply_lc_global_norm(all_lines, color_mode)
    else:
        _apply_line_colors(all_lines, color_mode, rt_cmap=rt_cmap)

    # sync twin position after tight_layout (caller handles tight_layout)
    if ax2 is not None:
        ax2.set_position(ax.get_position())


def _rt_cmap_from_extras(extras: dict):
    """Anchor-built Colormap from widget extras, or None when RT is off."""
    if extras.get("use_rt_cmap") and extras.get("rt_anchors"):
        from angstrompro.gui.widgets.curve_stack.rt_cmap import cmap_from_anchors
        return cmap_from_anchors(extras["rt_anchors"])
    return None


def _apply_line_colors(lines: list, color_mode: str, rt_cmap=None) -> None:
    """Assign colors to Line2D objects based on color_mode."""
    import matplotlib as mpl
    import matplotlib.colors as mcolors

    if color_mode == "auto" or not color_mode:
        # colors already set per-line via style.color; fill gaps with prop_cycle
        cycle = mpl.rcParams["axes.prop_cycle"].by_key().get("color") or ["C0"]
        for i, (ln, _) in enumerate(lines):
            if not ln.get_color() or ln.get_color() in ("", "None"):
                ln.set_color(cycle[i % len(cycle)])
        return

    if not color_mode.startswith("cmap:"):
        return

    if rt_cmap is not None:
        cmap = rt_cmap
    else:
        cmap_name = color_mode[5:] or "viridis"
        try:
            cmap = mpl.colormaps[cmap_name]
        except KeyError:
            return
    n = max(len(lines) - 1, 1)
    for i, (ln, _) in enumerate(lines):
        ln.set_color(mcolors.to_hex(cmap(i / n)))


def _apply_lc_global_norm(lines: list, color_mode: str) -> None:
    """For cmap_value_global: recompute norm over all LCs and reapply."""
    import matplotlib.colors as mcolors
    from matplotlib.collections import LineCollection

    if not color_mode.startswith("cmap_value_global:"):
        return   # per-line norm already set in _make_lc

    all_arrays = [lc.get_array() for lc, _ in lines
                  if isinstance(lc, LineCollection) and lc.get_array() is not None]
    if not all_arrays:
        return
    gmin = min(a.min() for a in all_arrays)
    gmax = max(a.max() for a in all_arrays)
    norm = mcolors.Normalize(gmin, gmax)
    for lc, _ in lines:
        if isinstance(lc, LineCollection):
            lc.set_norm(norm)


def _make_lc(x, y_plot, y_color, color_mode: str, norm, lw, visible,
             rt_cmap=None):
    import matplotlib as mpl
    import matplotlib.colors as mcolors
    from matplotlib.collections import LineCollection

    if rt_cmap is not None:
        cmap_name = rt_cmap   # anchor-built Colormap object
    else:
        for prefix in ("cmap_value_global:", "cmap_value:"):
            if color_mode.startswith(prefix):
                cmap_name = color_mode[len(prefix):] or "viridis"
                break
        else:
            cmap_name = "viridis"

    if norm is None:
        norm = mcolors.Normalize(y_color.min(), y_color.max())
    if lw is None:
        lw = mpl.rcParams.get("lines.linewidth", 1.0)

    pts      = np.column_stack([x, y_plot]).reshape(-1, 1, 2)
    segments = np.concatenate([pts[:-1], pts[1:]], axis=1)
    lc = LineCollection(segments, cmap=cmap_name, norm=norm,
                        linewidth=lw, visible=visible)
    lc.set_array(y_color)
    return lc


# ── Colormap mode ─────────────────────────────────────────────────────────────

def _render_colormap(ax_spec, ax) -> None:
    """Render all line artists as a 2D pcolormesh (ColormapPlotWidget style)."""
    extras    = ax_spec.extra.get("widget_extras", {}).get("colormap", {})
    symmetric = bool(extras.get("symmetric", True))
    # RT anchor-based colormap takes priority over the palette name
    cmap_name = (_rt_cmap_from_extras(extras)
                 or extras.get("colormap", "RdBu_r"))

    rows       = []
    row_vals   = []
    x_arr      = None
    x_label    = y_label = row_label = ""
    has_row_ax = True

    for artist in ax_spec.artists:
        if artist.kind != "line" or artist.data is None:
            continue
        entry   = _prepare(artist)
        y_2d    = entry["y"]
        rv      = entry.get("row_values")
        checked = artist.extra.get("row_visibility",
                                   [artist.visible] * y_2d.shape[0])
        for i, vis in enumerate(checked):
            if not vis:
                continue
            rows.append(y_2d[i] if y_2d.ndim > 1 else y_2d)
            if rv is not None and i < len(rv):
                row_vals.append(float(rv[i]))
            else:
                has_row_ax = False
        if x_arr is None:
            x_arr = entry["x"]
        x_label  = x_label  or entry.get("x_label", "")
        y_label  = y_label  or entry.get("y_label", "")
        row_label = row_label or entry.get("row_label", "")

    if not rows or x_arr is None:
        return

    z      = np.vstack([r[np.newaxis, :] for r in rows])
    n_rows = z.shape[0]

    if symmetric:
        vmax = float(np.nanmax(np.abs(z)))
        vmin = -vmax
    else:
        vmin = float(np.nanmin(z))
        vmax = float(np.nanmax(z))

    dx = (x_arr[1] - x_arr[0]) if len(x_arr) > 1 else 1.0
    x_edges = np.empty(len(x_arr) + 1)
    x_edges[:-1] = x_arr - dx / 2
    x_edges[-1]  = x_arr[-1] + dx / 2

    if has_row_ax and len(row_vals) == n_rows:
        rv_arr  = np.array(row_vals)
        dy      = (rv_arr[1] - rv_arr[0]) if n_rows > 1 else 1.0
        y_edges = np.empty(n_rows + 1)
        y_edges[:-1] = rv_arr - dy / 2
        y_edges[-1]  = rv_arr[-1] + dy / 2
        y_axis_label = row_label
    else:
        y_edges      = np.arange(n_rows + 1) - 0.5
        y_axis_label = ""

    mesh = ax.pcolormesh(x_edges, y_edges, z,
                         cmap=cmap_name, vmin=vmin, vmax=vmax, shading="flat")
    cb = ax.get_figure().colorbar(mesh, ax=ax)
    cb.set_label(y_label)

    if x_label:
        ax.set_xlabel(x_label)
    if y_axis_label:
        ax.set_ylabel(y_axis_label)

    ax.minorticks_on()
    ax.tick_params(axis="both", which="both", direction="in")


# ── Non-line artists ──────────────────────────────────────────────────────────

def _render_artist(artist, ax) -> None:
    kind = artist.kind
    if kind == "scatter":
        _render_scatter(artist, ax)
    elif kind == "image":
        _render_image(artist, ax)
    elif kind == "contour":
        _render_contour(artist, ax)
    elif kind == "fill":
        _render_fill(artist, ax)
    elif kind == "bar":
        _render_bar(artist, ax)
    elif kind == "errorbar":
        _render_errorbar(artist, ax)
    elif kind == "text":
        _render_text(artist, ax)
    elif kind == "patch":
        _render_patch(artist, ax)


def _prepare(artist) -> dict:
    from angstrompro.gui.widgets.curve_stack.prepare import prepare_entry
    return prepare_entry(artist.label or artist.data.name, artist.data)


def _render_scatter(artist, ax) -> None:
    if artist.data is None:
        return
    s    = artist.style
    data = artist.data.data
    x    = data[:, artist.x_col]
    y_c  = [c for c in range(data.shape[1]) if c != artist.x_col]
    y    = data[:, y_c[0]] if y_c else data[:, 0]
    kw   = dict(label=artist.label, visible=artist.visible,
                cmap=s.cmap, marker=s.marker)
    if s.color:      kw["c"]          = s.color
    if s.vmin:       kw["vmin"]       = s.vmin
    if s.vmax:       kw["vmax"]       = s.vmax
    if s.s:          kw["s"]          = s.s
    if s.edgecolors: kw["edgecolors"] = s.edgecolors
    if artist.alpha: kw["alpha"]      = artist.alpha
    if artist.zorder:kw["zorder"]     = artist.zorder
    ax.scatter(x, y, **kw)


def _render_image(artist, ax) -> None:
    if artist.data is None:
        return
    s   = artist.style
    raw = artist.data.data
    kw  = dict(cmap=s.cmap, aspect=s.aspect)
    if s.vmin:        kw["vmin"]  = s.vmin
    if s.vmax:        kw["vmax"]  = s.vmax
    if artist.alpha:  kw["alpha"] = artist.alpha
    if artist.zorder: kw["zorder"]= artist.zorder
    if s.render == "imshow":
        kw.update(interpolation=s.interpolation, origin=s.origin)
        ax.imshow(raw, **kw)
    else:
        ax.pcolormesh(raw, **kw)


def _render_contour(artist, ax) -> None:
    if artist.data is None:
        return
    s   = artist.style
    raw = artist.data.data
    kw  = dict(levels=s.levels, cmap=s.cmap or None)
    if s.colors:      kw["colors"] = s.colors; kw.pop("cmap", None)
    if s.linewidths:  kw["linewidths"] = s.linewidths
    if artist.alpha:  kw["alpha"]      = artist.alpha
    (ax.contourf if s.filled else ax.contour)(raw, **kw)


def _render_fill(artist, ax) -> None:
    if artist.data is None:
        return
    s  = artist.style
    d  = artist.data.data
    kw = dict(label=artist.label, visible=artist.visible)
    if s.facecolor: kw["facecolor"] = s.facecolor
    if s.edgecolor: kw["edgecolor"] = s.edgecolor
    if s.hatch:     kw["hatch"]     = s.hatch
    if artist.alpha:kw["alpha"]     = artist.alpha
    fn = ax.fill_betweenx if s.horizontal else ax.fill_between
    fn(d[:, s.x_col], d[:, s.y1_col], d[:, s.y2_col], **kw)


def _render_bar(artist, ax) -> None:
    if artist.data is None:
        return
    s  = artist.style
    d  = artist.data.data
    kw = dict(label=artist.label, visible=artist.visible)
    if s.color:     kw["color"]     = s.color
    if s.edgecolor: kw["edgecolor"] = s.edgecolor
    if s.width:     kw["width" if not s.horizontal else "height"] = s.width
    if artist.alpha:kw["alpha"]     = artist.alpha
    (ax.barh if s.horizontal else ax.bar)(d[:, s.x_col], d[:, s.y_col], **kw)


def _render_errorbar(artist, ax) -> None:
    if artist.data is None:
        return
    s  = artist.style
    d  = artist.data.data
    kw = dict(label=artist.label, visible=artist.visible, fmt=s.marker or "o")
    if s.yerr_col is not None and s.yerr_col < d.shape[1]:
        kw["yerr"] = d[:, s.yerr_col]
    elif s.yerr_data is not None:
        kw["yerr"] = s.yerr_data.data[:, min(s.yerr_data_col,
                                              s.yerr_data.data.shape[1]-1)]
    if s.xerr_col is not None and s.xerr_col < d.shape[1]:
        kw["xerr"] = d[:, s.xerr_col]
    elif s.xerr_data is not None:
        kw["xerr"] = s.xerr_data.data[:, min(s.xerr_data_col,
                                              s.xerr_data.data.shape[1]-1)]
    if s.color:     kw["color"]    = s.color
    if s.linewidth: kw["linewidth"]= s.linewidth
    if s.capsize:   kw["capsize"]  = s.capsize
    if s.ecolor:    kw["ecolor"]   = s.ecolor
    if s.markersize:kw["markersize"]= s.markersize
    if artist.alpha:kw["alpha"]    = artist.alpha
    ax.errorbar(d[:, s.x_col], d[:, s.y_col], **kw)


def _render_text(artist, ax) -> None:
    s  = artist.style
    kw = dict(ha=s.ha, va=s.va, rotation=s.rotation)
    if s.fontsize:  kw["fontsize"] = s.fontsize
    if s.color:     kw["color"]    = s.color
    if s.bbox:      kw["bbox"]     = s.bbox
    if artist.alpha:kw["alpha"]    = artist.alpha
    if s.xy_arrow is not None:
        ax.annotate(s.s, xy=s.xy_arrow, xytext=(s.x, s.y), **kw)
    else:
        ax.text(s.x, s.y, s.s, **kw)


def _render_patch(artist, ax) -> None:
    import matplotlib.patches as mpatches
    s  = artist.style
    ex = s.extra
    kw = dict()
    if s.facecolor: kw["facecolor"] = s.facecolor
    if s.edgecolor: kw["edgecolor"] = s.edgecolor
    if s.linewidth: kw["linewidth"] = s.linewidth
    if s.hatch:     kw["hatch"]     = s.hatch
    if artist.alpha:kw["alpha"]     = artist.alpha
    if artist.zorder:kw["zorder"]   = artist.zorder
    t = s.patch_type
    if t == "rectangle":
        patch = mpatches.Rectangle(
            (s.x, s.y), ex.get("width", 1.0), ex.get("height", 1.0), **kw)
    elif t == "circle":
        patch = mpatches.Circle((s.x, s.y), ex.get("radius", 0.5), **kw)
    elif t == "ellipse":
        patch = mpatches.Ellipse(
            (s.x, s.y), ex.get("width", 1.0), ex.get("height", 0.5),
            angle=ex.get("angle", 0.0), **kw)
    else:
        return
    ax.add_patch(patch)


# ── AxesConfig ────────────────────────────────────────────────────────────────

def _apply_axes_config(cfg, ax) -> None:
    if cfg.title:  ax.set_title(cfg.title)
    if cfg.xlabel: ax.set_xlabel(cfg.xlabel)
    if cfg.ylabel: ax.set_ylabel(cfg.ylabel)
    if cfg.xscale and cfg.xscale != "linear": ax.set_xscale(cfg.xscale)
    if cfg.yscale and cfg.yscale != "linear": ax.set_yscale(cfg.yscale)
    if cfg.xlim:   ax.set_xlim(tuple(cfg.xlim))
    if cfg.ylim:   ax.set_ylim(tuple(cfg.ylim))
    # grid: None = untouched → the scene's rcparams delta decides (axes.grid
    # is consumed at ax.clear() inside scene_rc_context); explicit bool wins
    if cfg.grid is not None:
        ax.grid(False, which="both")
        if cfg.grid:
            ax.grid(True, which=cfg.grid_which or "major",
                    linestyle="--", alpha=0.4)
    if cfg.legend:
        try:
            ax.legend(loc=cfg.legend_loc or "best")
        except Exception:
            pass
    if cfg.aspect and cfg.aspect != "auto":
        ax.set_aspect(cfg.aspect)
