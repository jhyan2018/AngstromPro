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

    # ── Color-mode helper (used by line-based widgets) ────────────────────

    def _assign_colors(self, lines: dict) -> None:
        """Apply color_mode to a {key: Line2D} dict.

        No-op for 'auto' (prop_cycle handles it) and for LineCollection modes
        (colors are baked in during _rebuild_lc).
        """
        if not self.color_mode or self.color_mode == "auto":
            return
        if not self.color_mode.startswith("cmap:"):
            return   # LC modes — skip
        import matplotlib as mpl
        import matplotlib.colors as mcolors
        from matplotlib.lines import Line2D
        cmap_name = self.color_mode[5:] or "viridis"
        try:
            cmap = mpl.colormaps[cmap_name]
        except KeyError:
            return
        # only colour Line2D artists — skip LineCollection and manually pinned lines
        manual = getattr(self, "_manual_colors", {})
        line2d_keys = [k for k, v in lines.items()
                       if isinstance(v, Line2D) and k not in manual]
        n = max(len(line2d_keys) - 1, 1)
        for i, key in enumerate(line2d_keys):
            lines[key].set_color(mcolors.to_hex(cmap(i / n)))
