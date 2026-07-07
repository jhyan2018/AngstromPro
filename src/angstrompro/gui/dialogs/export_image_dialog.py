# -*- coding: utf-8 -*-
"""
Export Image dialog for ImageStackViewer.

Presents four choices:
  Panel       — Main / Aux
  Annotations — include overlays (checkbox)
  Destination — Clipboard / File
  Format      — PNG / TIFF / JPEG  (only when Destination = File)

Last-used choices are persisted via QSettings (settings.ini).
"""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets


_SETTINGS_KEY = "ExportImageDialog"


class ExportImageDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget | None = None,
                 has_aux: bool = True) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Image")
        self.setModal(True)
        self.setMinimumWidth(320)
        self._has_aux = has_aux
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
        layout.addRow("", self._overlay_chk)

        # Destination
        self._dest_cb = QtWidgets.QComboBox()
        self._dest_cb.addItems(["Clipboard", "File"])
        self._dest_cb.currentIndexChanged.connect(self._on_dest_changed)
        layout.addRow("Destination:", self._dest_cb)

        # Format (only visible when Destination = File)
        self._format_cb = QtWidgets.QComboBox()
        self._format_cb.addItems(["PNG", "TIFF", "JPEG"])
        self._format_row_label = QtWidgets.QLabel("Format:")
        layout.addRow(self._format_row_label, self._format_cb)

        # Buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        self._on_dest_changed(self._dest_cb.currentIndex())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_dest_changed(self, index: int) -> None:
        is_file = (index == 1)
        self._format_cb.setVisible(is_file)
        self._format_row_label.setVisible(is_file)

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
            panel = s.value("panel", "Input")
            overlay = s.value("overlay", True, type=bool)
            dest = s.value("destination", "Clipboard")
            fmt = s.value("format", "PNG")
            s.endGroup()

            idx = self._panel_cb.findText(panel)
            if idx >= 0:
                self._panel_cb.setCurrentIndex(idx)
            self._overlay_chk.setChecked(overlay)
            idx = self._dest_cb.findText(dest)
            if idx >= 0:
                self._dest_cb.setCurrentIndex(idx)
            idx = self._format_cb.findText(fmt)
            if idx >= 0:
                self._format_cb.setCurrentIndex(idx)
        except Exception:
            pass  # first run or folder not set — use defaults silently

    def _save_settings(self) -> None:
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            s = get_qsettings()
            s.beginGroup(_SETTINGS_KEY)
            s.setValue("panel",       self._panel_cb.currentText())
            s.setValue("overlay",     self._overlay_chk.isChecked())
            s.setValue("destination", self._dest_cb.currentText())
            s.setValue("format",      self._format_cb.currentText())
            s.endGroup()
            s.sync()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    @property
    def panel(self) -> str:
        """'Main' or 'Aux'"""
        return self._panel_cb.currentText()

    @property
    def with_overlay(self) -> bool:
        return self._overlay_chk.isChecked()

    @property
    def to_clipboard(self) -> bool:
        return self._dest_cb.currentText() == "Clipboard"

    @property
    def file_format(self) -> str:
        """'PNG', 'TIFF', or 'JPEG'  (only relevant when to_clipboard is False)"""
        return self._format_cb.currentText()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @classmethod
    def run(cls, parent: QtWidgets.QWidget | None = None,
            has_aux: bool = True) -> "ExportImageDialog | None":
        dlg = cls(parent, has_aux=has_aux)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return dlg
        return None
