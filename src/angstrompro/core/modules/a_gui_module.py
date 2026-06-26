"""
AGuiModule — Qt base class for all AngstromPro GUI modules.

Combines ModuleMixin (workspace, identity, future resources) with
QMainWindow (menu bar, dock widgets, status bar).

Each GUI module is an independent QMainWindow with:
  - workspace panel dock (item list, double-click to load)
  - Process menu with Process Browser (Ctrl+B)
  - status bar wired to context.signals.status_message
  - auto-refresh when its workspace changes

Subclass contract
-----------------
    @register_module
    class Image2U3(AGuiModule):
        module_id      = "image2u3"
        display_name   = "Image 2U3"
        description    = "STM image analysis."
        accepted_types = {"uds"}

        def build_ui(self) -> None:
            self.setCentralWidget(...)

        def on_item_loaded(self, item: WorkspaceItem) -> None:
            ...

        def on_workspace_changed(self) -> None:   # optional
            ...
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets, IS_QT6
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from .module_mixin import ModuleMixin

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext

_DockArea = (QtCore.Qt.DockWidgetArea.LeftDockWidgetArea if IS_QT6
             else QtCore.Qt.LeftDockWidgetArea)


class AGuiModule(ModuleMixin, QtWidgets.QMainWindow):
    """Base class for every AngstromPro GUI module window."""

    def __init__(
        self,
        context: "AppContext",
        parent:  QtWidgets.QWidget | None = None,
    ) -> None:
        QtWidgets.QMainWindow.__init__(self, parent)
        self._init_module(context)   # sets self.workspace, self._context

        self.setWindowTitle(self.display_name or self.module_id)
        self.resize(900, 640)

        self._build_file_menu()
        self._build_view_menu()
        self._build_workspace_dock()
        self._build_inspector_dock()
        self._finalise_view_menu()
        self._connect_signals()

        self.build_ui()   # subclass sets central widget

    # ------------------------------------------------------------------
    # Workspace dock
    # ------------------------------------------------------------------

    def _build_workspace_dock(self) -> None:
        dock = QtWidgets.QDockWidget("Workspace", self)
        dock.setObjectName("workspace_dock")
        dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea |
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea
            if IS_QT6 else
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea
        )

        container = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(container)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(4)

        self._ws_list = QtWidgets.QListWidget()
        self._ws_list.itemDoubleClicked.connect(self._on_ws_item_double_clicked)
        vbox.addWidget(self._ws_list)

        # item action buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_add    = QtWidgets.QPushButton("Add")
        btn_remove = QtWidgets.QPushButton("Remove")
        btn_send   = QtWidgets.QPushButton("Send…")
        self._send_default_cb = QtWidgets.QCheckBox("Default")
        btn_add.clicked.connect(self._on_add_item)
        btn_remove.clicked.connect(self._on_remove_item)
        btn_send.clicked.connect(self._on_send_item)
        self._send_default_cb.toggled.connect(self._on_default_toggled)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_send)
        btn_row.addWidget(self._send_default_cb)
        vbox.addLayout(btn_row)

        dock.setWidget(container)
        self.addDockWidget(_DockArea, dock)
        self._workspace_dock = dock

    # ------------------------------------------------------------------
    # Inspector dock
    # ------------------------------------------------------------------

    def _build_inspector_dock(self) -> None:
        from angstrompro.gui.widgets.workspace_item_inspector import WorkspaceItemInspector
        dock = QtWidgets.QDockWidget("Inspector", self)
        dock.setObjectName("inspector_dock")
        dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea |
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea
            if IS_QT6 else
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea
        )
        self._inspector = WorkspaceItemInspector()
        dock.setWidget(self._inspector)
        self.addDockWidget(_DockArea, dock)
        self.tabifyDockWidget(self._workspace_dock, dock)
        self._workspace_dock.raise_()   # workspace tab active by default
        self._inspector_dock = dock
        dock.hide()                     # collapsed by default

    # ------------------------------------------------------------------
    # View menu
    # ------------------------------------------------------------------

    def _build_view_menu(self) -> None:
        self._view_menu = self.menuBar().addMenu("View")
        # actions added after docks are built, in _finalise_view_menu()

    def _finalise_view_menu(self) -> None:
        act_ws = self._workspace_dock.toggleViewAction()
        act_ws.setText("Workspace")
        act_ws.setShortcut("Ctrl+1")
        self._view_menu.addAction(act_ws)

        act_insp = self._inspector_dock.toggleViewAction()
        act_insp.setText("Inspector")
        act_insp.setShortcut("Ctrl+2")
        self._view_menu.addAction(act_insp)

    def _refresh_workspace_panel(self) -> None:
        self._ws_list.clear()
        for item in self.workspace.list_items():
            label = f"{item.display_name}  [{item.type_id}]"
            list_item = QtWidgets.QListWidgetItem(label)
            list_item.setData(
                QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole,
                item.name,
            )
            self._ws_list.addItem(list_item)

    def _selected_item_name(self) -> str | None:
        item = self._ws_list.currentItem()
        if item is None:
            return None
        return item.data(QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole)

    def _on_ws_item_double_clicked(self, list_item: QtWidgets.QListWidgetItem) -> None:
        name = list_item.data(
            QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        )
        item = self.workspace.get_item(name)
        try:
            self.load_item(item)
        except TypeError as exc:
            QtWidgets.QMessageBox.warning(self, "Type mismatch", str(exc))

    def _on_add_item(self) -> None:
        self.on_add_item()

    def _on_remove_item(self) -> None:
        name = self._selected_item_name()
        if name:
            self.workspace.remove_item(name)

    def _on_default_toggled(self, checked: bool) -> None:
        if not checked:
            return
        mm = self._context.module_manager
        current_ids = mm.get_default_target_ids(self.instance_id)
        from angstrompro.gui.dialogs.set_default_targets_dialog import SetDefaultTargetsDialog
        dlg = SetDefaultTargetsDialog(
            self._context,
            exclude_instance_id=self.instance_id,
            current_target_ids=current_ids,
            parent=self,
        )
        if dlg.exec() and dlg.selected_modules:
            mm.set_default_targets(
                self.instance_id,
                [inst.instance_id for inst in dlg.selected_modules],
            )
        else:
            # revert — nothing selected or cancelled
            self._send_default_cb.blockSignals(True)
            self._send_default_cb.setChecked(False)
            self._send_default_cb.blockSignals(False)

    def _on_send_item(self) -> None:
        name = self._selected_item_name()
        if not name:
            QtWidgets.QMessageBox.warning(self, "No item selected", "Select an item to send.")
            return
        if self._send_default_cb.isChecked():
            targets = self._context.module_manager.get_default_targets(self.instance_id)
            if not targets:
                QtWidgets.QMessageBox.warning(
                    self, "No default targets",
                    "Default targets are gone. Uncheck Default to pick manually."
                )
                return
            for target in targets:
                self._context.workspace_manager.transfer_item(
                    src_workspace_id=self.workspace.workspace_id,
                    dst_workspace_id=target.workspace.workspace_id,
                    item_name=name,
                )
        else:
            from angstrompro.gui.dialogs.send_item_dialog import SendItemDialog
            dlg = SendItemDialog(self._context, exclude_instance_id=self.instance_id, parent=self)
            if dlg.exec() and dlg.selected_module:
                target = dlg.selected_module
                self._context.workspace_manager.transfer_item(
                    src_workspace_id=self.workspace.workspace_id,
                    dst_workspace_id=target.workspace.workspace_id,
                    item_name=name,
                )

    # ------------------------------------------------------------------
    # File menu
    # ------------------------------------------------------------------

    def _build_file_menu(self) -> None:
        menu = self.menuBar().addMenu("File")

        act_open = menu.addAction("Open…")
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_file_open)

        act_save = menu.addAction("Save…")
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._on_file_save)

        menu.addSeparator()

        act_close = menu.addAction("Close Window")
        act_close.setShortcut("Ctrl+W")
        act_close.triggered.connect(self.hide)

    def _on_file_open(self) -> None:
        from angstrompro.io.angstrom_io import registered_formats
        formats = registered_formats()
        filters = ";;".join(
            f"{f.display_name} (*{f.extension})" for f in formats if f.readable
        )
        filters += ";;All Files (*)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", "", filters)
        if not path:
            return
        from pathlib import Path
        from angstrompro.io import load
        try:
            payload = load(Path(path))
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Open failed", str(exc))
            return
        name = self.workspace.suggest_name(Path(path).stem)
        self.workspace.add_item(name=name, payload=payload)

    def _on_file_save(self) -> None:
        name = self._selected_item_name()
        if not name:
            QtWidgets.QMessageBox.warning(self, "No item selected",
                                          "Select a workspace item to save.")
            return
        item = self.workspace.get_item(name)
        from angstrompro.io.angstrom_io import registered_formats
        formats = [f for f in registered_formats()
                   if f.writable and f.type_id == item.payload.type_id]
        if formats:
            default_ext = formats[0].extension
            filters = ";;".join(
                f"{f.display_name} (*{f.extension})" for f in formats
            )
        else:
            default_ext = ""
            filters = "All Files (*)"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Item", name + default_ext, filters
        )
        if not path:
            return
        from pathlib import Path
        from angstrompro.io import save
        try:
            save(Path(path), item.payload)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        wid = self.workspace.workspace_id
        wm  = self._context.workspace_manager

        def _guard(ws_id, *_args):
            if ws_id == wid:
                self._refresh_workspace_panel()
                self.on_workspace_changed()

        wm.item_added.connect(_guard)
        wm.item_removed.connect(_guard)
        wm.item_renamed.connect(_guard)

        self._ws_list.currentItemChanged.connect(self._on_ws_selection_changed)

        self._context.signals.status_message.connect(self.statusBar().showMessage)

    def _on_ws_selection_changed(self, current, _previous) -> None:
        if current is None:
            self._inspector.set_item(None)
            return
        name = current.data(
            QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        )
        item = self.workspace.get_item(name) if self.workspace.has_item(name) else None
        self._inspector.set_item(item)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_item(self, item: WorkspaceItem) -> None:
        if self.accepted_types and item.type_id not in self.accepted_types:
            raise TypeError(
                f"{self.__class__.__name__} does not accept type "
                f"{item.type_id!r}. Accepted: {self.accepted_types}"
            )
        self.on_item_loaded(item)

    def accepts(self, item: WorkspaceItem) -> bool:
        return not self.accepted_types or item.type_id in self.accepted_types

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    @abstractmethod
    def build_ui(self) -> None:
        """Build and set the central widget. Called once during __init__."""

    @abstractmethod
    def on_item_loaded(self, item: WorkspaceItem) -> None:
        """Called when a workspace item is double-clicked / activated."""

    def on_add_item(self) -> None:
        """Called when the Add button is clicked. Override to add module-specific items."""

    def on_workspace_changed(self) -> None:
        """Called after any workspace mutation. Override for extra refresh logic."""

    def closeEvent(self, event) -> None:
        """Hide the window instead of destroying it. Use module_manager.remove() to fully remove."""
        self.hide()
        event.ignore()
