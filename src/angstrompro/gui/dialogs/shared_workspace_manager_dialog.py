# -*- coding: utf-8 -*-
"""Application-level shared workspace management dialog."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets, IS_QT6

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext


class SharedWorkspaceManagerDialog(QtWidgets.QDialog):
    """Create shared workspaces and attach live module instances to them."""

    def __init__(self, context: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.setWindowTitle("Shared Workspace Manager")
        self.resize(720, 460)
        self.setModal(False)
        self._build_ui()
        self._connect_manager_signals()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        explanatory = QtWidgets.QLabel(
            "Shared workspaces belong to the application. Each module can "
            "attach to one shared workspace while retaining access to its "
            "private workspace."
        )
        explanatory.setWordWrap(True)
        layout.addWidget(explanatory)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        workspace_box = QtWidgets.QGroupBox("Shared workspaces")
        workspace_layout = QtWidgets.QVBoxLayout(workspace_box)
        self._workspace_list = QtWidgets.QListWidget()
        workspace_layout.addWidget(self._workspace_list)
        workspace_buttons = QtWidgets.QHBoxLayout()
        self._new_button = QtWidgets.QPushButton("New…")
        self._rename_button = QtWidgets.QPushButton("Rename…")
        self._delete_button = QtWidgets.QPushButton("Delete…")
        workspace_buttons.addWidget(self._new_button)
        workspace_buttons.addWidget(self._rename_button)
        workspace_buttons.addWidget(self._delete_button)
        workspace_layout.addLayout(workspace_buttons)
        archive_buttons = QtWidgets.QHBoxLayout()
        self._import_button = QtWidgets.QPushButton(
            "Import as New Shared Workspace…")
        self._save_button = QtWidgets.QPushButton(
            "Save Selected Shared Workspace…")
        archive_buttons.addWidget(self._import_button)
        archive_buttons.addWidget(self._save_button)
        workspace_layout.addLayout(archive_buttons)
        splitter.addWidget(workspace_box)

        module_box = QtWidgets.QGroupBox("Module attachments")
        module_layout = QtWidgets.QVBoxLayout(module_box)
        self._module_table = QtWidgets.QTableWidget(0, 2)
        self._module_table.setHorizontalHeaderLabels(
            ["Module instance", "Attached shared workspace"])
        self._module_table.verticalHeader().setVisible(False)
        self._module_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self._module_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._module_table.horizontalHeader()
        header.setStretchLastSection(True)
        module_layout.addWidget(self._module_table)
        splitter.addWidget(module_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._new_button.clicked.connect(self._create_workspace)
        self._rename_button.clicked.connect(self._rename_workspace)
        self._delete_button.clicked.connect(self._delete_workspace)
        self._import_button.clicked.connect(self._import_workspace)
        self._save_button.clicked.connect(self._save_workspace)
        self._workspace_list.currentItemChanged.connect(
            lambda *_args: self._update_workspace_buttons())

    def _connect_manager_signals(self) -> None:
        workspace_manager = self._context.workspace_manager
        workspace_manager.workspace_created.connect(lambda *_args: self._refresh())
        workspace_manager.workspace_removed.connect(lambda *_args: self._refresh())
        workspace_manager.workspace_renamed.connect(lambda *_args: self._refresh())
        workspace_manager.item_added.connect(lambda *_args: self._refresh())
        workspace_manager.item_removed.connect(lambda *_args: self._refresh())
        workspace_manager.module_attachment_changed.connect(
            lambda *_args: QtCore.QTimer.singleShot(0, self._refresh))
        module_manager = self._context.module_manager
        module_manager.module_added.connect(lambda *_args: self._refresh_modules())
        module_manager.module_removed.connect(lambda *_args: self._refresh_modules())

    @property
    def _user_role(self):
        return (QtCore.Qt.ItemDataRole.UserRole
                if IS_QT6 else QtCore.Qt.UserRole)

    def _selected_workspace_id(self) -> str | None:
        item = self._workspace_list.currentItem()
        return item.data(self._user_role) if item is not None else None

    def _refresh(self) -> None:
        selected_id = self._selected_workspace_id()
        self._workspace_list.blockSignals(True)
        self._workspace_list.clear()
        selected_row = -1
        for row, workspace in enumerate(
                self._context.workspace_manager.list_shared_workspaces()):
            attached = len(
                self._context.workspace_manager.attached_module_ids(
                    workspace.workspace_id))
            item = QtWidgets.QListWidgetItem(
                f"{workspace.label}  ({workspace.count()} items, "
                f"{attached} modules)")
            item.setData(self._user_role, workspace.workspace_id)
            self._workspace_list.addItem(item)
            if workspace.workspace_id == selected_id:
                selected_row = row
        self._workspace_list.blockSignals(False)
        if self._workspace_list.count():
            self._workspace_list.setCurrentRow(
                selected_row if selected_row >= 0 else 0)
        self._update_workspace_buttons()
        self._refresh_modules()

    def _refresh_modules(self) -> None:
        manager = self._context.workspace_manager
        workspaces = manager.list_shared_workspaces()
        instances = self._context.module_manager.list_instances()
        self._module_table.setRowCount(len(instances))
        for row, instance in enumerate(instances):
            label = f"{instance.display_name or instance.module_id}  [{instance.instance_id}]"
            self._module_table.setItem(row, 0, QtWidgets.QTableWidgetItem(label))

            combo = QtWidgets.QComboBox()
            combo.addItem("Not attached", "")
            for workspace in workspaces:
                combo.addItem(workspace.label, workspace.workspace_id)
            attached = manager.shared_workspace_for_module(instance.instance_id)
            attached_id = attached.workspace_id if attached is not None else ""
            index = combo.findData(attached_id)
            combo.setCurrentIndex(max(index, 0))
            combo.currentIndexChanged.connect(
                lambda _index, iid=instance.instance_id, widget=combo:
                self._set_module_attachment(iid, widget.currentData()))
            self._module_table.setCellWidget(row, 1, combo)
        self._module_table.resizeColumnToContents(0)

    def _update_workspace_buttons(self) -> None:
        enabled = self._selected_workspace_id() is not None
        self._rename_button.setEnabled(enabled)
        self._delete_button.setEnabled(enabled)
        self._save_button.setEnabled(enabled)

    def _create_workspace(self) -> None:
        name, accepted = QtWidgets.QInputDialog.getText(
            self, "New Shared Workspace", "Workspace name:")
        if not accepted:
            return
        try:
            workspace = self._context.workspace_manager.create_shared_workspace(name)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Cannot create workspace", str(exc))
            return
        self._refresh()
        for row in range(self._workspace_list.count()):
            item = self._workspace_list.item(row)
            if item.data(self._user_role) == workspace.workspace_id:
                self._workspace_list.setCurrentRow(row)
                break

    def _rename_workspace(self) -> None:
        workspace_id = self._selected_workspace_id()
        if workspace_id is None:
            return
        workspace = self._context.workspace_manager.get_workspace(workspace_id)
        echo_mode = getattr(
            QtWidgets.QLineEdit, "EchoMode", QtWidgets.QLineEdit).Normal
        name, accepted = QtWidgets.QInputDialog.getText(
            self, "Rename Shared Workspace", "Workspace name:",
            echo_mode, workspace.label)
        if not accepted:
            return
        try:
            self._context.workspace_manager.rename_shared_workspace(
                workspace_id, name)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Cannot rename workspace", str(exc))

    def _delete_workspace(self) -> None:
        workspace_id = self._selected_workspace_id()
        if workspace_id is None:
            return
        manager = self._context.workspace_manager
        workspace = manager.get_workspace(workspace_id)
        attached_count = len(manager.attached_module_ids(workspace_id))
        message = (
            f"Delete shared workspace '{workspace.label}' and its "
            f"{workspace.count()} item(s)?"
        )
        if attached_count:
            message += (
                f"\n\n{attached_count} attached module(s) will return to "
                "their private workspaces."
            )
        answer = QtWidgets.QMessageBox.question(
            self,
            "Delete Shared Workspace?",
            message,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            manager.remove_shared_workspace(workspace_id)

    def _set_module_attachment(
            self, instance_id: str, workspace_id: str | None) -> None:
        manager = self._context.workspace_manager
        if workspace_id:
            manager.attach_module(instance_id, workspace_id)
        else:
            manager.detach_module(instance_id)

    def _selected_workspace(self):
        workspace_id = self._selected_workspace_id()
        if workspace_id is None:
            return None
        try:
            return self._context.workspace_manager.get_workspace(workspace_id)
        except KeyError:
            return None

    def _confirm_skipped_items(
            self, heading: str, entries: list,
            *, allow_cancel: bool = True) -> bool:
        from angstrompro.gui.dialogs.workspace_archive_dialog import (
            SkippedWorkspaceItemsDialog,
        )

        lines = []
        for entry in entries:
            name = getattr(entry, "name", "") or "(unnamed item)"
            type_id = getattr(entry, "type_id", "") or "unknown"
            provider = getattr(entry, "provider", "")
            reason = getattr(entry, "reason", "")
            line = f"{name}  [{type_id}]"
            if provider:
                line += f"  — provider: {provider}"
            if reason and reason != "Unsupported payload type":
                line += f"\n    {reason}"
            lines.append(line)
        return SkippedWorkspaceItemsDialog.confirm(
            heading, lines, parent=self, allow_cancel=allow_cancel)

    def _save_workspace(self) -> None:
        from angstrompro.io.workspace_io import (
            save_workspace, split_supported_items,
        )

        workspace = self._selected_workspace()
        if workspace is None:
            return
        items = workspace.list_items()
        if not items:
            QtWidgets.QMessageBox.information(
                self, "Empty workspace",
                f"Workspace '{workspace.label}' has no items to save.")
            return
        supported, unsupported = split_supported_items(items)
        if unsupported and not self._confirm_skipped_items(
                "These workspace items cannot be stored in the archive:",
                unsupported):
            return
        if not supported:
            QtWidgets.QMessageBox.information(
                self, "Nothing to save",
                "None of the workspace items have a supported payload type.")
            return

        start_dir = (
            self._context.config.get("io", "default_save_dir")
            or self._context.config.get("io", "default_open_dir")
            or ""
        )
        safe_name = re.sub(r'[<>:"/\\|?*]+', "_", workspace.label).strip()
        suggested_name = (safe_name or "workspace") + ".apws"
        suggested = (str(Path(start_dir) / suggested_name)
                     if start_dir else suggested_name)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            f"Save Shared Workspace — {workspace.label}",
            suggested,
            "AngstromPro Workspace (*.apws);;HDF5 (*.h5 *.hdf5)",
        )
        if not path:
            return
        archive_path = Path(path)
        if not archive_path.suffix:
            archive_path = archive_path.with_suffix(".apws")
        try:
            save_workspace(archive_path, workspace)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Workspace save failed", str(exc))
            return
        QtWidgets.QMessageBox.information(
            self,
            "Shared Workspace Saved",
            f"Saved {len(supported)} item(s) from '{workspace.label}' to:\n"
            f"{archive_path}",
        )

    def _import_workspace(self) -> None:
        from angstrompro.io.workspace_io import import_workspace, load_workspace

        start_dir = self._context.config.get("io", "default_open_dir") or ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import as New Shared Workspace",
            start_dir,
            "AngstromPro Workspace (*.apws *.h5 *.hdf5);;All Files (*)",
        )
        if not path:
            return
        archive_path = Path(path)
        try:
            archive = load_workspace(archive_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Workspace import failed", str(exc))
            return
        if archive.skipped:
            self._confirm_skipped_items(
                "These archive items cannot be loaded by this installation "
                "and were skipped:",
                archive.skipped,
                allow_cancel=False,
            )
        if not archive.items:
            QtWidgets.QMessageBox.information(
                self, "Nothing to import",
                "The workspace archive contains no supported items.")
            return

        manager = self._context.workspace_manager
        existing_labels = {
            workspace.label for workspace in manager.list_shared_workspaces()
        }
        base_label = archive.label.strip() or archive_path.stem or "Imported workspace"
        label = base_label
        suffix = 2
        while label in existing_labels:
            label = f"{base_label}_{suffix}"
            suffix += 1

        workspace = manager.create_shared_workspace(label)
        try:
            imported, renamed = import_workspace(archive, workspace)
        except Exception as exc:
            manager.remove_shared_workspace(workspace.workspace_id)
            QtWidgets.QMessageBox.critical(
                self, "Workspace import failed", str(exc))
            return

        self._refresh()
        for row in range(self._workspace_list.count()):
            item = self._workspace_list.item(row)
            if item.data(self._user_role) == workspace.workspace_id:
                self._workspace_list.setCurrentRow(row)
                break
        message = (
            f"Created shared workspace '{workspace.label}' with "
            f"{len(imported)} item(s)."
        )
        if renamed:
            message += f"\n{len(renamed)} item(s) were renamed to avoid conflicts."
        QtWidgets.QMessageBox.information(
            self, "Shared Workspace Imported", message)
