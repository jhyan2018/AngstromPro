# -*- coding: utf-8 -*-
"""Preference control for queueing a user-data-folder change."""
from __future__ import annotations

from pathlib import Path

from angstrompro.app.user_data_folder import (
    USER_DATA_DIRNAME,
    cancel_pending_user_data_folder,
    get_pending_user_data_folder,
    get_user_data_folder,
    queue_user_data_folder,
    user_data_folder_from_parent,
)
from angstrompro.utils.qt_compat import QtWidgets


class UserDataFolderWidget(QtWidgets.QWidget):
    """Show the active root and queue a replacement for the next runtime."""

    def __init__(self, context=None, parent=None):
        super().__init__(parent)
        self._context = context
        self._selected_path: Path | None = None

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(8)

        current = get_user_data_folder()
        root.addWidget(QtWidgets.QLabel("Current user-data folder"))
        self._current = QtWidgets.QLineEdit(str(current or ""))
        self._current.setReadOnly(True)
        root.addWidget(self._current)

        row = QtWidgets.QHBoxLayout()
        self._pending = QtWidgets.QLineEdit()
        self._pending.setReadOnly(True)
        self._pending.setPlaceholderText("No folder change queued")
        row.addWidget(self._pending, stretch=1)

        choose = QtWidgets.QPushButton("Change…")
        choose.clicked.connect(self._choose_parent)
        row.addWidget(choose)

        self._clear = QtWidgets.QPushButton("Clear queued change")
        self._clear.clicked.connect(self._clear_pending)
        row.addWidget(self._clear)
        root.addLayout(row)

        message = (
            "Choose a parent location; AngstromPro will use its "
            f"'{USER_DATA_DIRNAME}' folder. Existing user data is copied "
            "automatically at the next new session; the old folder is retained "
            "as a backup. "
        )
        if context is not None and getattr(context, "hosted", False):
            message += (
                "The queued change is applied automatically after the Spyder "
                "kernel is restarted and AngstromPro is launched again."
            )
        else:
            message += (
                "The queued change is applied automatically after AngstromPro "
                "fully exits and is launched again."
            )
        hint = QtWidgets.QLabel(message)
        hint.setObjectName("pref_row_desc")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._refresh_pending()

    def _choose_parent(self) -> None:
        current = get_pending_user_data_folder() or get_user_data_folder()
        start = current.parent if current is not None else Path.home()
        chosen = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose Parent Folder for AngstromPro User Data",
            str(start),
        )
        if chosen:
            self._selected_path = user_data_folder_from_parent(Path(chosen))
            self._pending.setText(str(self._selected_path))
            self._clear.setEnabled(True)

    def _clear_pending(self) -> None:
        cancel_pending_user_data_folder()
        self._selected_path = None
        self._refresh_pending()

    def _refresh_pending(self) -> None:
        pending = get_pending_user_data_folder()
        self._pending.setText(str(pending) if pending is not None else "")
        self._clear.setEnabled(pending is not None)

    def set_value(self, _value) -> None:
        self._refresh_pending()

    def get_value(self):
        if self._selected_path is not None:
            try:
                queue_user_data_folder(self._selected_path)
            except (OSError, ValueError) as exc:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Cannot queue user-data folder",
                    f"Could not prepare the selected folder:\n{exc}",
                )
            else:
                self._selected_path = None
                self._refresh_pending()
        return None
