# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Abstract base for all CurveStackViewer plot widgets.
Each concrete subclass owns its own Figure, Axes, and mode-specific controls.
"""
from __future__ import annotations

from abc import abstractmethod

from angstrompro.utils.qt_compat import QtWidgets


class BasePlotWidget(QtWidgets.QWidget):
    """
    Contract every plot mode widget must fulfil.

    The container (CurveStackViewerWidget) calls these methods when the
    dataset list or visibility changes.  Each subclass decides how to render.

    Granular API (preferred — avoids unnecessary full redraws)
    ----------------------------------------------------------
    add_lines(name, entry, checked_list)  — new dataset arrived
    remove_lines(name)                    — dataset was removed
    set_line_visible(name, idx, visible)  — one curve toggled
    set_all_visible(name, visible)        — parent checkbox toggled

    Default implementations fall back to refresh() so subclasses only need
    to override what they can do cheaply.  StackPlotWidget overrides all
    four; ColormapPlotWidget inherits the defaults (pcolormesh always needs
    a full rebuild).

    Full-redraw API (use when data or rcParams changed)
    ---------------------------------------------------
    refresh(datasets, checked)  — rebuild everything from scratch
    clear()                     — wipe the canvas

    Entry dict shape (produced by prepare_entry)::

        {
            "uds":     UdsDataStru,
            "x":       np.ndarray  (n_pts,)
            "x_label": str
            "y":       np.ndarray  (n_curves, n_pts)
            "y_label": str
        }
    """

    def __init__(self, config: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self._config:      dict                  = config or {}
        self._datasets:    dict[str, dict]       = {}
        self._checked:     dict[str, list[bool]] = {}
        self.color_mode:   str                   = "auto"  # "auto" | "cmap:<name>"
        # scene providers — set by CurveStackViewerWidget; pull-only accessors
        # into the RuntimeScene (single source of truth)
        self.axes_config_provider = None   # () -> AxesConfig | None
        self.row_styles_provider  = None   # () -> {(ds_name, row): props dict}
        self.rcparams_provider    = None   # () -> dict (scene rcparams_delta)

    # ── rcParams delta (scene-owned style) ────────────────────────────────

    def _rc(self):
        """rc_context overlaying the scene's rcparams_delta.

        Every artist-creating rebuild must run inside this context so the
        scene's style applies without ever mutating global mpl.rcParams.
        """
        from .template_manager import rc_overlay
        delta = self.rcparams_provider() if self.rcparams_provider else {}
        return rc_overlay(delta or {})

    def _apply_fig_style(self) -> None:
        """Apply Figure-level style the axes rebuild can't reach.

        The Figure predates any delta change, so its facecolor must be set
        explicitly.  Call inside the _rc() context.
        """
        import matplotlib as mpl
        fig = getattr(self, "_fig", None)
        if fig is not None:
            fig.set_facecolor(mpl.rcParams["figure.facecolor"])

    def _apply_axes_face_style(self, ax) -> None:
        """Axes style that ax.clear() does NOT re-read from rcParams.

        Axes.clear() re-applies the facecolor captured at Axes creation, so
        delta changes to axes.facecolor / edgecolor / linewidth must be
        pushed explicitly.  Call inside the _rc() context, after ax.clear().
        """
        import matplotlib as mpl
        if ax is None:
            return
        ax.set_facecolor(mpl.rcParams["axes.facecolor"])
        for spine in ax.spines.values():
            spine.set_edgecolor(mpl.rcParams["axes.edgecolor"])
            spine.set_linewidth(mpl.rcParams["axes.linewidth"])

    # ── Full-redraw API ───────────────────────────────────────────────────

    @abstractmethod
    def refresh(self, datasets: dict[str, dict],
                checked: dict[str, list[bool]]) -> None:
        """Redraw from the current datasets and visibility flags."""

    @abstractmethod
    def clear(self) -> None:
        """Wipe the canvas."""

    def apply_config(self, config: dict) -> None:
        self._config = config

    # ── Granular API (default: fall back to refresh) ──────────────────────

    def add_lines(self, name: str, entry: dict,
                  checked_list: list[bool]) -> None:
        """Add one dataset.  Override for O(new_curves) instead of O(all)."""
        self._datasets[name] = entry
        self._checked[name]  = checked_list
        self.refresh(self._datasets, self._checked)

    def remove_lines(self, name: str) -> None:
        """Remove one dataset.  Override to avoid full rebuild if possible."""
        self._datasets.pop(name, None)
        self._checked.pop(name, None)
        self.refresh(self._datasets, self._checked)

    def set_line_visible(self, name: str, idx: int, visible: bool) -> None:
        """Toggle one curve.  Override to call line.set_visible() directly."""
        if name in self._checked:
            self._checked[name][idx] = visible
        self.refresh(self._datasets, self._checked)

    def set_all_visible(self, name: str, visible: bool) -> None:
        """Toggle all curves of a dataset.  Override for O(n) set_visible."""
        if name in self._checked:
            self._checked[name] = [visible] * len(self._checked[name])
        self.refresh(self._datasets, self._checked)

    # ── Scene pull helpers ────────────────────────────────────────────────

    def _row_style_pins(self) -> dict:
        """Per-line style pins {(ds_name, row): props} from the scene."""
        provider = self.row_styles_provider
        return provider() if provider is not None else {}

    def _apply_axes_config(self) -> None:
        """Overlay the scene's AxesSpec.config onto the live ax.

        Only non-default fields are applied so data-driven defaults
        (dataset axis labels, autoscale) survive when not overridden.
        Called at the end of every rebuild, after ax.clear().
        """
        provider = self.axes_config_provider
        ax = getattr(self, "_ax", None)
        if provider is None or ax is None:
            return
        cfg = provider()
        if cfg is None:
            return
        if cfg.title:
            ax.set_title(cfg.title)
        if cfg.xlabel:
            ax.set_xlabel(cfg.xlabel)
        if cfg.ylabel:
            ax.set_ylabel(cfg.ylabel)
        if cfg.xscale and cfg.xscale != "linear":
            ax.set_xscale(cfg.xscale)
        if cfg.yscale and cfg.yscale != "linear":
            ax.set_yscale(cfg.yscale)
        if cfg.xlim:
            ax.set_xlim(tuple(cfg.xlim))
        if cfg.ylim:
            ax.set_ylim(tuple(cfg.ylim))
        # grid: None = untouched → the rcParams delta decides (axes.grid is
        # consumed by ax.clear() inside rc_context); explicit bool overrides
        if cfg.grid is not None:
            ax.grid(False, which="both")   # clear previous grid state first
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

    def _apply_house_ticks(self, ax) -> None:
        """Explicit tick styling from the delta (house default: in-facing).

        Tick objects are created lazily at DRAW time — outside the _rc()
        context — so rc_context alone never reaches them.  All tick keys in
        the delta must be pushed through tick_params explicitly.
        """
        delta = (self.rcparams_provider() if self.rcparams_provider else {}) or {}
        if ax is None:
            return
        for axis in ("x", "y"):
            p = f"{axis}tick"
            direction = delta.get(f"{p}.direction", "in")
            major: dict = {"direction": direction}
            minor: dict = {"direction": direction}
            if f"{p}.major.size" in delta:
                major["length"] = delta[f"{p}.major.size"]
            if f"{p}.minor.size" in delta:
                minor["length"] = delta[f"{p}.minor.size"]
            if f"{p}.major.width" in delta:
                major["width"] = delta[f"{p}.major.width"]
            if f"{p}.minor.width" in delta:
                minor["width"] = delta[f"{p}.minor.width"]
            if f"{p}.labelsize" in delta:
                major["labelsize"] = delta[f"{p}.labelsize"]
            if f"{p}.color" in delta:
                major["color"] = delta[f"{p}.color"]
                minor["color"] = delta[f"{p}.color"]
            ax.tick_params(axis=axis, which="major", **major)
            ax.tick_params(axis=axis, which="minor", **minor)

    def _resolve_cmap(self, name: str):
        """Colormap lookup hook — widgets with an RT control override this."""
        import matplotlib as mpl
        try:
            return mpl.colormaps[name]
        except KeyError:
            return None

    # ── Color-mode helper (used by line-based widgets) ────────────────────

    def _assign_colors(self, lines: dict) -> None:
        """Apply color_mode to a {key: Line2D} dict.

        auto      — prop_cycle order; manual per-line pins apply here ONLY.
        cmap:*    — colormap gradient over line index; pins are ignored.
        LC modes  — no-op (colors baked into the collections in _rebuild_lc).
        """
        import matplotlib as mpl
        import matplotlib.colors as mcolors
        from matplotlib.lines import Line2D

        line2d = [(k, v) for k, v in lines.items() if isinstance(v, Line2D)]

        if not self.color_mode or self.color_mode == "auto":
            # actively re-assign so switching back from a cmap mode works;
            # scene color pins apply in auto mode only
            pins = self._row_style_pins()
            # prop_cycle must come from the scene delta, not global state —
            # _assign_colors is also called outside rebuilds (set_color_mode)
            with self._rc():
                cycle = (mpl.rcParams["axes.prop_cycle"].by_key().get("color")
                         or ["C0"])
            for i, (key, ln) in enumerate(line2d):
                pinned = pins.get(key, {}).get("color", "")
                ln.set_color(pinned or cycle[i % len(cycle)])
            return

        if not self.color_mode.startswith("cmap:"):
            return   # LC modes — skip

        cmap = self._resolve_cmap(self.color_mode[5:] or "viridis")
        if cmap is None:
            return
        n = max(len(line2d) - 1, 1)
        for i, (key, ln) in enumerate(line2d):
            ln.set_color(mcolors.to_hex(cmap(i / n)))
