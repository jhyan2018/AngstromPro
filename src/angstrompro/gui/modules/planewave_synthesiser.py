# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 2026

@author: jiahaoYan

PlanewaveSynthesiser — real-time plane-wave synthesis viewer.

Allows the user to compose a 2-D image as a sum of plane waves:

    f(x,y) = Σ_j  A_j · cos(2π(qx_j·X + qy_j·Y)/size − φ_j)

Each wave is controlled by a WaveVectorRow widget (qx, qy, amplitude slider,
phase slider).  The composite image updates live in an ImageStackViewerWidget
on every parameter change.

The actual sinusoidal kernel comes from the registered process
``simulate.sinusoidal2d`` (angstrompro.algorithms.simulate._sinusoidal2d)
so the math is identical to what the process produces.
"""
from __future__ import annotations

import numpy as np

from angstrompro.utils.qt_compat import QtCore, QtWidgets, Signal, Horizontal, ScrollBarAlwaysOn
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.gui.widgets.image_stack_viewer_widget import ImageStackViewerWidget
from angstrompro.gui.widgets.preferences import PrefSection, PrefItem
import angstrompro.gui.widgets.preferences.widgets  # registers custom widget types

# reuse the inlined kernel from simulate.py — no duplication
from angstrompro.algorithms.simulate import _sinusoidal2d


# ─────────────────────────────────────────────────────────────────────────────
# WaveVectorRow  — one row of controls per wave component
# ─────────────────────────────────────────────────────────────────────────────

class WaveVectorRow(QtWidgets.QWidget):
    """Controls for a single plane wave (qx, qy, amplitude, phase)."""

    paramsChanged = Signal(int)   # emits own index

    def __init__(self, index: int, parent=None) -> None:
        super().__init__(parent)
        self._index = index
        self.qx        = 0.0
        self.qy        = 0.0
        self.amplitude = 1.0
        self.phase     = 0.0
        self._build_ui()
        self._refresh_amplitude()
        self._refresh_phase()

    # ── construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 8)
        outer.setSpacing(5)

        heading = QtWidgets.QLabel(f"Q{self._index + 1}")
        heading.setProperty("typographyRole", "heading")
        outer.addWidget(heading)

        vector_row = QtWidgets.QHBoxLayout()
        vector_row.setSpacing(5)
        vector_row.addWidget(QtWidgets.QLabel("qx"))
        self._le_qx = QtWidgets.QLineEdit("0")
        self._le_qx.setFixedWidth(52)
        self._le_qx.editingFinished.connect(self._on_qx)
        vector_row.addWidget(self._le_qx)
        vector_row.addSpacing(12)
        vector_row.addWidget(QtWidgets.QLabel("qy"))
        self._le_qy = QtWidgets.QLineEdit("0")
        self._le_qy.setFixedWidth(52)
        self._le_qy.editingFinished.connect(self._on_qy)
        vector_row.addWidget(self._le_qy)
        vector_row.addSpacing(12)
        vector_row.addWidget(QtWidgets.QLabel("A"))
        self._le_amp_val = QtWidgets.QLineEdit()
        self._le_amp_val.setFixedWidth(60)
        self._le_amp_val.setReadOnly(True)
        vector_row.addWidget(self._le_amp_val)
        vector_row.addSpacing(12)
        vector_row.addWidget(QtWidgets.QLabel("φ"))
        self._le_ph_val = QtWidgets.QLineEdit()
        self._le_ph_val.setFixedWidth(60)
        self._le_ph_val.setReadOnly(True)
        vector_row.addWidget(self._le_ph_val)
        vector_row.addStretch()
        outer.addLayout(vector_row)

        controls = QtWidgets.QGridLayout()
        controls.setHorizontalSpacing(5)
        controls.setVerticalSpacing(5)

        controls.addWidget(QtWidgets.QLabel("A range"), 0, 0)
        self._le_amp_min = QtWidgets.QLineEdit("0")
        self._le_amp_min.setFixedWidth(104)
        self._le_amp_min.editingFinished.connect(self._refresh_amplitude)
        controls.addWidget(self._le_amp_min, 0, 1)
        self._sl_amp = QtWidgets.QSlider(Horizontal)
        self._sl_amp.setRange(0, 100)
        self._sl_amp.setValue(100)
        self._sl_amp.setFixedWidth(140)
        self._sl_amp.valueChanged.connect(self._refresh_amplitude)
        controls.addWidget(self._sl_amp, 0, 2)
        self._le_amp_max = QtWidgets.QLineEdit("1")
        self._le_amp_max.setFixedWidth(104)
        self._le_amp_max.editingFinished.connect(self._refresh_amplitude)
        controls.addWidget(self._le_amp_max, 0, 3)

        controls.addWidget(QtWidgets.QLabel("φ range"), 1, 0)
        self._le_ph_min = QtWidgets.QLineEdit("-3.14")
        self._le_ph_min.setFixedWidth(104)
        self._le_ph_min.editingFinished.connect(self._refresh_phase)
        controls.addWidget(self._le_ph_min, 1, 1)
        self._sl_ph = QtWidgets.QSlider(Horizontal)
        self._sl_ph.setRange(0, 100)
        self._sl_ph.setValue(50)
        self._sl_ph.setFixedWidth(140)
        self._sl_ph.valueChanged.connect(self._refresh_phase)
        controls.addWidget(self._sl_ph, 1, 2)
        self._le_ph_max = QtWidgets.QLineEdit("3.14")
        self._le_ph_max.setFixedWidth(104)
        self._le_ph_max.editingFinished.connect(self._refresh_phase)
        controls.addWidget(self._le_ph_max, 1, 3)
        controls.setColumnStretch(4, 1)
        outer.addLayout(controls)

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_qx(self) -> None:
        try:
            self.qx = float(self._le_qx.text())
        except ValueError:
            pass
        self.paramsChanged.emit(self._index)

    def _on_qy(self) -> None:
        try:
            self.qy = float(self._le_qy.text())
        except ValueError:
            pass
        self.paramsChanged.emit(self._index)

    def _refresh_amplitude(self) -> None:
        try:
            lo = float(self._le_amp_min.text())
            hi = float(self._le_amp_max.text())
        except ValueError:
            return
        pct = self._sl_amp.value() / 100.0
        self.amplitude = round((hi - lo) * pct + lo, 6)
        self._le_amp_val.setText(str(self.amplitude))
        self.paramsChanged.emit(self._index)

    def _refresh_phase(self) -> None:
        try:
            lo = float(self._le_ph_min.text())
            hi = float(self._le_ph_max.text())
        except ValueError:
            return
        pct = self._sl_ph.value() / 100.0
        self.phase = round((hi - lo) * pct + lo, 6)
        self._le_ph_val.setText(str(self.phase))
        self.paramsChanged.emit(self._index)


# ─────────────────────────────────────────────────────────────────────────────
# PlanewaveSynthesiser
# ─────────────────────────────────────────────────────────────────────────────

@register_module
class PlanewaveSynthesiser(AGuiModule):
    """Real-time 2-D plane-wave synthesis module."""

    module_id      = "planewave_synthesiser"
    display_name   = "Planewave Synthesiser"
    category       = "Simulation"
    accepted_types = set()     # no workspace input — generates data internally
    staged_labels  = []
    clearable_slots = set()

    preferences_schema = [
        PrefSection("Color map", "palette", [
            PrefItem("colormap.cmap_palette_list", "", "colormap_picker", full_width=True),
        ]),
        PrefSection("Scale", "adjustments-horizontal", [
            PrefItem("factor.sigma",                    "Sigma",              "number", "σ window for histogram auto-scale"),
            PrefItem("factor.slider_scale_zoom_factor", "Slider zoom factor", "number", "Step size for zoom in/out buttons",
                     kwargs={"min": 0.001, "max": 0.999}),
        ]),
        PrefSection("Canvas", "layout-kanban", [
            PrefItem("canvas.bias_text",       "Show bias value", "checkbox", "Overlay bias setpoint text on image"),
            PrefItem("canvas.bias_text_color", "Bias text color", "dropdown", "Color of the bias annotation",
                     kwargs={"choices": ["Red", "Green", "Blue", "Yellow", "Black", "White"]}),
        ]),
    ]

    def __init__(self, context, parent=None) -> None:
        # initialise before super().__init__ because AGuiModule calls build_ui() inside it
        self._data_size  = 256
        self._rows: list[WaveVectorRow] = []
        self._wave_cache: list[np.ndarray] = []
        self._sum_data   = np.zeros((self._data_size, self._data_size))
        self._uds        = self._make_uds()
        super().__init__(context, parent)
        self.resize(1100, 680)

    # ── AGuiModule contract ───────────────────────────────────────────────

    def build_ui(self) -> None:
        # ── left: image viewer ──────────────────────────────────────────
        self._viewer = ImageStackViewerWidget()
        self._viewer.setMinimumWidth(400)

        # ── right: controls ─────────────────────────────────────────────
        ctrl = QtWidgets.QWidget()
        ctrl.setMinimumWidth(320)
        vbox = QtWidgets.QVBoxLayout(ctrl)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(6)

        # formula label
        eq = QtWidgets.QLabel("f(x,y) = Σ  A<sub>j</sub> · cos(2π(qx<sub>j</sub>·X + qy<sub>j</sub>·Y)/size − φ<sub>j</sub>)")
        eq.setTextFormat(QtCore.Qt.TextFormat.RichText)
        eq.setWordWrap(True)
        vbox.addWidget(QtWidgets.QLabel("<b>─── Function ───</b>"))
        vbox.addWidget(eq)

        # size + buttons row
        size_row = QtWidgets.QHBoxLayout()
        size_row.addWidget(QtWidgets.QLabel("Size (px):"))
        self._le_size = QtWidgets.QLineEdit(str(self._data_size))
        self._le_size.setFixedWidth(60)
        self._le_size.editingFinished.connect(self._on_size_changed)
        size_row.addWidget(self._le_size)
        size_row.addStretch()
        vbox.addLayout(size_row)

        edit_row = QtWidgets.QHBoxLayout()
        pb_add = QtWidgets.QPushButton("＋ Add wave")
        pb_add.clicked.connect(self._on_add_wave)
        pb_remove = QtWidgets.QPushButton("－ Remove wave")
        pb_remove.clicked.connect(self._on_remove_wave)
        pb_save = QtWidgets.QPushButton("Save to workspace")
        pb_save.clicked.connect(self._on_save_to_workspace)
        edit_row.addWidget(pb_add)
        edit_row.addWidget(pb_remove)
        vbox.addLayout(edit_row)
        vbox.addWidget(pb_save)

        # scrollable wave-vector list
        self._scroll_content = QtWidgets.QWidget()
        self._scroll_vbox    = QtWidgets.QVBoxLayout(self._scroll_content)
        self._scroll_vbox.setContentsMargins(0, 0, 0, 0)
        self._scroll_vbox.setSpacing(2)
        self._scroll_vbox.addStretch()

        sa = QtWidgets.QScrollArea()
        sa.setWidgetResizable(True)
        sa.setVerticalScrollBarPolicy(ScrollBarAlwaysOn)
        sa.setWidget(self._scroll_content)
        vbox.addWidget(sa, stretch=1)

        # ── splitter ────────────────────────────────────────────────────
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._viewer)
        splitter.addWidget(ctrl)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([720, 360])
        self.setCentralWidget(splitter)

        # apply config (palette, scale, canvas settings)
        self._apply_config_to_panels(self._config)

        # seed one wave row so the viewer shows something
        self._add_wave_row()
        self._redraw()

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        pass   # module generates its own data; workspace loading unused

    def _apply_config_to_panels(self, cfg: dict) -> None:
        cmap_list = cfg.get("colormap", {}).get("cmap_palette_list", ["gray"])
        self._viewer.setup_palette(cmap_list)

        factor = cfg.get("factor", {})
        self._viewer.setScaleWidgetSigmaDefault(factor.get("sigma", 5))
        self._viewer.setScaleWidgetZoomFactor(factor.get("slider_scale_zoom_factor", 0.6))

        canvas = cfg.get("canvas", {})
        self._viewer.setBiasTextColor(canvas.get("bias_text_color", "Red"))
        self._viewer.setBiasTextShown(canvas.get("bias_text", False))

    # ── helpers ───────────────────────────────────────────────────────────

    def _make_uds(self) -> UdsDataStru:
        n = self._data_size
        d = self._sum_data[np.newaxis, :, :]
        return UdsDataStru(
            name="planewave_synthesiser",
            data=d.astype(np.float64),
            axes=[
                Axis(values=np.array([0.0]), label="Layer", units=""),
                Axis(values=np.arange(n, dtype=np.float64), label="Row",    units="px"),
                Axis(values=np.arange(n, dtype=np.float64), label="Column", units="px"),
            ],
            info={"_source_format": "planewave_synthesiser"},
            proc_history=[],
        )

    def _redraw(self) -> None:
        self._uds.data[0] = self._sum_data
        self._viewer.setUdsData(self._uds)

    def _recompute_all(self) -> None:
        n = self._data_size
        self._sum_data = np.zeros((n, n))
        self._wave_cache.clear()
        for row in self._rows:
            wave = _sinusoidal2d(n, row.qx, row.qy, row.phase, row.amplitude)
            self._wave_cache.append(wave)
            self._sum_data += wave
        self._redraw()

    # ── wave row management ───────────────────────────────────────────────

    def _add_wave_row(self) -> None:
        idx = len(self._rows)
        if idx >= 50:
            return
        row = WaveVectorRow(idx)
        row.paramsChanged.connect(self._on_wave_params_changed)
        self._rows.append(row)
        self._wave_cache.append(np.zeros((self._data_size, self._data_size)))
        # insert before the trailing stretch
        self._scroll_vbox.insertWidget(self._scroll_vbox.count() - 1, row)

    def _remove_wave_row(self) -> None:
        if not self._rows:
            return
        row = self._rows.pop()
        wave = self._wave_cache.pop()
        self._sum_data -= wave
        self._scroll_vbox.removeWidget(row)
        row.deleteLater()
        self._redraw()

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_add_wave(self) -> None:
        self._add_wave_row()

    def _on_remove_wave(self) -> None:
        self._remove_wave_row()

    def _on_wave_params_changed(self, index: int) -> None:
        if index >= len(self._rows):
            return
        n    = self._data_size
        row  = self._rows[index]
        new_wave = _sinusoidal2d(n, row.qx, row.qy, row.phase, row.amplitude)

        if index < len(self._wave_cache):
            self._sum_data -= self._wave_cache[index]
            self._wave_cache[index] = new_wave
        else:
            self._wave_cache.append(new_wave)
        self._sum_data += new_wave
        self._redraw()

    def _on_size_changed(self) -> None:
        txt = self._le_size.text().strip()
        if not txt.isdigit():
            return
        n = int(txt)
        if n < 16 or n > 4096:
            return
        self._data_size = n
        self._sum_data  = np.zeros((n, n))
        self._uds       = self._make_uds()
        self._recompute_all()

    def _on_save_to_workspace(self) -> None:
        n = self._data_size
        uds = UdsDataStru(
            name="planewave_synthesiser_snapshot",
            data=self._sum_data[np.newaxis, :, :].copy().astype(np.float64),
            axes=[
                Axis(values=np.array([0.0]), label="Layer",  units=""),
                Axis(values=np.arange(n, dtype=np.float64), label="Row",    units="px"),
                Axis(values=np.arange(n, dtype=np.float64), label="Column", units="px"),
            ],
            info={"_source_format": "planewave_synthesiser"},
            proc_history=[],
        )
        self.workspace.add_item(payload=uds)
