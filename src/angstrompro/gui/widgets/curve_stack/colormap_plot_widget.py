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
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

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
            self._config.get("colormap", "RdBu_r"))
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
        self._navbar = NavigationToolbar2QT(self._canvas, self)
        layout.addWidget(self._navbar)
        layout.addWidget(self._canvas)

        self._datasets: dict[str, dict] = {}
        self._checked:  dict[str, list[bool]] = {}

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
        cmap = config.get("colormap")
        if cmap and cmap in _CMAPS:
            self._cmap_combo.setCurrentText(cmap)
        self._rebuild_plot()

    # ── Drawing ───────────────────────────────────────────────────────────

    def _rebuild_plot(self) -> None:
        self._remove_colorbar()
        self._ax.clear()

        # collect visible rows across all datasets
        rows:    list[np.ndarray] = []
        x_arr:   np.ndarray | None = None
        x_label  = ""
        y_label  = ""
        row_labels: list[str] = []

        for name, entry in self._datasets.items():
            y_data  = entry["y"]
            x_data  = entry["x"]
            checked = self._checked.get(name, [True] * y_data.shape[0])
            n       = y_data.shape[0]

            for i, visible in enumerate(checked):
                if not visible:
                    continue
                rows.append(y_data[i])
                row_labels.append(f"{name} / Line {i}" if n > 1 else name)

            if x_arr is None:
                x_arr = x_data
            x_label = entry.get("x_label", "")
            y_label = entry.get("y_label", "")

        if not rows or x_arr is None:
            self._canvas.draw_idle()
            return

        z = np.vstack([r[np.newaxis, :] for r in rows])   # (n_rows, n_pts)

        cmap = self._cmap_combo.currentText()
        if self._sym_check.isChecked():
            vmax = float(np.nanmax(np.abs(z)))
            vmin = -vmax
        else:
            vmin = float(np.nanmin(z))
            vmax = float(np.nanmax(z))

        # pcolormesh needs cell edges — append one extra x value
        x_edges = np.empty(len(x_arr) + 1)
        if len(x_arr) > 1:
            dx = x_arr[1] - x_arr[0]
        else:
            dx = 1.0
        x_edges[:-1] = x_arr - dx / 2
        x_edges[-1]  = x_arr[-1] + dx / 2

        n_rows   = z.shape[0]
        y_edges  = np.arange(n_rows + 1) - 0.5

        mesh = self._ax.pcolormesh(
            x_edges, y_edges, z,
            cmap=cmap, vmin=vmin, vmax=vmax, shading="flat")

        self._colorbar = self._fig.colorbar(mesh, ax=self._ax)
        self._colorbar.set_label(y_label)

        self._ax.set_xlabel(x_label)
        self._ax.set_ylabel("Curve index")
        self._ax.set_yticks(range(n_rows))
        self._ax.set_yticklabels(row_labels, fontsize=7)

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
