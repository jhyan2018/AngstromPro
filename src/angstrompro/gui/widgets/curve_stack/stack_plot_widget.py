# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Stack (waterfall) plot widget — line plot with per-curve vertical offset.

Color modes
-----------
"auto"                     Line2D, prop_cycle from rcParams
"cmap:<name>"              Line2D, one flat color per line from colormap
"cmap_value:<name>"        LineCollection, per-point color, per-line norm
"cmap_value_global:<name>" LineCollection, per-point color, global norm + colorbar
"""
from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .nav_toolbar import NavToolbar

from angstrompro.utils.qt_compat import QtCore, QtWidgets

from .base_plot_widget import BasePlotWidget

# ── color mode helpers ────────────────────────────────────────────────────────

def _is_lc_mode(mode: str) -> bool:
    return mode.startswith("cmap_value:")

def _is_lc_global_mode(mode: str) -> bool:
    return mode.startswith("cmap_value_global:")

def _needs_lc(mode: str) -> bool:
    return _is_lc_mode(mode) or _is_lc_global_mode(mode)

def _cmap_name_from_mode(mode: str) -> str:
    for prefix in ("cmap_value_global:", "cmap_value:", "cmap:"):
        if mode.startswith(prefix):
            return mode[len(prefix):] or "viridis"
    return "viridis"


class StackPlotWidget(BasePlotWidget):
    """Line-plot mode with waterfall offset.  Supports Line2D and LineCollection color modes."""

    # emitted after _rebuild_plot replaced all artists — subscribers holding
    # artist references (style panel via ViewerContext) must re-pull
    artists_rebuilt = QtCore.pyqtSignal()

    def __init__(self, config: dict | None = None, parent=None) -> None:
        super().__init__(config, parent)
        self._lines:         dict[tuple[str, int], object] = {}
        self._line_order:    list[tuple[str, int]]         = []
        self._manual_colors: dict[tuple[str, int], str]    = {}  # pinned per-line colors
        self._colorbar    = None
        self._setup_ui()
        self._setup_crosshair()

    # ── UI ────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        ctrl = QtWidgets.QHBoxLayout()
        ctrl.setContentsMargins(4, 4, 4, 2)
        ctrl.setSpacing(8)

        # Color mode — two separate combos: Color mode + Colormap
        ctrl.addWidget(QtWidgets.QLabel("Color:"))
        self._mode_combo = QtWidgets.QComboBox()
        self._mode_combo.setToolTip("Color assignment mode")
        for label, value in [
            ("Auto",       "auto"),
            ("Cmap",       "cmap"),
            ("CmapValue",  "cmap_value"),
            ("CmapGlobal", "cmap_value_global"),
        ]:
            self._mode_combo.addItem(label, value)
        self._mode_combo.currentIndexChanged.connect(self._on_color_mode_changed)
        ctrl.addWidget(self._mode_combo)

        ctrl.addWidget(QtWidgets.QLabel("Colormap:"))
        self._cmap_combo = QtWidgets.QComboBox()
        self._cmap_combo.setToolTip("Colormap (used when Mode ≠ Auto)")
        for name in ["viridis", "plasma", "coolwarm", "RdBu", "tab10", "tab20",
                     "inferno", "magma", "cividis", "turbo"]:
            self._cmap_combo.addItem(name, name)
        self._cmap_combo.setEnabled(False)   # Auto is default
        self._cmap_combo.currentIndexChanged.connect(self._on_color_mode_changed)
        ctrl.addWidget(self._cmap_combo)

        ctrl.addSpacing(8)

        # Offset
        ctrl.addWidget(QtWidgets.QLabel("Offset:"))
        self._offset_spin = QtWidgets.QDoubleSpinBox()
        self._offset_spin.setRange(-1e9, 1e9)
        self._offset_spin.setValue(0.0)
        self._offset_spin.setSingleStep(0.1)
        self._offset_spin.setDecimals(4)
        self._offset_spin.setFixedWidth(110)
        self._offset_spin.setToolTip("Vertical offset between successive curves")
        self._offset_spin.valueChanged.connect(self._on_offset_changed)
        ctrl.addWidget(self._offset_spin)

        btn_yauto = QtWidgets.QPushButton("Y Auto")
        btn_yauto.setToolTip("Auto-scale Y axis to visible data")
        btn_yauto.clicked.connect(self._on_y_autoscale)
        ctrl.addWidget(btn_yauto)

        self._xhair_cb = QtWidgets.QCheckBox("Crosshair")
        self._xhair_cb.setChecked(True)
        self._xhair_cb.setToolTip("Show crosshair cursor with x/y readout")
        self._xhair_cb.stateChanged.connect(self._on_crosshair_toggled)
        ctrl.addWidget(self._xhair_cb)

        ctrl.addStretch()

        self._readout = QtWidgets.QLabel("")
        self._readout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                   QtCore.Qt.AlignmentFlag.AlignVCenter)
        # never contribute to the layout's minimum width — just use spare space
        self._readout.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Preferred)
        self._readout.setStyleSheet("font-family: monospace; color: #555;")
        ctrl.addWidget(self._readout, stretch=1)

        layout.addLayout(ctrl)

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

    # ── Crosshair ─────────────────────────────────────────────────────────

    def _setup_crosshair(self) -> None:
        self._xhair_h = None
        self._xhair_v = None
        self._bg      = None
        self._cid_move  = self._canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self._cid_leave = self._canvas.mpl_connect("axes_leave_event",    self._on_axes_leave)
        self._cid_draw  = self._canvas.mpl_connect("draw_event",          self._on_draw)

    def _on_draw(self, _event) -> None:
        self._bg = self._canvas.copy_from_bbox(self._ax.bbox)

    def _ensure_crosshair_lines(self) -> None:
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
        if self._bg is None:
            return
        self._canvas.restore_region(self._bg)
        self._ax.draw_artist(self._xhair_v)
        self._ax.draw_artist(self._xhair_h)
        self._canvas.blit(self._ax.bbox)
        xl = self._ax.get_xlabel() or "x"
        yl = self._ax.get_ylabel() or "y"
        self._readout.setText(f"{xl} = {x:.6g}    {yl} = {y:.6g}")

    def _on_axes_leave(self, _event) -> None:
        self._hide_crosshair()

    def _hide_crosshair(self) -> None:
        if self._xhair_h is not None:
            self._xhair_h.set_visible(False)
        if self._xhair_v is not None:
            self._xhair_v.set_visible(False)
        if self._bg is None:
            return
        try:
            self._canvas.restore_region(self._bg)
            self._canvas.blit(self._ax.bbox)
        except RuntimeError:
            pass  # canvas deleted during widget rebuild
        self._readout.setText("")

    def _on_crosshair_toggled(self, _state) -> None:
        if not self._xhair_cb.isChecked():
            self._hide_crosshair()

    def _capture_background(self) -> None:
        self._canvas.draw_idle()

    # ── Full-redraw API ───────────────────────────────────────────────────

    def refresh(self, datasets: dict[str, dict],
                checked: dict[str, list[bool]]) -> None:
        self._datasets = datasets
        self._checked  = checked
        self._rebuild_plot()

    def _remove_colorbar(self) -> None:
        if self._colorbar is not None:
            try:
                self._colorbar.remove()
            except Exception:
                pass
            self._colorbar = None

    def clear(self) -> None:
        self._xhair_h = None
        self._xhair_v = None
        self._lines.clear()
        self._line_order.clear()
        self._manual_colors.clear()
        self._datasets.clear()
        self._checked.clear()
        self._remove_colorbar()
        self._ax.clear()
        self._canvas.draw_idle()
        self._readout.setText("")

    def apply_config(self, config: dict) -> None:
        super().apply_config(config)
        self._rebuild_plot()

    # ── Granular API ─────────────────────────────────────────────────────

    def add_lines(self, name: str, entry: dict, checked_list: list[bool]) -> None:
        """Append one dataset.  LC modes require full rebuild (global norm changes)."""
        self._datasets[name] = entry
        self._checked[name]  = checked_list

        if _needs_lc(self.color_mode):
            # global norm must be recomputed over all lines including the new one
            self._rebuild_plot()
            return

        offset = self._offset_spin.value()
        x_arr  = entry["x"]
        y_arr  = entry["y"]
        n      = y_arr.shape[0]
        start  = len(self._line_order)

        for i, vis in enumerate(checked_list):
            global_idx  = start + i
            curve_label = f"{name} / Line {i}" if n > 1 else name
            line, = self._ax.plot(
                x_arr, y_arr[i] + global_idx * offset,
                label=curve_label, visible=vis)
            self._lines[(name, i)] = line
            self._line_order.append((name, i))

        x_label = entry.get("x_label", "")
        y_label = entry.get("y_label", "")
        if x_label and not self._ax.get_xlabel():
            self._ax.set_xlabel(x_label)
        if y_label and not self._ax.get_ylabel():
            self._ax.set_ylabel(y_label)

        self._assign_colors(self._lines)
        self._fig.tight_layout()
        self._capture_background()

    def remove_lines(self, name: str) -> None:
        self._datasets.pop(name, None)
        self._checked.pop(name, None)
        self._rebuild_plot()

    def set_line_visible(self, name: str, idx: int, visible: bool) -> None:
        if name in self._checked:
            self._checked[name][idx] = visible
        artist = self._lines.get((name, idx))
        if artist is not None:
            artist.set_visible(visible)
            self._capture_background()

    def set_all_visible(self, name: str, visible: bool) -> None:
        if name not in self._checked:
            return
        n = len(self._checked[name])
        self._checked[name] = [visible] * n
        for i in range(n):
            artist = self._lines.get((name, i))
            if artist is not None:
                artist.set_visible(visible)
        self._capture_background()

    # ── Scene helpers ─────────────────────────────────────────────────────

    def pin_color(self, key: tuple[str, int], color: str) -> None:
        """Record a manual color override for one line."""
        self._manual_colors[key] = color

    def reset_color(self, key: tuple[str, int]) -> None:
        """Remove manual color override and reapply color mode."""
        self._manual_colors.pop(key, None)
        self._assign_colors(self._lines)
        self._capture_background()

    def get_line_styles(self) -> dict[tuple[str, int], dict]:
        from matplotlib.lines import Line2D
        result = {}
        for key, artist in self._lines.items():
            if not isinstance(artist, Line2D):
                continue   # LineCollection — no simple per-line style to extract
            result[key] = {
                "color":     artist.get_color(),
                "linewidth": artist.get_linewidth(),
                "linestyle": artist.get_linestyle(),
                "marker":    artist.get_marker() if artist.get_marker() != "None" else "",
                "alpha":     artist.get_alpha() or 1.0,
                "label":     artist.get_label(),
                "visible":   artist.get_visible(),
            }
        return result

    def get_offset(self) -> float:
        return self._offset_spin.value()

    def set_offset(self, value: float) -> None:
        self._offset_spin.setValue(value)

    # ── Color mode ────────────────────────────────────────────────────────

    def _composed_mode(self) -> str:
        """Build 'auto' / 'cmap:name' / 'cmap_value:name' / 'cmap_value_global:name'."""
        base = self._mode_combo.currentData() or "auto"
        if base == "auto":
            return "auto"
        cmap = self._cmap_combo.currentData() or "viridis"
        return f"{base}:{cmap}"

    def _on_color_mode_changed(self, _idx: int) -> None:
        # enable/disable the cmap combo depending on mode
        is_auto = (self._mode_combo.currentData() == "auto")
        self._cmap_combo.setEnabled(not is_auto)

        new_mode = self._composed_mode()
        old_mode = self.color_mode
        old_lc   = _needs_lc(old_mode)
        new_lc   = _needs_lc(new_mode)
        self.color_mode = new_mode
        if old_lc != new_lc or (new_lc and new_mode != old_mode):
            # artist type changed, OR same LC type but different cmap (colors baked in)
            self._rebuild_plot()
        else:
            self._assign_colors(self._lines)
            self._capture_background()
            self.artists_rebuilt.emit()   # colors changed — panels re-pull

    def set_cmap_palette(self, names: list[str]) -> None:
        """Repopulate the colormap combo with the user's preference list."""
        current = self._cmap_combo.currentData()
        self._cmap_combo.blockSignals(True)
        self._cmap_combo.clear()
        for name in names:
            self._cmap_combo.addItem(name, name)
        # restore previous selection if still present, else first item
        idx = self._cmap_combo.findData(current)
        self._cmap_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._cmap_combo.blockSignals(False)

    def set_color_mode(self, mode: str) -> None:
        """Set color mode programmatically (e.g. from restore_scene)."""
        old_mode = self.color_mode
        old_lc   = _needs_lc(old_mode)
        self.color_mode = mode

        # decompose 'prefix:cmap' back into the two combos
        self._mode_combo.blockSignals(True)
        self._cmap_combo.blockSignals(True)
        if mode == "auto":
            self._mode_combo.setCurrentIndex(self._mode_combo.findData("auto"))
            self._cmap_combo.setEnabled(False)
        else:
            for prefix in ("cmap_value_global", "cmap_value", "cmap"):
                if mode.startswith(prefix + ":"):
                    cmap_name = mode[len(prefix) + 1:]
                    idx = self._mode_combo.findData(prefix)
                    if idx >= 0:
                        self._mode_combo.setCurrentIndex(idx)
                    idx2 = self._cmap_combo.findData(cmap_name)
                    if idx2 < 0:
                        self._cmap_combo.addItem(cmap_name, cmap_name)
                        idx2 = self._cmap_combo.count() - 1
                    self._cmap_combo.setCurrentIndex(idx2)
                    self._cmap_combo.setEnabled(True)
                    break
        self._mode_combo.blockSignals(False)
        self._cmap_combo.blockSignals(False)

        new_lc = _needs_lc(mode)
        if old_lc != new_lc or (new_lc and mode != old_mode):
            self._rebuild_plot()
        else:
            self._assign_colors(self._lines)
            self._capture_background()

    # ── Drawing ───────────────────────────────────────────────────────────

    def _rebuild_plot(self) -> None:
        self._xhair_h = None
        self._xhair_v = None
        self._remove_colorbar()
        self._ax.clear()
        self._lines.clear()
        self._line_order.clear()

        if _needs_lc(self.color_mode):
            self._rebuild_lc()
        else:
            self._rebuild_line2d()

        # re-apply manual color pins that survive mode/offset changes
        for key, color in self._manual_colors.items():
            artist = self._lines.get(key)
            if artist is not None:
                artist.set_color(color)

        self._ax.minorticks_on()
        self._ax.tick_params(axis="both", which="both", direction="in")
        self._fig.tight_layout()
        self._capture_background()
        self.artists_rebuilt.emit()

    def _rebuild_line2d(self) -> None:
        offset    = self._offset_spin.value()
        x_label   = ""
        y_label   = ""
        global_idx = 0

        for name, entry in self._datasets.items():
            y_arr   = entry["y"]
            x_arr   = entry["x"]
            checked = self._checked.get(name, [True] * y_arr.shape[0])
            n       = y_arr.shape[0]

            for i, vis in enumerate(checked):
                curve_label = f"{name} / Line {i}" if n > 1 else name
                line, = self._ax.plot(
                    x_arr, y_arr[i] + global_idx * offset,
                    label=curve_label, visible=vis)
                self._lines[(name, i)] = line
                self._line_order.append((name, i))
                global_idx += 1

            x_label = entry.get("x_label", "") or x_label
            y_label = entry.get("y_label", "") or y_label

        if x_label:
            self._ax.set_xlabel(x_label)
        if y_label:
            self._ax.set_ylabel(y_label)
        if self._config.get("show_grid", False):
            self._ax.grid(True, linestyle="--", alpha=0.4)

        self._assign_colors(self._lines)

    def _rebuild_lc(self) -> None:
        import matplotlib.colors as mcolors
        from matplotlib.collections import LineCollection

        import matplotlib as mpl
        mode      = self.color_mode
        cmap_name = _cmap_name_from_mode(mode)
        is_global = _is_lc_global_mode(mode)
        offset    = self._offset_spin.value()
        lw        = mpl.rcParams.get("lines.linewidth", 1.0)
        x_label   = ""
        y_label   = ""

        # For global mode: compute norm over ALL visible raw y values first
        if is_global:
            all_vals = [
                entry["y"][i]
                for name, entry in self._datasets.items()
                for i, vis in enumerate(
                    self._checked.get(name, [True] * entry["y"].shape[0]))
                if vis
            ]
            if all_vals:
                gmin = min(v.min() for v in all_vals)
                gmax = max(v.max() for v in all_vals)
            else:
                gmin, gmax = 0.0, 1.0
            global_norm = mcolors.Normalize(gmin, gmax)
        else:
            global_norm = None

        global_idx = 0
        last_lc    = None   # track last collection for colorbar

        for name, entry in self._datasets.items():
            y_arr   = entry["y"]
            x_arr   = entry["x"]
            checked = self._checked.get(name, [True] * y_arr.shape[0])
            n       = y_arr.shape[0]

            for i, vis in enumerate(checked):
                y_plot  = y_arr[i] + global_idx * offset
                y_color = y_arr[i]   # raw value for color — no offset

                norm = global_norm if is_global else mcolors.Normalize(
                    y_color.min(), y_color.max())

                lc = self._make_lc(x_arr, y_plot, y_color,
                                   cmap_name, norm, lw, vis)
                self._ax.add_collection(lc)
                self._lines[(name, i)] = lc
                self._line_order.append((name, i))
                global_idx += 1
                last_lc = lc

            x_label = entry.get("x_label", "") or x_label
            y_label = entry.get("y_label", "") or y_label

        # Collections don't auto-scale axes
        self._ax.autoscale_view()

        if x_label:
            self._ax.set_xlabel(x_label)
        if y_label:
            self._ax.set_ylabel(y_label)
        if self._config.get("show_grid", False):
            self._ax.grid(True, linestyle="--", alpha=0.4)

        # Colorbar only for global mode (unambiguous shared norm)
        if is_global and last_lc is not None:
            self._colorbar = self._fig.colorbar(last_lc, ax=self._ax)

    @staticmethod
    def _make_lc(x, y_plot, y_color, cmap_name, norm, lw, visible):
        from matplotlib.collections import LineCollection
        pts      = np.column_stack([x, y_plot]).reshape(-1, 1, 2)
        segments = np.concatenate([pts[:-1], pts[1:]], axis=1)
        lc = LineCollection(segments, cmap=cmap_name, norm=norm,
                            linewidth=lw, visible=visible)
        lc.set_array(y_color)
        return lc

    def _on_offset_changed(self, _val) -> None:
        self._rebuild_plot()

    def _on_y_autoscale(self) -> None:
        self._ax.autoscale(axis="y")
        self._canvas.draw_idle()
        self._capture_background()
