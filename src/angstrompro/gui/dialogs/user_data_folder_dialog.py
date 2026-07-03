# -*- coding: utf-8 -*-
"""
First-launch dialog for choosing the AngstromPro User Data Folder.

This dialog is shown once, the first time AngstromPro runs (or whenever the
pointer file is missing).  The user picks a folder that lives outside the OS
system directories so it survives reinstalls.  The choice is stored as a tiny
pointer file in the OS-managed location; everything else lives under the
user-chosen folder.
"""

from __future__ import annotations

from pathlib import Path

from angstrompro.utils.qt_compat import QtCore, QtWidgets, Signal
from angstrompro.app.user_data_folder import default_suggestion, set_user_data_folder


class UserDataFolderDialog(QtWidgets.QDialog):
    """
    Modal dialog that lets the user choose their AngstromPro data folder.
    Closes with Accepted only after a valid path is confirmed.
    """

    folderChosen = Signal(Path)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AngstromPro — Choose User Data Folder")
        self.setMinimumWidth(560)
        self.setModal(True)
        self._chosen: Path | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QtWidgets.QLabel("<b>Welcome to AngstromPro</b>")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter
                           if hasattr(QtCore.Qt, "AlignmentFlag")
                           else QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Explanation
        info = QtWidgets.QLabel(
            "Please choose a folder to store your AngstromPro settings, "
            "recent files, and cached data.\n\n"
            "Recommendation: choose a location that survives OS reinstalls, "
            "such as a secondary drive (e.g. D:\\AngstromPro) or a "
            "cloud-synced folder (OneDrive, Dropbox, etc.).\n\n"
            "Avoid paths like C:\\Users\\...\\AppData or system folders — "
            "these are wiped when you reinstall Windows / macOS."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Path row
        path_row = QtWidgets.QHBoxLayout()
        self._path_edit = QtWidgets.QLineEdit()
        self._path_edit.setPlaceholderText("Choose a folder…")
        self._path_edit.setText(str(default_suggestion()))
        self._path_edit.textChanged.connect(self._on_path_changed)
        path_row.addWidget(self._path_edit)

        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        # Warning label (shown when path looks risky)
        self._warning = QtWidgets.QLabel()
        self._warning.setWordWrap(True)
        self._warning.setStyleSheet("color: #c0392b;")
        layout.addWidget(self._warning)

        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._ok_btn = btn_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self._on_path_changed(self._path_edit.text())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        start = self._path_edit.text() or str(Path.home())
        chosen = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose AngstromPro Data Folder", start
        )
        if chosen:
            self._path_edit.setText(chosen)

    def _on_path_changed(self, text: str) -> None:
        path = Path(text.strip()) if text.strip() else None
        warning = self._check_path(path)
        self._warning.setText(warning)
        self._ok_btn.setEnabled(bool(path))

    def _accept(self) -> None:
        text = self._path_edit.text().strip()
        if not text:
            return
        path = Path(text).expanduser().resolve()
        try:
            set_user_data_folder(path)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self, "Cannot create folder",
                f"Could not create the selected folder:\n{exc}"
            )
            return
        self._chosen = path
        self.folderChosen.emit(path)
        self.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_path(path: Path | None) -> str:
        """Return a warning string if the path looks risky, else empty string."""
        if path is None:
            return ""
        s = str(path).lower()
        risky = (
            "appdata", "application support", ".config",
            "programdata", "program files", "windows", "system32",
        )
        if any(r in s for r in risky):
            return (
                "Warning: this path is in an OS-managed directory and may be "
                "cleared on reinstall. Consider a secondary drive or cloud folder."
            )
        return ""

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def chosen_path(self) -> Path | None:
        return self._chosen

    # ------------------------------------------------------------------
    # Convenience class method
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Force to front — important when launched before any main window exists
        self.raise_()
        self.activateWindow()

    @classmethod
    def run(cls, parent: QtWidgets.QWidget | None = None) -> Path | None:
        """
        Show the dialog and return the chosen path, or None if cancelled.
        Blocks until the user confirms or cancels.
        """
        import logging
        logging.getLogger(__name__).info(
            "First launch: showing User Data Folder setup dialog"
        )
        print("[AngstromPro] First launch — please set your User Data Folder "
              "in the dialog window that just opened.")
        dlg = cls(parent)
        # WindowStaysOnTopHint ensures visibility even in IDEs like Spyder
        if hasattr(QtCore.Qt, "WindowType"):
            dlg.setWindowFlags(
                dlg.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint
            )
        else:
            dlg.setWindowFlags(
                dlg.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
            )
        result = dlg.exec()
        accepted = (QtWidgets.QDialog.DialogCode.Accepted
                    if hasattr(QtWidgets.QDialog, "DialogCode")
                    else QtWidgets.QDialog.Accepted)
        if result == accepted:
            return dlg.chosen_path()
        return None
