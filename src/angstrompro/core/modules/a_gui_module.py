# -*- coding: utf-8 -*-
"""
Created on Tue Jun 23 22:54:12 2026

@author: jiahaoYan

AGuiModule — Qt base class for all AngstromPro GUI modules.

Each GUI module is an independent QMainWindow with:
  - workspace and identity via ModuleMixin
  - a workspace panel dock (item list + type badge)
  - a Process menu auto-connected to ProcessBrowserDialog
  - status bar wired to context.signals.status_message
  - WorkspaceManager signal connections for auto-refresh

Subclass contract
-----------------
    @register_module
    class Image2U3(AGuiModule):
        module_id      = "image2u3"
        display_name   = "Image 2U3"
        description    = "STM image analysis."
        accepted_types = {"uds"}

        def build_ui(self) -> None:
            # build and set the central widget
            self.setCentralWidget(...)

        def on_item_loaded(self, item: WorkspaceItem) -> None:
            # react to a workspace item being activated
            ...

        def on_workspace_changed(self) -> None:
            # optional — workspace panel auto-refreshes; override for extra logic
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

_DockArea = QtCore.Qt.DockWidgetArea.LeftDockWidgetArea if IS_QT6 \
            else QtCore.Qt.LeftDockWidgetArea


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

        self._build_workspace_dock()
        self._build_process_menu()
        self._connect_signals()

        # subclass builds its central widget
        self.build_ui()

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

        dock.setWidget(container)
        self.addDockWidget(_DockArea, dock)
        self._workspace_dock = dock

    def _refresh_workspace_panel(self) -> None:
        self._ws_list.clear()
        for item in self.workspace.list_items():
            label = f"{item.display_name}  [{item.type_id}]"
            list_item = QtWidgets.QListWidgetItem(label)
            list_item.setData(QtCore.Qt.ItemDataRole.UserRole if IS_QT6
                              else QtCore.Qt.UserRole, item.name)
            self._ws_list.addItem(list_item)

    def _on_ws_item_double_clicked(self, list_item: QtWidgets.QListWidgetItem) -> None:
        name = list_item.data(QtCore.Qt.ItemDataRole.UserRole if IS_QT6
                              else QtCore.Qt.UserRole)
        item = self.workspace.get_item(name)
        try:
            self.load_item(item)
        except TypeError as exc:
            QtWidgets.QMessageBox.warning(self, "Type mismatch", str(exc))

    # ------------------------------------------------------------------
    # Process menu
    # ------------------------------------------------------------------

    def _build_process_menu(self) -> None:
        menu = self.menuBar().addMenu("Process")
        browser_action = menu.addAction("Process Browser…")
        browser_action.setShortcut("Ctrl+B")
        browser_action.triggered.connect(self._open_process_browser)

    def _open_process_browser(self) -> None:
        from angstrompro.gui.dialogs.process_browser_dialog import ProcessBrowserDialog
        dlg = ProcessBrowserDialog(self._context, parent=self)
        dlg.exec()

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

        self._context.signals.status_message.connect(
            self.statusBar().showMessage
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_item(self, item: WorkspaceItem) -> None:
        """Validate type then call on_item_loaded."""
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

    def on_workspace_changed(self) -> None:
        """Called after any workspace mutation. Override for extra refresh logic."""
