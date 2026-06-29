# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 2026

@author: jiahaoYan

AGuiModule Qt base class for all AngstromPro GUI modules.

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

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from angstrompro.utils.qt_compat import QtCore, QtWidgets, IS_QT6

log = logging.getLogger(__name__)
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.core.tasks.task_handle import TaskHandle
from .module_mixin import ModuleMixin

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext

_DockArea = (QtCore.Qt.DockWidgetArea.LeftDockWidgetArea if IS_QT6
             else QtCore.Qt.LeftDockWidgetArea)


class AGuiModule(ModuleMixin, QtWidgets.QMainWindow):
    """Base class for every AngstromPro GUI module window."""

    # Subclasses override these to declare what data they work with
    accepted_ndim: int | None = None   # None = any; 2 = 2D only; 3 = 3D only

    # Developer-curated list of process names shown in this module's Process menu.
    # Merged with config "process_menus" (developer) and "user_process_menus" (user).
    default_process_menu: list[str] = []

    # Config sections shown in Edit → Preferences for this module.
    # None = show all (intended for MainWorkbench only).
    config_sections: list[str] | None = ["gui", "algorithms"]

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
        self._build_edit_menu()
        self._build_view_menu()
        self._build_process_menu()
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

    # ------------------------------------------------------------------
    # Process menu
    # ------------------------------------------------------------------

    def _build_process_menu(self) -> None:
        self._process_menu = self.menuBar().addMenu("Process")
        act_browser = self._process_menu.addAction("Process Browser…")
        act_browser.setShortcut("Ctrl+B")
        act_browser.triggered.connect(self._on_open_process_browser)
        act_config = self._process_menu.addAction("Configure Process Menu…")
        act_config.triggered.connect(self._on_configure_process_menu)
        self._process_menu.addSeparator()
        self._rebuild_process_submenu()

    def _rebuild_process_submenu(self) -> None:
        """Rebuild the dynamic category submenus from the 3-layer merged process list."""
        # Remove everything after the fixed header (Browser action + separator = 2 items)
        for act in self._process_menu.actions()[2:]:
            self._process_menu.removeAction(act)

        registry = self._context.processes
        strict   = self._context.config.get("app", "strict_process_menu", True)

        dev_names  = self._context.config.get(
            "algorithms", "process_menus",      {}).get(self.module_id, [])
        user_names = self._context.config.get(
            "algorithms", "user_process_menus", {}).get(self.module_id, [])

        # Merge: class list → developer config → user config; deduplicate, preserve order
        seen: set[str] = set()
        merged: list[str] = []
        for name in list(self.default_process_menu) + list(dev_names) + list(user_names):
            if name not in seen:
                seen.add(name)
                merged.append(name)

        if not merged:
            return

        # Resolve, check compatibility, group by category
        by_category: dict[str, list] = {}
        for name in merged:
            if not registry.has(name):
                log.warning(
                    "Process menu [%s]: %r is not registered — skipped",
                    self.module_id, name,
                )
                continue
            entry = registry.get(name)
            ok, reason = self._check_process_compatibility(entry)
            if not ok:
                log.warning(
                    "Process menu [%s]: %r is incompatible (%s)%s",
                    self.module_id, name, reason,
                    "" if strict else " — added anyway (strict_process_menu=false)",
                )
                if strict:
                    continue
            by_category.setdefault(entry.category, []).append(entry)

        # Build one submenu per category (sorted alphabetically)
        for category in sorted(by_category.keys()):
            submenu = self._process_menu.addMenu(category)
            for entry in by_category[category]:
                act = submenu.addAction(entry.label)
                act.setToolTip(entry.description or entry.name)
                act.triggered.connect(
                    lambda checked=False, n=entry.name: self._on_process_menu_triggered(n)
                )

    def _check_process_compatibility(self, entry) -> tuple[bool, str]:
        """Return (True, "") if the entry is compatible with this module, else (False, reason)."""
        for spec in entry.schema.inputs:
            if self.accepted_types and spec.type_id and spec.type_id not in self.accepted_types:
                return (
                    False,
                    f"input '{spec.name}' type_id={spec.type_id!r} "
                    f"not in accepted_types={self.accepted_types}",
                )
            if (self.accepted_ndim is not None and
                    spec.ndim is not None and
                    spec.ndim != self.accepted_ndim):
                return (
                    False,
                    f"input '{spec.name}' ndim={spec.ndim} "
                    f"!= module accepted_ndim={self.accepted_ndim}",
                )
        return True, ""

    def _on_process_menu_triggered(self, process_name: str) -> None:
        from angstrompro.gui.dialogs.process_param_dialog import ProcessParamDialog
        entry = self._context.processes.get(process_name)

        # Validate process_inputs before opening the param dialog
        ok, msg = self._validate_process_inputs(entry)
        if not ok:
            QtWidgets.QMessageBox.warning(self, "Input data not ready", msg)
            return

        dlg = ProcessParamDialog(entry, self._context, parent=self)
        if dlg.exec():
            params      = dlg.params()
            n           = len(entry.schema.inputs)
            input_items = self.process_inputs[:n]   # take only what the process needs
            self.submit_process(process_name, input_items, params)

    def _validate_process_inputs(self, entry) -> tuple[bool, str]:
        """
        Check that process_inputs satisfies entry.schema.inputs.

        Rules:
          - len(process_inputs) >= len(schema.inputs)
          - For each (spec, item) pair: type_id and ndim must match (None/empty = wildcard)
        """
        required = entry.schema.inputs
        if not required:
            return True, ""   # 0-input process — always valid

        staged = self.process_inputs
        if len(staged) < len(required):
            return (
                False,
                f"'{entry.label}' needs {len(required)} input(s), "
                f"but only {len(staged)} item(s) are staged.\n\n"
                f"Load or select the required data first.",
            )

        for i, (spec, item) in enumerate(zip(required, staged)):
            # type_id check
            if spec.type_id and item.type_id != spec.type_id:
                return (
                    False,
                    f"Input slot {i+1} ('{spec.name}') expects type '{spec.type_id}', "
                    f"but staged item '{item.name}' has type '{item.type_id}'.",
                )
            # ndim check (only for UDS payloads with a .data attribute)
            if spec.ndim is not None:
                payload = item.payload
                actual_ndim = getattr(getattr(payload, "data", None), "ndim", None)
                if actual_ndim is not None and actual_ndim != spec.ndim:
                    return (
                        False,
                        f"Input slot {i+1} ('{spec.name}') expects {spec.ndim}D data, "
                        f"but staged item '{item.name}' has {actual_ndim}D data.",
                    )

        return True, ""

    def _on_open_process_browser(self) -> None:
        from angstrompro.gui.dialogs.process_browser_dialog import ProcessBrowserDialog
        dlg = ProcessBrowserDialog(self._context, parent=self)
        dlg.exec()

    def _on_configure_process_menu(self) -> None:
        from angstrompro.gui.dialogs.process_menu_config_dialog import ProcessMenuConfigDialog
        dlg = ProcessMenuConfigDialog(self._context, initial_module_id=self.module_id, parent=self)
        if dlg.exec():
            self._context.signals.processes_updated.emit()

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

    # ------------------------------------------------------------------
    # Edit menu
    # ------------------------------------------------------------------

    def _build_edit_menu(self) -> None:
        menu = self.menuBar().addMenu("Edit")
        act_prefs = menu.addAction("Preferences…")
        act_prefs.setShortcut("Ctrl+,")
        act_prefs.triggered.connect(self._on_preferences)

    def _on_preferences(self) -> None:
        from angstrompro.gui.widgets.config_editor_widget import ConfigEditorWidget
        from angstrompro.utils.qt_compat import QtWidgets
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Preferences")
        dlg.resize(700, 500)
        layout = QtWidgets.QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ConfigEditorWidget(self._context, dlg,
                                            sections=self.config_sections))
        dlg.exec()

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
        self._context.signals.processes_updated.connect(self._rebuild_process_submenu)

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
    # Process submission convenience
    # ------------------------------------------------------------------

    def submit_process(
        self,
        process_name: str,
        input_items:  list[WorkspaceItem],
        params:       dict[str, Any] | None = None,
        *,
        on_result:    Callable | None = None,
        on_error:     Callable | None = None,
        group_id:     str = "",
    ) -> TaskHandle:
        """
        Submit a registered process as a background task.

        Automatically wires a default error dialog so subclasses only
        need to connect on_result for the happy path.

        Parameters
        ----------
        process_name:
            Dotted process id, e.g. "spatial.crop".
        input_items:
            WorkspaceItems matched to schema.inputs by order.
        params:
            Override values for scalar parameters. Missing keys fall
            back to ProcessSchema defaults.
        on_result:
            Optional callback: on_result(task_id, result).
        on_error:
            Optional extra callback: on_error(task_id, error_text).
            The default error dialog always fires regardless.
        """
        entry  = self._context.processes.get(process_name)
        label  = entry.label

        handle = self.process_runner.run(
            process_name = process_name,
            input_items  = input_items,
            params       = params,
            source_id    = self.instance_id,
            group_id     = group_id,
        )
        handle.error.connect(self._on_process_error)
        handle.result.connect(on_result if on_result is not None
                              else self._on_process_result_default)
        if on_error is not None:
            handle.error.connect(on_error)

        # Status bar feedback wired to this handle's lifecycle
        sb = self.statusBar()
        sb.showMessage(f"{label}: submitted…")
        handle.started.connect(
            lambda _tid, l=label: sb.showMessage(f"{l}: running…"))
        handle.progress.connect(
            lambda _tid, cur, tot, l=label:
                sb.showMessage(f"{l}: {cur}/{tot}"))
        handle.result.connect(
            lambda _tid, _res, l=label: sb.showMessage(f"{l}: done.", 5000))
        handle.error.connect(
            lambda _tid, _err, l=label: sb.showMessage(f"{l}: failed.", 8000))
        handle.cancelled.connect(
            lambda _tid, l=label: sb.showMessage(f"{l}: cancelled.", 5000))

        return handle

    def _on_process_result_default(self, _task_id: str, result: Any) -> None:
        """
        Default result handler: add the returned WorkspaceData to this module's workspace.

        Subclasses that need custom behaviour (e.g. display the result immediately)
        should pass on_result= to submit_process() instead of overriding this.
        """
        from angstrompro.core.data.base import WorkspaceData
        if not isinstance(result, WorkspaceData):
            log.warning(
                "Process returned %s which is not WorkspaceData — not added to workspace",
                type(result).__name__,
            )
            return
        raw_name = getattr(result, "name", None) or "result"
        name     = self.workspace.suggest_name(raw_name)
        self.workspace.add_item(name=name, payload=result)

    def _on_process_error(self, task_id: str, error_text: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Process Error", error_text)

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
