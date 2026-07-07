# -*- coding: utf-8 -*-
"""
Export Video dialog for ImageStackViewer.

Parameters
----------
Panel           Main / Aux
With annotations  checkbox
  True  → drive layer spinbox + viewport grab (Option B); DPI hidden
  False → headless colormap render; DPI spinbox shown
Format          MP4, GIF, AVI
FPS             1–60 (default 10)
Quality         0–100 (hidden for GIF)
DPI             72–600 (only when annotations off)
Layer range     First / Last spinboxes

Last-used choices persisted via QSettings (settings.ini).
"""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets

_SETTINGS_KEY = "ExportVideoDialog"


class ExportVideoDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget | None = None,
                 has_aux: bool = True,
                 n_layers: int = 1) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Video")
        self.setModal(True)
        self.setMinimumWidth(360)
        self._has_aux  = has_aux
        self._n_layers = max(n_layers, 1)
        self._build_ui()
        self._restore_settings()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Panel
        self._panel_cb = QtWidgets.QComboBox()
        self._panel_cb.addItems(["Input", "Reference"])
        if not self._has_aux:
            self._panel_cb.model().item(1).setEnabled(False)
        layout.addRow("Panel:", self._panel_cb)

        # Annotations
        self._overlay_chk = QtWidgets.QCheckBox("Include annotations / overlays")
        self._overlay_chk.setChecked(True)
        layout.addRow("", self._overlay_chk)

        # Format
        self._format_cb = QtWidgets.QComboBox()
        self._format_cb.addItems(["MP4", "GIF", "AVI"])
        self._format_cb.currentTextChanged.connect(self._on_format_changed)
        layout.addRow("Format:", self._format_cb)

        # FPS
        self._fps_sb = QtWidgets.QSpinBox()
        self._fps_sb.setRange(1, 60)
        self._fps_sb.setValue(10)
        self._fps_sb.setSuffix(" fps")
        layout.addRow("Frame rate:", self._fps_sb)

        # Quality (hidden for GIF)
        self._quality_sb = QtWidgets.QSpinBox()
        self._quality_sb.setRange(0, 100)
        self._quality_sb.setValue(85)
        self._quality_label = QtWidgets.QLabel("Quality:")
        layout.addRow(self._quality_label, self._quality_sb)

        # Layer range
        range_row = QtWidgets.QHBoxLayout()
        self._first_sb = QtWidgets.QSpinBox()
        self._first_sb.setRange(0, self._n_layers - 1)
        self._first_sb.setValue(0)
        self._last_sb = QtWidgets.QSpinBox()
        self._last_sb.setRange(0, self._n_layers - 1)
        self._last_sb.setValue(self._n_layers - 1)
        self._first_sb.valueChanged.connect(
            lambda v: self._last_sb.setMinimum(v))
        self._last_sb.valueChanged.connect(
            lambda v: self._first_sb.setMaximum(v))
        range_row.addWidget(QtWidgets.QLabel("First:"))
        range_row.addWidget(self._first_sb)
        range_row.addSpacing(12)
        range_row.addWidget(QtWidgets.QLabel("Last:"))
        range_row.addWidget(self._last_sb)
        layout.addRow("Layers:", range_row)

        # Buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        # Initial visibility
        self._on_format_changed(self._format_cb.currentText())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_format_changed(self, fmt: str) -> None:
        is_gif = (fmt == "GIF")
        self._quality_sb.setVisible(not is_gif)
        self._quality_label.setVisible(not is_gif)

    def _on_accept(self) -> None:
        self._save_settings()
        self.accept()

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _restore_settings(self) -> None:
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            s = get_qsettings()
            s.beginGroup(_SETTINGS_KEY)
            panel   = s.value("panel",   "Input")
            overlay = s.value("overlay", True,  type=bool)
            fmt     = s.value("format",  "MP4")
            fps     = s.value("fps",     10,    type=int)
            quality = s.value("quality", 85,    type=int)
            s.endGroup()

            for cb, val in [(self._panel_cb, panel), (self._format_cb, fmt)]:
                idx = cb.findText(val)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            self._overlay_chk.setChecked(overlay)
            self._fps_sb.setValue(fps)
            self._quality_sb.setValue(quality)
        except Exception:
            pass

    def _save_settings(self) -> None:
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            s = get_qsettings()
            s.beginGroup(_SETTINGS_KEY)
            s.setValue("panel",   self._panel_cb.currentText())
            s.setValue("overlay", self._overlay_chk.isChecked())
            s.setValue("format",  self._format_cb.currentText())
            s.setValue("fps",     self._fps_sb.value())
            s.setValue("quality", self._quality_sb.value())
            s.endGroup()
            s.sync()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    @property
    def panel(self) -> str:
        return self._panel_cb.currentText()

    @property
    def with_overlay(self) -> bool:
        return self._overlay_chk.isChecked()

    @property
    def file_format(self) -> str:
        return self._format_cb.currentText()

    @property
    def fps(self) -> int:
        return self._fps_sb.value()

    @property
    def quality(self) -> int:
        return self._quality_sb.value()

    @property
    def first_layer(self) -> int:
        return self._first_sb.value()

    @property
    def last_layer(self) -> int:
        return self._last_sb.value()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @classmethod
    def run(cls, parent: QtWidgets.QWidget | None = None,
            has_aux: bool = True,
            n_layers: int = 1) -> "ExportVideoDialog | None":
        dlg = cls(parent, has_aux=has_aux, n_layers=n_layers)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return dlg
        return None
