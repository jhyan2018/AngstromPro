# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Stack (waterfall) plot widget — line plot with per-curve vertical offset.
"""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from angstrompro.utils.qt_compat import QtCore, QtWidgets

from .base_plot_widget import BasePlotWidget


class StackPlotWidget(BasePlotWidget):
    """Line-plot mode: all curves on one Axes with a configurable waterfall offset."""

    def __init__(self, config: dict | None = None, parent=None) -> None:
        super().__init__(config, parent)
        self._setup_ui()
        self._setup_crosshair()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── controls ──────────────────────────────────────────────────────
        ctrl = QtWidgets.QHBoxLayout()
        ctrl.setContentsMargins(4, 4, 4, 2)
        ctrl.setSpacing(8)

        ctrl.addWidget(QtWidgets.QLabel("Offset:"))
        self._offset_spin = QtWidgets.QDoubleSpinBox()
        self._offset_spin.setRange(-1e9, 1e9)
        self._offset_spin.setValue(0.0)
        self._offset_spin.setSingleStep(0.1)
        self._offset_spin.setDecimals(4)
        self._offset_spin.setFixedWidth(110)
        self._offset_spin.setToolTip("Vertical offset between successive visible curves")
        self._offset_spin.valueChanged.connect(self._on_offset_changed)
        ctrl.addWidget(self._offset_spin)

        btn_yauto = QtWidgets.QPushButton("Y Auto")
        btn_yauto.setToolTip("Auto-scale Y axis to visible data")
        btn_yauto.clicked.connect(self._on_y_autoscale)
        ctrl.addWidget(btn_yauto)

        # crosshair toggle
        self._xhair_cb = QtWidgets.QCheckBox("Crosshair")
        self._xhair_cb.setChecked(True)
        self._xhair_cb.setToolTip("Show crosshair cursor with x/y readout")
        self._xhair_cb.stateChanged.connect(self._on_crosshair_toggled)
        ctrl.addWidget(self._xhair_cb)

        ctrl.addStretch()

        # ── readout label ─────────────────────────────────────────────────
        self._readout = QtWidgets.QLabel("")
        self._readout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                   QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._readout.setMinimumWidth(200)
        self._readout.setStyleSheet("font-family: monospace; color: #555;")
        ctrl.addWidget(self._readout)

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
        self._lines: dict[tuple[str, int], object] = {}

    # ── Crosshair ─────────────────────────────────────────────────────────

    def _setup_crosshair(self) -> None:
        self._xhair_h = None   # horizontal Line2D
        self._xhair_v = None   # vertical   Line2D
        self._bg      = None
        self._cid_move   = self._canvas.mpl_connect(
            "motion_notify_event", self._on_mouse_move)
        self._cid_leave  = self._canvas.mpl_connect(
            "axes_leave_event", self._on_axes_leave)
        self._cid_resize = self._canvas.mpl_connect(
            "resize_event", self._on_resize)

    def _ensure_crosshair_lines(self) -> None:
        """Create crosshair artists if they don't exist yet (after ax.clear)."""
        if self._xhair_h is None or self._xhair_h not in self._ax.lines:
            self._xhair_h = self._ax.axhline(
                color="gray", linewidth=0.8, linestyle="--", alpha=0.7,
                visible=False, zorder=10, animated=True)
        if self._xhair_v is None or self._xhair_v not in self._ax.lines:
            self._xhair_v = self._ax.axvline(
                color="gray", linewidth=0.8, linestyle="--", alpha=0.7,
                visible=False, zorder=10, animated=True)

    def _on_mouse_move(self, event) -> None:
        if not self._xhair_cb.isChecked():
            return
        if event.inaxes is not self._ax or event.xdata is None:
            self._hide_crosshair()
            return

        self._ensure_crosshair_lines()
        x, y = event.xdata, event.ydata

        self._xhair_v.set_xdata([x, x])
        self._xhair_h.set_ydata([y, y])
        self._xhair_v.set_visible(True)
        self._xhair_h.set_visible(True)

        # blit: restore background, draw crosshair artists, flush
        if self._bg is None:
            return
        self._canvas.restore_region(self._bg)
        self._ax.draw_artist(self._xhair_v)
        self._ax.draw_artist(self._xhair_h)
        self._canvas.blit(self._ax.bbox)

        # format readout using current axis labels for units hint
        xl = self._ax.get_xlabel() or "x"
        yl = self._ax.get_ylabel() or "y"
        self._readout.setText(f"{xl} = {x:.6g}    {yl} = {y:.6g}")

    def _on_axes_leave(self, event) -> None:
        self._hide_crosshair()

    def _hide_crosshair(self) -> None:
        if self._xhair_h is not None:
            self._xhair_h.set_visible(False)
        if self._xhair_v is not None:
            self._xhair_v.set_visible(False)
        if self._bg is None:
            return
        self._canvas.restore_region(self._bg)
        self._canvas.blit(self._ax.bbox)
        self._readout.setText("")

    def _on_crosshair_toggled(self, _state) -> None:
        if not self._xhair_cb.isChecked():
            self._hide_crosshair()

    def _on_resize(self, _event) -> None:
        self._capture_background()

    def _capture_background(self) -> None:
        """Cache the canvas background for blit after a full redraw."""
        self._canvas.draw()
        self._bg = self._canvas.copy_from_bbox(self._ax.bbox)

    # ── BasePlotWidget interface ──────────────────────────────────────────

    def refresh(self, datasets: dict[str, dict],
                checked: dict[str, list[bool]]) -> None:
        self._datasets = datasets
        self._checked  = checked
        self._rebuild_plot()

    def clear(self) -> None:
        self._xhair_h = None
        self._xhair_v = None
        self._ax.clear()
        self._canvas.draw_idle()
        self._readout.setText("")

    def apply_config(self, config: dict) -> None:
        super().apply_config(config)
        self._rebuild_plot()

    # ── Drawing ───────────────────────────────────────────────────────────

    def get_line_styles(self) -> dict[tuple[str, int], dict]:
        result = {}
        for key, line in self._lines.items():
            result[key] = {
                "color":     line.get_color(),
                "linewidth": line.get_linewidth(),
                "linestyle": line.get_linestyle(),
                "marker":    line.get_marker() if line.get_marker() != "None" else "",
                "alpha":     line.get_alpha() or 1.0,
                "label":     line.get_label(),
                "visible":   line.get_visible(),
            }
        return result

    def get_offset(self) -> float:
        return self._offset_spin.value()

    def set_offset(self, value: float) -> None:
        self._offset_spin.setValue(value)

    def _rebuild_plot(self) -> None:
        self._xhair_h = None
        self._xhair_v = None
        self._ax.clear()
        self._lines.clear()
        offset    = self._offset_spin.value()
        curve_idx = 0
        x_label   = ""
        y_label   = ""

        for name, entry in self._datasets.items():
            y_arr   = entry["y"]
            x_arr   = entry["x"]
            checked = self._checked.get(name, [True] * y_arr.shape[0])
            lw      = self._config.get("line_width", 1.0)
            n       = y_arr.shape[0]

            for i, visible in enumerate(checked):
                if not visible:
                    continue
                curve_label = f"{name} / Line {i}" if n > 1 else name
                lines = self._ax.plot(x_arr, y_arr[i] + curve_idx * offset,
                                      linewidth=lw, label=curve_label)
                self._lines[(name, i)] = lines[0]
                curve_idx += 1

            x_label = entry.get("x_label", "")
            y_label = entry.get("y_label", "")

        if x_label:
            self._ax.set_xlabel(x_label)
        if y_label:
            self._ax.set_ylabel(y_label)
        if self._config.get("show_grid", False):
            self._ax.grid(True, linestyle="--", alpha=0.4)

        self._ax.minorticks_on()
        self._ax.tick_params(axis="both", which="both", direction="in")
        self._fig.tight_layout()
        self._capture_background()

    def _on_offset_changed(self, _val) -> None:
        self._rebuild_plot()

    def _on_y_autoscale(self) -> None:
        self._ax.autoscale(axis="y")
        self._canvas.draw_idle()
        self._capture_background()
