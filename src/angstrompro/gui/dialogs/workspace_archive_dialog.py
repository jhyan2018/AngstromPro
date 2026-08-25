"""Dialogs used by workspace archive save/load flows."""

from __future__ import annotations

from angstrompro.utils.qt_compat import IS_QT6, QtWidgets


class SkippedWorkspaceItemsDialog(QtWidgets.QDialog):
    """Show every item that will be skipped and ask whether to continue."""

    def __init__(
            self, heading: str, lines: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Unsupported workspace items")
        self.resize(560, 360)

        layout = QtWidgets.QVBoxLayout(self)
        message = QtWidgets.QLabel(heading)
        message.setWordWrap(True)
        layout.addWidget(message)

        item_list = QtWidgets.QPlainTextEdit()
        item_list.setReadOnly(True)
        item_list.setPlainText("\n".join(lines))
        layout.addWidget(item_list, 1)

        note = QtWidgets.QLabel(
            "These items will be ignored. Click OK to continue with the "
            "remaining items."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @classmethod
    def confirm(
            cls, heading: str, lines: list[str], parent=None) -> bool:
        dialog = cls(heading, lines, parent)
        accepted = (QtWidgets.QDialog.DialogCode.Accepted
                    if IS_QT6 else QtWidgets.QDialog.Accepted)
        return dialog.exec() == accepted


__all__ = ["SkippedWorkspaceItemsDialog"]
