# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Colormap (2D heatmap) plot widget.

Rows    = curves (dataset order, top-to-bottom)
Columns = x-axis (bias / energy / …)
Color   = y signal value

Uses pcolormesh so each dataset can have its own x spacing.
A colorbar is created once and removed cleanly on mode switch / clear.
"""
from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .nav_toolbar import NavToolbar

from angstrompro.utils.qt_compat import QtWidgets

from .base_plot_widget import BasePlotWidget

_CMAPS = [
    "RdBu_r", "seismic", "bwr",
    "viridis", "plasma", "inferno",
    "coolwarm", "PiYG", "PRGn",
    "gray", "hot",
]


class ColormapPlotWidget(BasePlotWidget):
    """2D colormap view: curves stacked as rows, signal encoded as color."""

    def __init__(self, config: dict | None = None, parent=None) -> None:
        super().__init__(config, parent)
        self._colorbar = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── controls ──────────────────────────────────────────────────────
        ctrl = QtWidgets.QHBoxLayout()
        ctrl.setContentsMargins(4, 4, 4, 2)
        ctrl.setSpacing(8)

        ctrl.addWidget(QtWidgets.QLabel("Colormap:"))
        self._cmap_combo = QtWidgets.QComboBox()
        for name in _CMAPS:
            self._cmap_combo.addItem(name)
        self._cmap_combo.setCurrentText(
            self._config.get("default_cmap", "RdBu_r"))
        self._cmap_combo.currentTextChanged.connect(self._on_cmap_changed)
        ctrl.addWidget(self._cmap_combo)

        ctrl.addWidget(QtWidgets.QLabel("Symmetrical:"))
        self._sym_check = QtWidgets.QCheckBox()
        self._sym_check.setChecked(True)
        self._sym_check.setToolTip(
            "Force colormap range to be symmetric around zero")
        self._sym_check.stateChanged.connect(self._on_sym_changed)
        ctrl.addWidget(self._sym_check)

        ctrl.addStretch()
        layout.addLayout(ctrl)

        # ── canvas ────────────────────────────────────────────────────────
        self._fig    = Figure(tight_layout=True)
        self._ax     = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding)
        self._canvas.setMinimumSize(1, 1)
        self._navbar = NavToolbar(self._canvas, self)
        layout.addWidget(self._navbar)
        layout.addWidget(self._canvas)

    # ── BasePlotWidget interface ──────────────────────────────────────────

    def refresh(self, datasets: dict[str, dict],
                checked: dict[str, list[bool]]) -> None:
        self._datasets = datasets
        self._checked  = checked
        self._rebuild_plot()

    def clear(self) -> None:
        self._remove_colorbar()
        self._ax.clear()
        self._canvas.draw_idle()

    def apply_config(self, config: dict) -> None:
        super().apply_config(config)
        cmap = config.get("default_cmap")
        if cmap and isinstance(cmap, str) \
                and self._cmap_combo.findText(cmap) >= 0:
            self._cmap_combo.setCurrentText(cmap)
        self._rebuild_plot()

    def set_cmap_palette(self, names: list[str]) -> None:
        """Repopulate the colormap combo from the user's preference list."""
        current = self._cmap_combo.currentText()
        self._cmap_combo.blockSignals(True)
        self._cmap_combo.clear()
        self._cmap_combo.addItems(names)
        idx = self._cmap_combo.findText(current)
        self._cmap_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._cmap_combo.blockSignals(False)
        # selection may have changed — repaint with the new cmap
        if self._cmap_combo.currentText() != current:
            self._rebuild_plot()

    # ── Drawing ───────────────────────────────────────────────────────────

    def _rebuild_plot(self) -> None:
        self._remove_colorbar()
        self._ax.clear()

        # collect visible rows across all datasets
        rows:       list[np.ndarray] = []
        row_vals:   list[float] = []        # physical row positions when available
        x_arr:      np.ndarray | None = None
        x_label     = ""
        y_label     = ""
        row_label   = ""
        has_row_axis = True   # stays True only when every entry has matching row_values

        for name, entry in self._datasets.items():
            y_data   = entry["y"]
            x_data   = entry["x"]
            rv       = entry.get("row_values")   # np.ndarray or None
            checked  = self._checked.get(name, [True] * y_data.shape[0])
            n        = y_data.shape[0]

            for i, visible in enumerate(checked):
                if not visible:
                    continue
                rows.append(y_data[i])
                if rv is not None and i < len(rv):
                    row_vals.append(float(rv[i]))
                else:
                    has_row_axis = False

            if x_arr is None:
                x_arr = x_data
            x_label   = entry.get("x_label", "")
            y_label   = entry.get("y_label", "")
            if not row_label:
                row_label = entry.get("row_label", "")

        if not rows or x_arr is None:
            self._canvas.draw_idle()
            return

        z      = np.vstack([r[np.newaxis, :] for r in rows])  # (n_rows, n_pts)
        n_rows = z.shape[0]

        cmap = self._cmap_combo.currentText()
        if self._sym_check.isChecked():
            vmax = float(np.nanmax(np.abs(z)))
            vmin = -vmax
        else:
            vmin = float(np.nanmin(z))
            vmax = float(np.nanmax(z))

        # x cell edges
        x_edges = np.empty(len(x_arr) + 1)
        dx = (x_arr[1] - x_arr[0]) if len(x_arr) > 1 else 1.0
        x_edges[:-1] = x_arr - dx / 2
        x_edges[-1]  = x_arr[-1] + dx / 2

        # y cell edges — use physical values when all rows have them
        if has_row_axis and len(row_vals) == n_rows:
            rv_arr  = np.array(row_vals)
            dy      = (rv_arr[1] - rv_arr[0]) if n_rows > 1 else 1.0
            y_edges = np.empty(n_rows + 1)
            y_edges[:-1] = rv_arr - dy / 2
            y_edges[-1]  = rv_arr[-1] + dy / 2
            y_axis_label = row_label
        else:
            y_edges      = np.arange(n_rows + 1) - 0.5
            y_axis_label = ""   # plain index, no label

        mesh = self._ax.pcolormesh(
            x_edges, y_edges, z,
            cmap=cmap, vmin=vmin, vmax=vmax, shading="flat")

        self._colorbar = self._fig.colorbar(mesh, ax=self._ax)
        self._colorbar.set_label(y_label)

        self._ax.set_xlabel(x_label)
        self._ax.set_ylabel(y_axis_label)
        # let matplotlib auto-tick the y-axis — no forced per-row labels

        self._ax.minorticks_on()
        self._ax.tick_params(axis="both", which="both", direction="in")
        self._fig.tight_layout()
        self._canvas.draw_idle()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _remove_colorbar(self) -> None:
        if self._colorbar is not None:
            self._colorbar.remove()
            self._colorbar = None

    def _on_cmap_changed(self, _name: str) -> None:
        self._rebuild_plot()

    def _on_sym_changed(self, _state) -> None:
        self._rebuild_plot()
