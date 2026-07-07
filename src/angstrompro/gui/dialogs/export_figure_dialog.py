# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 2026

@author: jiahaoYan

Export Figure dialog for CurveStackViewer.

Options
-------
  Destination  — File / Clipboard
  Format       — PNG / PDF / SVG / TIFF  (File only; PDF & SVG are vector)
  DPI          — 72–1200, default 300    (disabled for PDF / SVG)
  Transparent  — transparent background  (PNG / TIFF only)
  Tight bbox   — bbox_inches="tight"

Last-used choices are persisted via QSettings.
"""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets

_SETTINGS_KEY = "ExportFigureDialog"
_VECTOR_FORMATS = {"PDF", "SVG"}
_ALPHA_FORMATS  = {"PNG", "TIFF"}


class ExportFigureDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Figure")
        self.setModal(True)
        self.setMinimumWidth(340)
        self._build_ui()
        self._restore_settings()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Destination
        self._dest_cb = QtWidgets.QComboBox()
        self._dest_cb.addItems(["File", "Clipboard"])
        self._dest_cb.currentIndexChanged.connect(self._on_dest_changed)
        layout.addRow("Destination:", self._dest_cb)

        # Format
        self._format_cb = QtWidgets.QComboBox()
        self._format_cb.addItems(["PNG", "PDF", "SVG", "TIFF"])
        self._format_cb.currentTextChanged.connect(self._on_format_changed)
        self._format_label = QtWidgets.QLabel("Format:")
        layout.addRow(self._format_label, self._format_cb)

        # DPI
        self._dpi_spin = QtWidgets.QSpinBox()
        self._dpi_spin.setRange(72, 1200)
        self._dpi_spin.setValue(300)
        self._dpi_spin.setSingleStep(50)
        self._dpi_spin.setSuffix(" dpi")
        self._dpi_label = QtWidgets.QLabel("Resolution:")
        layout.addRow(self._dpi_label, self._dpi_spin)

        # Transparent background
        self._transp_chk = QtWidgets.QCheckBox("Transparent background")
        self._transp_chk.setToolTip("Save with a transparent background (PNG / TIFF only)")
        self._transp_label = QtWidgets.QLabel("")
        layout.addRow(self._transp_label, self._transp_chk)

        # Tight bbox
        self._tight_chk = QtWidgets.QCheckBox("Trim whitespace  (bbox_inches=\"tight\")")
        self._tight_chk.setChecked(True)
        layout.addRow("", self._tight_chk)

        # Buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        self._on_dest_changed(0)
        self._on_format_changed(self._format_cb.currentText())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_dest_changed(self, _index: int) -> None:
        is_file = self._dest_cb.currentText() == "File"
        self._format_cb.setVisible(is_file)
        self._format_label.setVisible(is_file)
        self._dpi_spin.setVisible(is_file)
        self._dpi_label.setVisible(is_file)
        self._transp_chk.setVisible(is_file)
        self._transp_label.setVisible(is_file)
        if is_file:
            self._on_format_changed(self._format_cb.currentText())

    def _on_format_changed(self, fmt: str) -> None:
        if self._dest_cb.currentText() != "File":
            return
        is_vector = fmt in _VECTOR_FORMATS
        self._dpi_spin.setEnabled(not is_vector)
        self._dpi_label.setEnabled(not is_vector)
        supports_alpha = fmt in _ALPHA_FORMATS
        self._transp_chk.setEnabled(supports_alpha)
        self._transp_label.setEnabled(supports_alpha)
        if not supports_alpha:
            self._transp_chk.setChecked(False)

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
            dest   = s.value("destination", "File")
            fmt    = s.value("format",      "PNG")
            dpi    = s.value("dpi",         300, type=int)
            transp = s.value("transparent", False, type=bool)
            tight  = s.value("tight",       True,  type=bool)
            s.endGroup()

            idx = self._dest_cb.findText(dest)
            if idx >= 0:
                self._dest_cb.setCurrentIndex(idx)
            idx = self._format_cb.findText(fmt)
            if idx >= 0:
                self._format_cb.setCurrentText(fmt)
            self._dpi_spin.setValue(dpi)
            self._transp_chk.setChecked(transp)
            self._tight_chk.setChecked(tight)
        except Exception:
            pass

    def _save_settings(self) -> None:
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            s = get_qsettings()
            s.beginGroup(_SETTINGS_KEY)
            s.setValue("destination", self._dest_cb.currentText())
            s.setValue("format",      self._format_cb.currentText())
            s.setValue("dpi",         self._dpi_spin.value())
            s.setValue("transparent", self._transp_chk.isChecked())
            s.setValue("tight",       self._tight_chk.isChecked())
            s.endGroup()
            s.sync()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    @property
    def to_clipboard(self) -> bool:
        return self._dest_cb.currentText() == "Clipboard"

    @property
    def file_format(self) -> str:
        return self._format_cb.currentText()

    @property
    def dpi(self) -> int:
        return self._dpi_spin.value()

    @property
    def transparent(self) -> bool:
        return self._transp_chk.isChecked()

    @property
    def tight(self) -> bool:
        return self._tight_chk.isChecked()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @classmethod
    def run(cls, parent: QtWidgets.QWidget | None = None
            ) -> "ExportFigureDialog | None":
        dlg = cls(parent)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return dlg
        return None
