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

    # Simulation names shown in the Simulate menu (kind="simulation" entries only).
    default_simulate_menu: list[str] = []

    # Config sections shown in Edit → Preferences for this module.
    # None = show all (intended for MainWorkbench only).
    config_sections: list[str] | None = ["algorithms"]

    # Short badge labels shown next to staged items in the workspace panel.
    # Index matches process_inputs order.  e.g. ["M", "A"] for ImageStackViewer.
    staged_labels: list[str] = []

    # ── process_inputs property ──────────────────────────────────────────
    # Wraps the plain list from ModuleMixin so the workspace panel refreshes
    # automatically whenever staged items change.

    @property
    def process_inputs(self) -> list:
        return self._process_inputs

    @process_inputs.setter
    def process_inputs(self, value: list) -> None:
        self._process_inputs = list(value)
        if hasattr(self, "_ws_list"):
            self._refresh_workspace_panel()

    # ── init ─────────────────────────────────────────────────────────────

    def __init__(
        self,
        context: "AppContext",
        parent:  QtWidgets.QWidget | None = None,
    ) -> None:
        QtWidgets.QMainWindow.__init__(self, parent)
        self._process_inputs: list = []          # backing store for the property
        self._init_module(context)   # sets self.workspace, self._context

        # Per-instance runtime copy of this module's config slice.
        # Plugin modules (module_id contains a dot) use isolated per-plugin config files.
        if "." in self.module_id:
            _plugin_ns = self.module_id.split(".")[0]
            self._plugin_ns: str | None = _plugin_ns
            self._config: dict = context.get_plugin_config(_plugin_ns).get_module(self.module_id)
        else:
            self._plugin_ns = None
            self._config: dict = context.config.get_group("modules").get(self.module_id, {})

        self.setWindowTitle(self.display_name or self.module_id)
        self.resize(900, 640)

        self._build_file_menu()
        self._build_edit_menu()
        self._build_view_menu()
        self._build_process_menu()
        self._build_simulate_menu()
        self._build_workspace_dock()
        self._build_inspector_dock()
        self._finalise_view_menu()
        self._connect_signals()

        self.build_ui()   # subclass sets central widget
        self._build_help_menu()  # always the rightmost menu

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

        self._ws_list = QtWidgets.QTreeWidget()
        self._ws_list.setColumnCount(2)
        self._ws_list.setHeaderLabels(["Name", "Info"])
        _Interactive = (QtWidgets.QHeaderView.ResizeMode.Interactive
                        if IS_QT6 else QtWidgets.QHeaderView.Interactive)
        self._ws_list.header().setStretchLastSection(True)
        self._ws_list.header().setSectionResizeMode(0, _Interactive)
        self._ws_list.header().setMinimumSectionSize(60)
        self._ws_list.setColumnWidth(0, 200)
        self._ws_list.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu if IS_QT6
            else QtCore.Qt.CustomContextMenu
        )
        self._ws_list.itemDoubleClicked.connect(self._on_ws_item_double_clicked)
        self._ws_list.customContextMenuRequested.connect(self._on_ws_context_menu)
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
        # Remove everything after the fixed header (Browser + Configure + separator = 3 items)
        for act in self._process_menu.actions()[3:]:
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

    def _build_simulate_menu(self) -> None:
        """Build the Simulate top-level menu from default_simulate_menu + config."""
        if not self.default_simulate_menu:
            return  # module declares no simulations — skip menu entirely

        self._simulate_menu = self.menuBar().addMenu("Simulate")
        registry = self._context.processes

        by_category: dict[str, list] = {}
        for name in self.default_simulate_menu:
            if not registry.has(name):
                log.warning("Simulate menu [%s]: %r not registered — skipped",
                            self.module_id, name)
                continue
            entry = registry.get(name)
            if entry.kind != "simulation":
                log.warning("Simulate menu [%s]: %r has kind=%r, expected 'simulation' — skipped",
                            self.module_id, name, entry.kind)
                continue
            by_category.setdefault(entry.category, []).append(entry)

        for category in sorted(by_category.keys()):
            if len(by_category) > 1:
                submenu = self._simulate_menu.addMenu(category)
                target_menu = submenu
            else:
                target_menu = self._simulate_menu
            for entry in by_category[category]:
                act = target_menu.addAction(entry.label)
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

        pre_staged   = self.process_inputs[:len(entry.schema.inputs)]
        ws_items     = self.workspace.list_items()
        dlg = ProcessParamDialog(
            entry, self._context, parent=self,
            input_items=pre_staged, workspace_items=ws_items,
        )
        if dlg.exec():
            params      = dlg.params()
            self.submit_process(process_name, dlg.input_items(), params)

    def _validate_process_inputs(self, entry) -> tuple[bool, str]:
        """
        Check that process_inputs satisfies entry.schema.inputs.

        Rules:
          - len(process_inputs) >= number of required inputs (spec.required=True)
          - For each (spec, item) pair that is staged: type_id and ndim must match
        """
        specs = entry.schema.inputs
        if not specs:
            return True, ""   # 0-input process — always valid

        n_required = sum(1 for s in specs if s.required)
        staged = self.process_inputs

        if len(staged) < n_required:
            req_names = ", ".join(f"'{s.name}'" for s in specs if s.required)
            return (
                False,
                f"'{entry.label}' needs {n_required} required input(s) "
                f"({req_names}), but only {len(staged)} item(s) are staged.\n\n"
                f"Load or select the required data first.",
            )

        for i, (spec, item) in enumerate(zip(specs, staged)):
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

    def _build_help_menu(self) -> None:
        # Create a temporary menu to let subclasses populate it;
        # only add it to the menu bar if the subclass added any items.
        tmp = QtWidgets.QMenu("Help", self)
        self._populate_help_menu(tmp)
        if not tmp.isEmpty():
            self._help_menu = self.menuBar().addMenu("Help")
            for action in tmp.actions():
                self._help_menu.addAction(action)
        else:
            self._help_menu = None

    def _populate_help_menu(self, menu: QtWidgets.QMenu) -> None:
        """Hook for subclasses to append items to the Help menu."""

    def _on_open_process_browser(self) -> None:
        from angstrompro.gui.dialogs.process_browser_dialog import ProcessBrowserDialog
        dlg = ProcessBrowserDialog(self._context, parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dlg.show()

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

    def _ann_summary(self, ann) -> str:
        """One-line summary string for an annotation object."""
        from angstrompro.core.data.annotation_data import PointSetData, RegionData, LineData
        if isinstance(ann, PointSetData):
            return f"[{len(ann.coords)} pts]"
        if isinstance(ann, RegionData):
            return (f"r[{ann.row_min}:{ann.row_max}] "
                    f"c[{ann.col_min}:{ann.col_max}]")
        if isinstance(ann, LineData):
            return f"{ann.p1} → {ann.p2}"
        return str(ann)

    # Badge colours for staged_labels — cycles if more labels than colours
    _BADGE_COLORS = ["#2196F3", "#FF9800", "#4CAF50", "#9C27B0", "#F44336"]

    def _refresh_workspace_panel(self) -> None:
        from angstrompro.utils.qt_compat import QtGui
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole

        # Build a map: item.name → (label_text, color) for staged items
        staged_map: dict[str, tuple[str, str]] = {}
        for idx, ws_item in enumerate(self._process_inputs):
            if ws_item is None:
                continue
            if idx < len(self.staged_labels):
                label = self.staged_labels[idx]
                color = self._BADGE_COLORS[idx % len(self._BADGE_COLORS)]
                staged_map[ws_item.name] = (label, color)

        self._ws_list.clear()
        for item in self.workspace.list_items():
            top = QtWidgets.QTreeWidgetItem(self._ws_list)

            # Badge prefix in name column
            badge_info = staged_map.get(item.name)
            if badge_info:
                label, color = badge_info
                top.setText(0, f"[{label}]  {item.display_name}")
                top.setForeground(0, QtGui.QBrush(QtGui.QColor(color)))
                font = top.font(0)
                font.setBold(True)
                top.setFont(0, font)
            else:
                top.setText(0, item.display_name)

            top.setData(0, _UserRole, item.name)

            # Shape / type info
            shape = getattr(getattr(item.payload, 'data', None), 'shape', None)
            info_text = f"[{item.type_id}]"
            if shape:
                info_text += f"  {shape}"
            top.setText(1, info_text)

            # Annotation children
            for role, ann in item.annotations.items():
                child = QtWidgets.QTreeWidgetItem(top)
                child.setText(0, role)
                child.setText(1, self._ann_summary(ann))
                child.setData(0, _UserRole, (item.name, role))
            top.setExpanded(True)

    def _selected_item_name(self) -> str | None:
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        tree_item = self._ws_list.currentItem()
        if tree_item is None:
            return None
        data = tree_item.data(0, _UserRole)
        # Top-level items store str; child items store (name, role) tuple
        if isinstance(data, tuple):
            return data[0]
        return data

    def _on_ws_item_double_clicked(self, tree_item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        data = tree_item.data(0, _UserRole)
        # Only activate on top-level items (str name), not annotation children
        if not isinstance(data, str):
            return
        name = data
        item = self.workspace.get_item(name)
        try:
            self.load_item(item)
        except TypeError as exc:
            QtWidgets.QMessageBox.warning(self, "Type mismatch", str(exc))

    def _on_ws_context_menu(self, pos) -> None:
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        tree_item = self._ws_list.itemAt(pos)
        if tree_item is None:
            return
        data = tree_item.data(0, _UserRole)
        if isinstance(data, tuple):
            # Annotation child — show Clear action
            item_name, role = data
            menu = QtWidgets.QMenu(self)
            act_clear = menu.addAction(f"Clear '{role}'")
            act = menu.exec(self._ws_list.viewport().mapToGlobal(pos))
            if act == act_clear:
                ws_item = self.workspace.get_item(item_name)
                ws_item.annotations.pop(role, None)
                self.workspace.notify_changed(item_name)
        elif isinstance(data, str):
            ws_item = self.workspace.get_item(data)
            if ws_item is None:
                return
            menu = QtWidgets.QMenu(self)
            self._populate_ws_item_context_menu(menu, ws_item)
            if not menu.isEmpty():
                menu.exec(self._ws_list.viewport().mapToGlobal(pos))

    def _populate_ws_item_context_menu(
            self, menu: "QtWidgets.QMenu", item: "WorkspaceItem") -> None:
        """Hook for subclasses to add actions to the workspace item context menu."""

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

    def build_preferences_widget(self, parent: QtWidgets.QWidget,
                                    on_apply, on_save_as_default
                                    ) -> QtWidgets.QWidget | None:
        """
        Return a custom preferences widget, or None to fall through to the
        schema-based panel (when preferences_schema is defined) or the generic
        tree editor.  Override only when neither option suits the module.
        """
        return None

    def _on_preferences(self) -> None:
        import copy
        from angstrompro.gui.widgets.config_editor_widget import ConfigEditorWidget
        from angstrompro.core.configs.defaults import DEFAULTS
        from angstrompro.utils.qt_compat import QtWidgets

        from angstrompro.app.user_data_folder import get_qsettings
        _qs_key = f"prefs_size/{self.module_id}"

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dlg.setWindowTitle(f"Preferences — {self.display_name}")
        qs = get_qsettings()
        dlg.resize(qs.value(_qs_key, QtCore.QSize(900, 600)))
        dlg.finished.connect(lambda: get_qsettings().setValue(_qs_key, dlg.size()))
        layout = QtWidgets.QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)

        def _apply(cfg: dict) -> None:
            self._config = copy.deepcopy(cfg)

        def _save_as_default(cfg: dict) -> None:
            self._config = copy.deepcopy(cfg)
            if self._plugin_ns:
                pc = self._context.get_plugin_config(self._plugin_ns)
                pc.set_module(self.module_id, cfg)
                pc.save()
            else:
                self._context.config.set_module_config(self.module_id, cfg)
                self._context.config.save_defaults()

        def _reset() -> None:
            from angstrompro.core.configs.defaults import DEFAULTS
            defaults = DEFAULTS.get("modules", {}).get(self.module_id, {})
            _apply(copy.deepcopy(defaults))

        # 1. Subclass custom widget (full override)
        widget = self.build_preferences_widget(dlg, _apply, _save_as_default)

        if widget is None:
            schema = getattr(self, "preferences_schema", None)
            if schema:
                # 2. Declarative schema → PreferencesPanel
                from angstrompro.gui.widgets.preferences import PreferencesPanel
                widget = PreferencesPanel(
                    module_name=self.display_name,
                    schema=schema,
                    config=copy.deepcopy(self._config),
                    on_apply=_apply,
                    on_save_as_default=_save_as_default,
                    on_reset=_reset,
                    parent=dlg,
                )
                # Let the module react to config changes (e.g. repaint panels)
                if hasattr(self, "_apply_config_to_panels"):
                    orig_apply = _apply
                    def _apply(cfg: dict, _orig=orig_apply) -> None:  # noqa: E731
                        _orig(cfg)
                        self._apply_config_to_panels(cfg)
                    widget._on_apply_cb  = _apply
                    orig_save = _save_as_default
                    def _save_as_default(cfg: dict, _orig=orig_save) -> None:  # noqa: E731
                        _orig(cfg)
                        self._apply_config_to_panels(cfg)
                    widget._on_save_cb = _save_as_default
            elif self._config:
                # 3. Instance config but no schema → generic tree editor (instance mode)
                module_defaults = DEFAULTS.get("modules", {}).get(self.module_id, {})
                widget = ConfigEditorWidget(
                    self._context, dlg,
                    instance_config=copy.deepcopy(self._config),
                    instance_defaults=module_defaults,
                    on_apply=_apply,
                    on_save_as_default=_save_as_default,
                )
            else:
                # 4. Global config tree (MainWorkbench with config_sections=None)
                widget = ConfigEditorWidget(self._context, dlg,
                                            sections=self.config_sections)

        layout.addWidget(widget)
        dlg.show()

    def _on_file_open(self) -> None:
        from angstrompro.io.angstrom_io import registered_formats
        formats = registered_formats()
        format_filters = ";;".join(
            f"{f.display_name} (*{f.extension})" for f in formats if f.readable
        )
        filters = "All Files (*);;" + format_filters
        start_dir = self._context.config.get("io", "default_open_dir") or ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", start_dir, filters)
        if not path:
            return
        from pathlib import Path
        from angstrompro.io import load
        p = Path(path)
        try:
            from angstrompro.gui.utils.file_loading import load_with_channel_picker
            result = load_with_channel_picker(p, self._context, self)
            if result is None:
                return  # user cancelled
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Open failed", str(exc))
            return
        payloads = result if isinstance(result, list) else [result]
        for payload in payloads:
            name = self.workspace.suggest_name(
                getattr(payload, "name", None) or p.stem
            )
            self.workspace.add_item(name=name, payload=payload)

    def _load_with_channel_picker(self, p):
        """Deprecated: use angstrompro.gui.utils.file_loading.load_with_channel_picker."""
        from angstrompro.gui.utils.file_loading import load_with_channel_picker
        return load_with_channel_picker(p, self._context, self)

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
        wm.item_changed.connect(_guard)

        self._ws_list.currentItemChanged.connect(self._on_ws_selection_changed)  # type: ignore[attr-defined]

        self._context.signals.status_message.connect(self.statusBar().showMessage)
        self._context.signals.processes_updated.connect(self._rebuild_process_submenu)

    def _on_ws_selection_changed(self, current, _previous) -> None:
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        if current is None:
            self._inspector.set_item(None)
            return
        data = current.data(0, _UserRole)
        # Resolve name from both top-level (str) and child (tuple) items
        name = data[0] if isinstance(data, tuple) else data
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

        Accepts either a single WorkspaceData or a list of WorkspaceData objects
        (e.g. from submit_pipeline with return_all=True, or a process that
        naturally produces multiple outputs).

        Subclasses that need custom behaviour (e.g. display the result immediately)
        should pass on_result= to submit_process() instead of overriding this.
        """
        from angstrompro.core.data.base import WorkspaceData
        items = result if isinstance(result, list) else [result]
        for item in items:
            if not isinstance(item, WorkspaceData):
                log.warning(
                    "Process returned %s which is not WorkspaceData — not added to workspace",
                    type(item).__name__,
                )
                continue
            raw_name = getattr(item, "name", None) or "result"
            name     = self.workspace.suggest_name(raw_name)
            self.workspace.add_item(name=name, payload=item)

    def _on_process_error(self, task_id: str, error_text: str) -> None:
        log.error("Process error [%s]: %s", task_id, error_text)

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
