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

from angstrompro.utils.qt_compat import Action, QtCore, QtWidgets, IS_QT6
from angstrompro.gui.appearance.typography import (
    BODY, HINT, SECTION, set_typography_role)

log = logging.getLogger(__name__)
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.core.tasks.task_handle import TaskHandle
from .module_mixin import ModuleMixin

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext

_DockArea = (QtCore.Qt.DockWidgetArea.LeftDockWidgetArea if IS_QT6
             else QtCore.Qt.LeftDockWidgetArea)


def _set_menu_role(action, role_name: str) -> None:
    """Set a QAction menu role across scoped (Qt6) and unscoped (Qt5) enums."""
    action_type = type(action)
    menu_role = getattr(action_type, "MenuRole", None)
    role = (
        getattr(menu_role, role_name)
        if menu_role is not None
        else getattr(action_type, role_name)
    )
    action.setMenuRole(role)


class AGuiModule(ModuleMixin, QtWidgets.QMainWindow):
    """Base class for every AngstromPro GUI module window."""

    # Subclasses override these to declare what data they work with
    accepted_ndim: int | None = None   # None = any; 2 = 2D only; 3 = 3D only

    # Legacy declaration retained for source compatibility. Process submenus
    # now come only from the user's algorithms.process_menu_layouts entry.
    default_process_menu: list[str] = []

    # Simulation names shown in the Simulate menu (kind="simulation" entries only).
    default_simulate_menu: list[str] = []

    # Config sections shown in Edit → Preferences for this module.
    # None = show all (intended for MainWorkbench only).
    config_sections: list[str] | None = ["algorithms"]

    # Short badge labels shown next to staged items in the workspace panel.
    # Index matches process_inputs order.  e.g. ["M", "A"] for ImageStackViewer.
    staged_labels: list[str] = []
    # Indices of slots that show a ✕ clear button in the Active Slots panel.
    # Slot 0 (Input) is never clearable regardless. Default: all non-zero slots.
    clearable_slots: set[int] | None = None  # None → {1, 2, ...} (all non-zero)
    persist_window_layout: bool = True

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
        _ExtendedSelection = (
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
            if IS_QT6 else
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        _SelectRows = (
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
            if IS_QT6 else
            QtWidgets.QAbstractItemView.SelectRows
        )
        self._ws_list.setSelectionMode(_ExtendedSelection)
        self._ws_list.setSelectionBehavior(_SelectRows)
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
        self._btn_remove = QtWidgets.QPushButton("Remove")
        self._btn_send   = QtWidgets.QPushButton("Send…")
        self._send_default_cb = QtWidgets.QCheckBox("Default")
        self._btn_remove.clicked.connect(self._on_remove_item)
        self._btn_send.clicked.connect(self._on_send_item)
        self._send_default_cb.toggled.connect(self._on_default_toggled)
        btn_row.addWidget(self._btn_remove)
        btn_row.addWidget(self._btn_send)
        btn_row.addWidget(self._send_default_cb)
        vbox.addLayout(btn_row)
        self._update_workspace_selection_actions()

        # active slots panel — shown below action buttons whenever staged_labels is defined
        if self.staged_labels:
            vbox.addWidget(self._build_active_slots_panel())

        dock.setWidget(container)
        self.addDockWidget(_DockArea, dock)
        self._workspace_dock = dock
        self._workspace_destination_buttons = {}
        self._workspace_destination_group = None
        self._workspace_expansion = {}
        # module types listed in app.hide_workspace_dock start hidden;
        # the View menu toggle (Ctrl+1) re-opens the dock any time
        if self.module_id in (self._context.config.get(
                "app", "hide_workspace_dock", []) or []):
            dock.hide()

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
        act_config = Action("Configure Process Menu…", self)
        # macOS text heuristics may classify "Configure" as the application's
        # Preferences command. Keep this action in the Process menu.
        _set_menu_role(act_config, "NoRole")
        act_config.triggered.connect(self._on_configure_process_menu)
        self._process_menu.addAction(act_config)
        self._process_menu.addSeparator()
        self._rebuild_process_submenu()

    def _rebuild_process_submenu(self) -> None:
        """Rebuild user-named submenus from the explicit saved layout."""
        # Remove everything after the fixed header (Browser + Configure + separator = 3 items)
        for act in self._process_menu.actions()[3:]:
            self._process_menu.removeAction(act)

        registry = self._context.processes
        strict   = self._context.config.get("app", "strict_process_menu", True)

        from angstrompro.core.processes.menu_layout import (
            normalize_process_menu_layout,
        )
        layouts = self._context.config.get(
            "algorithms", "process_menu_layouts", {})
        raw_layout = layouts.get(self.module_id, {}) if isinstance(layouts, dict) else {}
        layout = normalize_process_menu_layout(raw_layout)

        for group in layout["groups"]:
            entries = []
            for name in group["processes"]:
                if not registry.has(name):
                    log.warning(
                        "Process menu [%s]: %r is not registered — skipped",
                        self.module_id, name,
                    )
                    continue
                entry = registry.get(name)
                if entry.kind != "process":
                    log.warning(
                        "Process menu [%s]: %r has kind=%r — skipped",
                        self.module_id, name, entry.kind,
                    )
                    continue
                ok, reason = self._check_process_compatibility(entry)
                if not ok:
                    log.warning(
                        "Process menu [%s]: %r is incompatible (%s)%s",
                        self.module_id, name, reason,
                        "" if strict else
                        " — added anyway (strict_process_menu=false)",
                    )
                    if strict:
                        continue
                entries.append(entry)

            if not entries:
                continue
            submenu = self._process_menu.addMenu(
                group["title"].replace("&", "&&"))
            for entry in entries:
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
                submenu = self._simulate_menu.addMenu(
                    category.replace("&", "&&"))
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
        from angstrompro.core.processes import select_compatible_input_items
        entry = self._context.processes.get(process_name)

        ws_items = self.accessible_workspace_items()
        pre_staged = select_compatible_input_items(
            entry.schema.inputs,
            self.process_inputs,
            ws_items,
        )
        # Validate the domain-aware selection before opening the dialog.
        ok, msg = self._validate_process_inputs(entry, pre_staged)
        if not ok:
            QtWidgets.QMessageBox.warning(self, "Input data not ready", msg)
            return

        dlg = ProcessParamDialog(
            entry, self._context, parent=self,
            input_items=pre_staged, workspace_items=ws_items,
        )
        if dlg.exec():
            params      = dlg.params()
            self.submit_process(process_name, dlg.input_items(), params)

    def _validate_process_inputs(
            self, entry, input_items=None) -> tuple[bool, str]:
        """
        Check that process_inputs satisfies entry.schema.inputs.

        Rules:
          - len(process_inputs) >= number of required inputs (spec.required=True)
          - For each (spec, item) pair that is staged: type_id and ndim must match
        """
        specs = entry.schema.inputs
        if not specs:
            return True, ""   # 0-input process — always valid

        staged = list(self.process_inputs if input_items is None else input_items)

        for i, spec in enumerate(specs):
            item = staged[i] if i < len(staged) else None
            if item is None:
                if not spec.required:
                    continue
                domain = (
                    ""
                    if spec.data_domain == "any"
                    else f" {spec.data_domain.replace('_', '-')}"
                )
                return (
                    False,
                    f"Input slot {i+1} ('{spec.name}') needs a compatible"
                    f"{domain} item. Load or select the required data first.",
                )
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
            if not spec.accepts(item.payload):
                required = spec.data_domain.replace("_", "-")
                return (
                    False,
                    f"Input slot {i+1} ('{spec.name}') requires {required} "
                    f"data, but staged item '{item.name}' is not compatible.",
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

    def _build_active_slots_panel(self) -> QtWidgets.QWidget:
        """Build the Active Slots panel from staged_labels. Called by base class."""
        panel = QtWidgets.QWidget()
        panel.setObjectName("active_slots_panel")
        panel.setStyleSheet(
            "QWidget#active_slots_panel { border-top: 1px solid palette(mid); }")
        vl = QtWidgets.QVBoxLayout(panel)
        vl.setContentsMargins(4, 6, 4, 2)
        vl.setSpacing(2)

        title = QtWidgets.QLabel("Active Processing Slots")
        set_typography_role(title, SECTION)
        vl.addWidget(title)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setSpacing(3)
        grid.setColumnStretch(1, 1)

        self._slot_labels: list[QtWidgets.QLabel] = []
        self._slot_clear_btns: list[QtWidgets.QPushButton | None] = []

        for idx, label in enumerate(self.staged_labels):
            row_lbl = QtWidgets.QLabel(f"[{label}]")
            val_lbl = QtWidgets.QLabel("—")
            set_typography_role(val_lbl, HINT)
            val_lbl.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Ignored,
                QtWidgets.QSizePolicy.Policy.Preferred)
            grid.addWidget(row_lbl, idx, 0)
            grid.addWidget(val_lbl, idx, 1)
            self._slot_labels.append(val_lbl)

            clearable = (self.clearable_slots is None and idx > 0) or (
                self.clearable_slots is not None and idx in self.clearable_slots)
            if not clearable:
                self._slot_clear_btns.append(None)
            else:
                btn = QtWidgets.QPushButton("✕")
                btn.setFixedWidth(22)
                btn.setToolTip(f"Clear {label} slot")
                btn.setEnabled(False)
                btn.clicked.connect(lambda _checked, i=idx: self._clear_slot(i))
                grid.addWidget(btn, idx, 2)
                self._slot_clear_btns.append(btn)

        vl.addLayout(grid)
        return panel

    def _refresh_slots_panel(self) -> None:
        """Update Active Slots panel labels from current process_inputs."""
        if not hasattr(self, "_slot_labels"):
            return
        for idx, val_lbl in enumerate(self._slot_labels):
            item = (self._process_inputs[idx]
                    if idx < len(self._process_inputs) else None)
            btn = self._slot_clear_btns[idx]
            if item is not None:
                val_lbl.setText(item.name)
                set_typography_role(val_lbl, BODY)
                if btn is not None:
                    btn.setEnabled(True)
            else:
                val_lbl.setText("—")
                set_typography_role(val_lbl, HINT)
                if btn is not None:
                    btn.setEnabled(False)

    def _clear_slot(self, idx: int) -> None:
        """Called when the user clicks ✕ on a slot. Override in subclasses."""

    def _get_display_color(self, item_name: str) -> str | None:
        """Return hex color if item is currently shown in the display, else None.
        Override in subclasses: blue (#2196F3) for input panel,
        orange (#FF9800) for reference panel, None if not displayed."""
        return None

    def _refresh_workspace_panel(self) -> None:
        from angstrompro.utils.qt_compat import QtGui
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole

        # Workspace rows are rebuilt after every mutation.  Preserve both the
        # multi-selection and its single focused/current row by stable IDs.
        selected_data = {
            tree_item.data(0, _UserRole)
            for tree_item in self._ws_list.selectedItems()
            if tree_item.data(0, _UserRole) is not None
        }
        current_tree_item = self._ws_list.currentItem()
        current_data = (
            current_tree_item.data(0, _UserRole)
            if current_tree_item is not None else None
        )

        # Workspace rows are rebuilt after every mutation. Remember their
        # disclosure state so a collapsed workspace stays collapsed.
        for index in range(self._ws_list.topLevelItemCount()):
            row = self._ws_list.topLevelItem(index)
            data = row.data(0, _UserRole)
            if isinstance(data, tuple) and len(data) == 2 and data[0] == "workspace":
                self._workspace_expansion[data[1]] = row.isExpanded()

        # Build a map keyed by stable item id so duplicate names in the private
        # and shared workspaces remain unambiguous.
        staged_map: dict[str, str] = {}
        for idx, ws_item in enumerate(self._process_inputs):
            if ws_item is None:
                continue
            if idx < len(self.staged_labels):
                staged_map[ws_item.item_id] = self.staged_labels[idx]

        if self._workspace_destination_group is not None:
            self._workspace_destination_group.deleteLater()
        self._workspace_destination_group = QtWidgets.QButtonGroup(self._ws_list)
        self._workspace_destination_group.setExclusive(True)
        self._workspace_destination_buttons = {}
        self._ws_list.clear()
        workspaces = [(self.private_workspace, "Private workspace")]
        if self.shared_workspace is not None:
            workspaces.append((
                self.shared_workspace,
                f"Shared: {self.shared_workspace.label}",
            ))
        multiple = len(workspaces) > 1
        indicator = (
            QtWidgets.QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
            if IS_QT6 else QtWidgets.QTreeWidgetItem.ShowIndicator
        )
        for workspace, title in workspaces:
            group = QtWidgets.QTreeWidgetItem(self._ws_list)
            group.setChildIndicatorPolicy(indicator)
            accessible_role = (
                QtCore.Qt.ItemDataRole.AccessibleTextRole
                if IS_QT6 else QtCore.Qt.AccessibleTextRole
            )
            group.setData(0, accessible_role, title)
            group.setToolTip(0, title)
            group.setText(1, f"{workspace.count()} item(s)")
            group.setData(
                0, _UserRole, ("workspace", workspace.workspace_id),
            )
            font = group.font(0)
            font.setBold(True)
            group.setFont(0, font)
            if multiple:
                # The embedded radio button is the sole painter of the title.
                # Qt stylesheets can disable its auto-filled background, so
                # model display text here would show through and overlap it.
                selector = QtWidgets.QRadioButton(title)
                selector.setAutoFillBackground(True)
                selector.setObjectName(
                    f"workspace_destination_{workspace.workspace_id}"
                )
                selector.setFont(font)
                selector.setToolTip(
                    "Active destination for incoming items, opened data and new "
                    "process outputs. Both workspaces remain accessible. Running "
                    "processes keep their destination."
                )
                selector.setAccessibleName(f"Active destination: {title}")
                self._workspace_destination_group.addButton(selector)
                selector.setChecked(workspace is self.active_workspace)
                selector.toggled.connect(
                    lambda checked, wid=workspace.workspace_id:
                    self.set_active_workspace(wid) if checked else None
                )
                self._workspace_destination_buttons[workspace.workspace_id] = selector
                self._ws_list.setItemWidget(group, 0, selector)
            else:
                group.setText(0, title)
            self._populate_workspace_tree_items(
                group, workspace, staged_map, _UserRole,
            )
            group.setExpanded(
                self._workspace_expansion.get(workspace.workspace_id, True)
            )

        selected_matches = []
        current_match = None
        pending = [
            self._ws_list.topLevelItem(index)
            for index in range(self._ws_list.topLevelItemCount())
        ]
        while pending:
            row = pending.pop(0)
            data = row.data(0, _UserRole)
            if data in selected_data:
                selected_matches.append(row)
            if data == current_data:
                current_match = row
            pending[0:0] = [row.child(i) for i in range(row.childCount())]

        blocked = self._ws_list.blockSignals(True)
        self._ws_list.clearSelection()
        for row in selected_matches:
            row.setSelected(True)
        if current_match is None and selected_matches:
            current_match = selected_matches[-1]
        if current_match is not None:
            _NoUpdate = (
                QtCore.QItemSelectionModel.SelectionFlag.NoUpdate
                if IS_QT6 else QtCore.QItemSelectionModel.NoUpdate
            )
            self._ws_list.selectionModel().setCurrentIndex(
                self._ws_list.indexFromItem(current_match), _NoUpdate)
        self._ws_list.blockSignals(blocked)

        self._refresh_slots_panel()
        self._on_ws_selection_changed(current_match, None)
        self._update_workspace_selection_actions()

    def on_active_workspace_changed(self) -> None:
        """Update destination indicators without rebuilding or deselecting items."""
        for workspace_id, button in self._workspace_destination_buttons.items():
            blocked = button.blockSignals(True)
            button.setChecked(workspace_id == self.active_workspace.workspace_id)
            button.blockSignals(blocked)
        kind = "Shared" if self.active_workspace.is_shared else "Private"
        self.statusBar().showMessage(
            f"Active destination: {kind} — {self.active_workspace.label}", 5000)

    def _populate_workspace_tree_items(
            self, parent, workspace, staged_map: dict[str, str],
            user_role) -> None:
        from angstrompro.utils.qt_compat import QtGui

        for item in workspace.list_items():
            top = QtWidgets.QTreeWidgetItem(parent)

            badge = staged_map.get(item.item_id)
            display_color = self._get_display_color(item.name)

            # Name text: badge prefix when in a processing slot
            top.setText(0, f"[{badge}]  {item.display_name}" if badge else item.display_name)

            # Color = display state (always applied when displayed)
            # Badge = processing slot (bold only, no separate color)
            if display_color:
                top.setForeground(0, QtGui.QBrush(QtGui.QColor(display_color)))
            if badge:
                font = top.font(0)
                font.setBold(True)
                top.setFont(0, font)
            if item.alias:
                top.setToolTip(
                    0,
                    f"Workspace name: {item.name}\nAlias: {item.alias}",
                )

            top.setData(
                0, user_role,
                ("item", workspace.workspace_id, item.item_id),
            )

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
                child.setData(
                    0, user_role,
                    ("annotation", workspace.workspace_id, item.item_id, role),
                )
            top.setExpanded(True)

    def _workspace_tree_context(self, data):
        """Resolve tree data to ``(kind, workspace, item, role)``."""
        manager = self._context.workspace_manager
        if isinstance(data, tuple) and data:
            kind = data[0]
            if kind == "workspace" and len(data) == 2:
                try:
                    return kind, manager.get_workspace(data[1]), None, None
                except KeyError:
                    return None, None, None, None
            if kind in {"item", "annotation"} and len(data) >= 3:
                try:
                    workspace = manager.get_workspace(data[1])
                except KeyError:
                    return None, None, None, None
                item = workspace.find_item_by_id(data[2])
                role = data[3] if kind == "annotation" and len(data) > 3 else None
                return kind, workspace, item, role
        # Compatibility for tree data produced by older subclasses.
        if isinstance(data, str):
            item = self.workspace.find_item(data)
            return "item", self.workspace, item, None
        if isinstance(data, tuple) and len(data) == 2:
            item = self.workspace.find_item(data[0])
            return "annotation", self.workspace, item, data[1]
        return None, None, None, None

    def _selected_workspace_item(self) -> WorkspaceItem | None:
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        tree_item = self._ws_list.currentItem()
        if tree_item is None:
            return None
        kind, _workspace, item, _role = self._workspace_tree_context(
            tree_item.data(0, _UserRole))
        return item if kind in {"item", "annotation"} else None

    def _selected_workspace_entries(self) -> list[tuple[Any, WorkspaceItem]]:
        """Return selected real item rows as ``(workspace, item)`` pairs.

        Workspace headings and annotation child rows are deliberately not
        bulk-action targets.  Stable item IDs prevent duplicate entries.
        """
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        entries: list[tuple[Any, WorkspaceItem]] = []
        seen: set[tuple[str, str]] = set()
        for tree_item in self._ws_list.selectedItems():
            kind, workspace, item, _role = self._workspace_tree_context(
                tree_item.data(0, _UserRole))
            if kind != "item" or workspace is None or item is None:
                continue
            key = (workspace.workspace_id, item.item_id)
            if key in seen:
                continue
            seen.add(key)
            entries.append((workspace, item))
        return entries

    def _bulk_entries_or_legacy_current(self) -> list[tuple[Any, WorkspaceItem]]:
        """Selected item rows, with a compatibility fallback for old callers."""
        entries = self._selected_workspace_entries()
        if entries or self._ws_list.currentItem() is not None:
            return entries
        # Some lightweight callers and subclasses provide only the older
        # current-item helpers and no real tree selection.
        item = self._selected_workspace_item()
        workspace = self._selected_item_workspace()
        return [(workspace, item)] if item is not None and workspace is not None else []

    def _update_workspace_selection_actions(self) -> None:
        if not hasattr(self, "_btn_remove"):
            return
        count = len(self._selected_workspace_entries())
        enabled = count > 0
        self._btn_remove.setEnabled(enabled)
        self._btn_send.setEnabled(enabled)
        self._btn_remove.setText(f"Remove ({count})" if count > 1 else "Remove")
        self._btn_send.setText(f"Send ({count})…" if count > 1 else "Send…")
        hint = (f"Apply to {count} selected workspace item(s)"
                if count else "Select one or more workspace items")
        self._btn_remove.setToolTip(hint)
        self._btn_send.setToolTip(hint)

    def _selected_item_workspace(self):
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        tree_item = self._ws_list.currentItem()
        if tree_item is None:
            return None
        kind, workspace, _item, _role = self._workspace_tree_context(
            tree_item.data(0, _UserRole))
        return workspace if kind in {"item", "annotation"} else None

    def _selected_item_name(self) -> str | None:
        item = self._selected_workspace_item()
        return item.name if item is not None else None

    def _on_ws_item_double_clicked(self, tree_item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        _LeftButton = QtCore.Qt.MouseButton.LeftButton if IS_QT6 else QtCore.Qt.LeftButton
        if not (QtWidgets.QApplication.mouseButtons() & _LeftButton):
            return
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        data = tree_item.data(0, _UserRole)
        kind, _workspace, item, _role = self._workspace_tree_context(data)
        if kind != "item" or item is None:
            return
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
        kind, workspace, ws_item, role = self._workspace_tree_context(data)
        if kind == "annotation" and workspace is not None and ws_item is not None:
            # Annotation child — show Clear action
            menu = QtWidgets.QMenu(self)
            act_clear = menu.addAction(f"Clear '{role}'")
            act = menu.exec(self._ws_list.viewport().mapToGlobal(pos))
            if act == act_clear:
                ws_item.annotations.pop(role, None)
                workspace.notify_changed(ws_item.name)
        elif kind == "item" and workspace is not None and ws_item is not None:
            menu = QtWidgets.QMenu(self)
            self._populate_ws_item_context_menu(menu, ws_item)
            if not menu.isEmpty():
                menu.addSeparator()
            act_set_alias = menu.addAction("Set alias…")
            act_set_alias.triggered.connect(
                lambda _checked=False, w=workspace:
                self._set_workspace_item_alias(ws_item, w))
            if ws_item.alias:
                act_clear_alias = menu.addAction("Clear alias")
                act_clear_alias.triggered.connect(
                    lambda _checked=False, w=workspace:
                    self._clear_workspace_item_alias(ws_item, w))
            menu.exec(self._ws_list.viewport().mapToGlobal(pos))

    def _populate_ws_item_context_menu(
            self, menu: "QtWidgets.QMenu", item: "WorkspaceItem") -> None:
        """Hook for subclasses to add actions to the workspace item context menu."""

    def _set_workspace_item_alias(
            self, item: "WorkspaceItem", workspace=None) -> None:
        """Prompt for a display-only alias without changing item identity."""

        echo_mode_type = getattr(
            QtWidgets.QLineEdit, "EchoMode", QtWidgets.QLineEdit)
        alias, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Set workspace item alias",
            f"Display alias for '{item.name}':\n"
            "Leave blank to clear the alias.",
            echo_mode_type.Normal,
            item.alias,
        )
        if not accepted:
            return
        alias = alias.strip()
        if alias == item.name:
            alias = ""
        if alias == item.alias:
            return
        item.alias = alias
        owner_lookup = getattr(self, "workspace_containing_item", None)
        owner = owner_lookup(item) if callable(owner_lookup) else None
        (workspace or owner or self.workspace).notify_changed(item.name)

    def _clear_workspace_item_alias(
            self, item: "WorkspaceItem", workspace=None) -> None:
        """Remove an item's display alias while preserving its real name."""

        if not item.alias:
            return
        item.alias = ""
        owner_lookup = getattr(self, "workspace_containing_item", None)
        owner = owner_lookup(item) if callable(owner_lookup) else None
        (workspace or owner or self.workspace).notify_changed(item.name)


    def _on_remove_item(self) -> None:
        entries = self._bulk_entries_or_legacy_current()
        if not entries:
            return
        if len(entries) > 1:
            answer = QtWidgets.QMessageBox.question(
                self,
                "Remove workspace items?",
                f"Remove {len(entries)} selected workspace items?",
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        removed = 0
        for workspace, item in entries:
            if workspace.has_item_id(item.item_id):
                workspace.remove_item(item.name)
                removed += 1
        if removed:
            self.statusBar().showMessage(
                f"Removed {removed} workspace item(s).", 4000)

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
        entries = self._bulk_entries_or_legacy_current()
        if not entries:
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
        else:
            from angstrompro.gui.dialogs.send_item_dialog import SendItemDialog
            dlg = SendItemDialog(self._context, exclude_instance_id=self.instance_id, parent=self)
            if dlg.exec() and dlg.selected_module:
                targets = [dlg.selected_module]
            else:
                return

        # Multiple target modules may share one destination workspace.  Copy
        # into that workspace once, not once per attached module.
        destinations = []
        seen_destinations = set()
        for target in targets:
            destination = target.active_workspace
            if destination.workspace_id in seen_destinations:
                continue
            seen_destinations.add(destination.workspace_id)
            destinations.append(destination)

        transfer_count = 0
        sent_items = 0
        skipped_count = 0
        deletable: list[tuple[Any, WorkspaceItem]] = []
        failures: list[str] = []
        for source_workspace, item in entries:
            succeeded = 0
            failed = False
            for destination in destinations:
                if destination.workspace_id == source_workspace.workspace_id:
                    skipped_count += 1
                    continue
                try:
                    self._context.workspace_manager.transfer_item(
                        src_workspace_id=source_workspace.workspace_id,
                        dst_workspace_id=destination.workspace_id,
                        item_name=item.name,
                    )
                except Exception as exc:
                    failed = True
                    failures.append(f"{item.display_name}: {exc}")
                else:
                    succeeded += 1
                    transfer_count += 1
            if succeeded:
                sent_items += 1
                if not failed:
                    deletable.append((source_workspace, item))

        # Complete all copies before applying the app's move-like preference;
        # otherwise the first destination could remove a source needed by the
        # remaining destinations.
        for source_workspace, item in deletable:
            self._after_send(item.name, source_workspace)

        if failures:
            details = "\n".join(failures[:8])
            if len(failures) > 8:
                details += f"\n…and {len(failures) - 8} more."
            QtWidgets.QMessageBox.warning(
                self, "Some items were not sent", details)
        if transfer_count:
            message = f"Sent {sent_items} item(s) in {transfer_count} transfer(s)."
            if skipped_count:
                message += f" Skipped {skipped_count} already-shared destination(s)."
            self.statusBar().showMessage(message, 5000)
        elif skipped_count and not failures:
            self.statusBar().showMessage(
                "The selected item(s) already belong to the target workspace.",
                4000,
            )

    def _after_send(self, item_name: str, source_workspace=None) -> None:
        """App-level send semantics: transfer_item copies, so with
        delete_after_send=True (default) the sender's copy is removed —
        a send reads as *move*.  Safe because the receiver deep-copies /
        takes ownership at the accept boundary."""
        source_workspace = source_workspace or self.workspace
        if self._context.config.get("app", "delete_after_send", True):
            if source_workspace.has_item(item_name):
                source_workspace.remove_item(item_name)

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

        act_open_workspace = menu.addAction("Open Workspace…")
        act_open_workspace.triggered.connect(self._on_workspace_open)

        act_save_workspace = menu.addAction("Save Workspace…")
        act_save_workspace.triggered.connect(self._on_workspace_save)

        menu.addSeparator()

        act_prefs = Action("Preferences…", self)
        act_prefs.setShortcut("Ctrl+,")
        # Mark the one true Preferences action explicitly. On macOS Qt moves
        # this action into the application menu.
        _set_menu_role(act_prefs, "PreferencesRole")
        act_prefs.triggered.connect(self._on_preferences)
        menu.addAction(act_prefs)

        menu.addSeparator()

        act_close = menu.addAction("Close Window")
        act_close.setShortcut("Ctrl+W")
        # Route through closeEvent rather than bypassing it with hide().
        # Child modules still hide through AGuiModule.closeEvent, while the
        # Main Workbench can run its confirmation and orderly app-exit path.
        act_close.triggered.connect(self.close)

    # ------------------------------------------------------------------
    # Edit menu
    # ------------------------------------------------------------------

    def _build_edit_menu(self) -> None:
        pass  # subclasses may populate Edit with content-level actions

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

        def _reset() -> dict:
            from angstrompro.core.configs.defaults import DEFAULTS
            defaults = DEFAULTS.get("modules", {}).get(self.module_id, {})
            _apply(copy.deepcopy(defaults))
            return defaults

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
                    context=self._context,
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
        destination = self.active_workspace
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
        from angstrompro.io import load_item
        from angstrompro.io.angstrom_io import _is_hdf5
        p = Path(path)
        try:
            from angstrompro.gui.utils.file_loading import load_with_channel_picker
            result = (load_item(p) if _is_hdf5(p) else
                      load_with_channel_picker(p, self._context, self))
            if result is None:
                return  # user cancelled
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Open failed", str(exc))
            return
        payloads = result if isinstance(result, list) else [result]
        for loaded in payloads:
            saved_item = loaded if isinstance(loaded, WorkspaceItem) else None
            payload = saved_item.payload if saved_item else loaded
            if not payload.name:
                payload.name = p.stem
            if saved_item:
                destination.add_item(
                    payload=payload, alias=saved_item.alias,
                    annotations=saved_item.annotations,
                    metadata=saved_item.metadata,
                    item_id=saved_item.item_id,
                )
            else:
                destination.add_item(payload=payload)

    def _load_with_channel_picker(self, p):
        """Deprecated: use angstrompro.gui.utils.file_loading.load_with_channel_picker."""
        from angstrompro.gui.utils.file_loading import load_with_channel_picker
        return load_with_channel_picker(p, self._context, self)

    def _on_file_save(self) -> None:
        selected_item = getattr(self, "_selected_workspace_item", None)
        item = selected_item() if callable(selected_item) else None
        if item is None:
            # Compatibility for lightweight callers and older subclasses that
            # only provide the name-based selection helper.
            name = self._selected_item_name()
            item = self.workspace.find_item(name) if name else None
        if item is None:
            QtWidgets.QMessageBox.warning(self, "No item selected",
                                          "Select a workspace item to save.")
            return
        name = item.name
        if not self._confirm_standalone_uds_save(item):
            return
        from angstrompro.io import uds_io, scene_plot_io  # noqa: F401 — ensure all formats registered
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
        suggested_name = item.alias or name
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Item", suggested_name + default_ext, filters
        )
        if not path:
            return
        from pathlib import Path
        from angstrompro.io import save_item
        try:
            save_item(Path(path), item)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

    def _confirm_standalone_uds_save(self, item: WorkspaceItem) -> bool:
        """Recommend a workspace archive for UDS data with multiple sources."""
        from angstrompro.core.data.uds_data import (
            UdsDataStru,
            uds_has_multiple_sources,
        )

        payload = item.payload
        if not isinstance(payload, UdsDataStru):
            return True
        if not uds_has_multiple_sources(payload):
            return True

        source_count = len(payload.info["source"])
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        box.setWindowTitle("Multiple Source Inputs")
        box.setText(
            "This data was derived from multiple source inputs. Saving only "
            "this UDS may omit other workspace data required to reproduce "
            "the result."
        )
        box.setInformativeText(
            f"The data records {source_count} source contributions. Saving "
            "the whole workspace is recommended.\n\nContinue saving only "
            "this UDS?"
        )
        continue_button = box.addButton(
            "Continue",
            QtWidgets.QMessageBox.ButtonRole.AcceptRole,
        )
        cancel_button = box.addButton(
            QtWidgets.QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(cancel_button)
        box.exec()
        return box.clickedButton() is continue_button

    def _confirm_skipped_workspace_items(
            self, heading: str, entries: list,
            *, allow_cancel: bool = True) -> bool:
        """Show every skipped item before a workspace operation continues."""
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

    def _choose_workspace_archive_target(self, operation: str):
        """Choose an archive target, defaulting to the active destination."""
        if self.shared_workspace is None:
            return self.private_workspace
        workspaces = [self.shared_workspace, self.private_workspace]
        active = self.active_workspace
        choices = [
            f"{'Shared' if ws.is_shared else 'Private'} — {ws.label}"
            + (" (active destination)" if ws is active else "")
            for ws in workspaces
        ]
        selected, accepted = QtWidgets.QInputDialog.getItem(
            self,
            f"{operation} Workspace",
            "Choose the workspace:",
            choices,
            workspaces.index(active),
            False,
        )
        if not accepted:
            return None
        return workspaces[choices.index(selected)]

    def _confirm_shared_workspace_import(self, workspace) -> bool:
        attached_count = len(
            self._context.workspace_manager.attached_module_ids(
                workspace.workspace_id))
        answer = QtWidgets.QMessageBox.question(
            self,
            "Import into Shared Workspace?",
            f"Import items into shared workspace '{workspace.label}'?\n\n"
            f"The changes will be visible immediately to {attached_count} "
            "attached module(s).",
            QtWidgets.QMessageBox.StandardButton.Ok
            | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        return answer == QtWidgets.QMessageBox.StandardButton.Ok

    def _on_workspace_save(self) -> None:
        from angstrompro.io.workspace_io import (
            save_workspace, split_supported_items,
        )

        chooser = getattr(self, "_choose_workspace_archive_target", None)
        workspace = chooser("Save") if callable(chooser) else self.workspace
        if workspace is None:
            return

        items = workspace.list_items()
        if not items:
            QtWidgets.QMessageBox.information(
                self, "Empty workspace",
                f"Workspace '{workspace.label}' has no items to save.")
            return

        supported, unsupported = split_supported_items(items)
        if unsupported and not self._confirm_skipped_workspace_items(
                "These workspace items use payload types that cannot be "
                "stored in a workspace archive:", unsupported):
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
        from pathlib import Path
        suggested = (
            str(Path(start_dir) / "workspace.apws")
            if start_dir else "workspace.apws"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            f"Save Workspace — {workspace.label}",
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
            self.statusBar().showMessage(
                f"Workspace '{workspace.label}' saved: "
                f"{len(supported)} item(s) → {archive_path}",
                5000,
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Workspace save failed", str(exc))

    def _on_workspace_open(self) -> None:
        from angstrompro.io.workspace_io import (
            import_workspace, load_workspace,
        )

        chooser = getattr(self, "_choose_workspace_archive_target", None)
        workspace = chooser("Open") if callable(chooser) else self.workspace
        if workspace is None:
            return

        start_dir = self._context.config.get("io", "default_open_dir") or ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            f"Open Workspace — {workspace.label}",
            start_dir,
            "AngstromPro Workspace (*.apws *.h5 *.hdf5);;All Files (*)",
        )
        if not path:
            return

        from pathlib import Path
        archive_path = Path(path)
        try:
            archive = load_workspace(archive_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Workspace open failed", str(exc))
            return

        if archive.skipped:
            self._confirm_skipped_workspace_items(
                "These archive items cannot be loaded by this installation "
                "and were skipped:",
                archive.skipped,
                allow_cancel=False,
            )
        if not archive.items:
            QtWidgets.QMessageBox.information(
                self, "Nothing to load",
                "The workspace archive contains no supported items.")
            return

        if workspace.is_shared:
            confirmer = getattr(self, "_confirm_shared_workspace_import", None)
            if callable(confirmer) and not confirmer(workspace):
                return

        imported, renamed = import_workspace(archive, workspace)
        message = (
            f"Loaded {len(imported)} item(s) into workspace "
            f"'{workspace.label}' from {archive_path}"
        )
        if renamed:
            message += f"; {len(renamed)} renamed to avoid name conflicts"
        self.statusBar().showMessage(message, 6000)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        wm  = self._context.workspace_manager

        def _guard(ws_id, *_args):
            accessible_ids = {
                workspace.workspace_id
                for workspace in self.accessible_workspaces()
            }
            if ws_id in accessible_ids:
                self._refresh_workspace_panel()
                self.on_workspace_changed()

        wm.item_added.connect(_guard)
        wm.item_removed.connect(_guard)
        wm.item_renamed.connect(_guard)
        wm.item_changed.connect(_guard)
        wm.workspace_renamed.connect(_guard)

        self._ws_list.currentItemChanged.connect(self._on_ws_selection_changed)  # type: ignore[attr-defined]
        self._ws_list.itemSelectionChanged.connect(
            self._on_ws_selection_set_changed)

        self._context.signals.status_message.connect(self.statusBar().showMessage)
        self._context.signals.processes_updated.connect(self._rebuild_process_submenu)

    def _on_ws_selection_changed(self, current, _previous) -> None:
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        if current is None:
            self._inspector.set_item(None)
            return
        data = current.data(0, _UserRole)
        _kind, _workspace, item, _role = self._workspace_tree_context(data)
        self._inspector.set_item(item)
        self._update_workspace_selection_actions()

    def _on_ws_selection_set_changed(self) -> None:
        """Update bulk-action scope without changing the focused inspector item."""
        self._update_workspace_selection_actions()

    def on_workspace_attachment_changed(self) -> None:
        """Refresh module chrome after its shared-workspace attachment changes."""
        if hasattr(self, "_ws_list"):
            self._refresh_workspace_panel()
            self.on_workspace_changed()
        if hasattr(self, "statusBar"):
            if self.shared_workspace is None:
                message = "Detached from shared workspace; outputs now go to the private workspace."
            else:
                message = (
                    f"Attached to shared workspace '{self.shared_workspace.label}'; "
                    f"active destination: {self.active_workspace.label}."
                )
            self.statusBar().showMessage(message, 5000)

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
        destination = self.workspace

        handle = self.process_runner.run(
            process_name = process_name,
            input_items  = input_items,
            params       = params,
            source_id    = self.instance_id,
            group_id     = group_id,
        )
        handle.error.connect(self._on_process_error)
        result_callback = (on_result if on_result is not None
                           else self._on_process_result_default)
        captured_inputs = list(input_items)
        handle.result.connect(
            lambda task_id, result, callback=result_callback,
                   inputs=captured_inputs, workspace=destination:
            self._dispatch_process_result(
                task_id, result, callback, inputs, output_workspace=workspace))
        if on_error is not None:
            handle.error.connect(on_error)

        # Status bar feedback wired to this handle's lifecycle.
        # Explicit QueuedConnection: handle signals may be emitted from the worker
        # thread (if any upstream slot runs there); QueuedConnection ensures the
        # status-bar update always executes on the GUI thread.
        _Q = QtCore.Qt.ConnectionType.QueuedConnection
        sb = self.statusBar()
        sb.showMessage(f"{label}: submitted…")
        handle.started.connect(
            lambda _tid, l=label: sb.showMessage(f"{l}: running…"), _Q)
        handle.progress.connect(
            lambda _tid, cur, tot, l=label:
                sb.showMessage(f"{l}: {cur}/{tot}"), _Q)
        handle.result.connect(
            lambda _tid, _res, l=label: sb.showMessage(f"{l}: done.", 5000), _Q)
        handle.error.connect(
            lambda _tid, _err, l=label: sb.showMessage(f"{l}: failed.", 8000), _Q)
        handle.cancelled.connect(
            lambda _tid, l=label: sb.showMessage(f"{l}: cancelled.", 5000), _Q)

        return handle

    @staticmethod
    def _derived_process_alias(
            primary_item: WorkspaceItem | None, output_name: str) -> str:
        """Compatibility wrapper around the shared workspace naming rule."""
        from angstrompro.core.workspaces import derived_process_alias
        return derived_process_alias(primary_item, output_name)

    def _dispatch_process_result(
            self, task_id: str, result: Any, callback: Callable,
            input_items: list[WorkspaceItem], *, output_workspace=None) -> None:
        """Run the result callback, then alias newly-added result items."""
        if output_workspace is not None:
            manager = self._context.workspace_manager
            if manager.workspaces.get(output_workspace.workspace_id) is not output_workspace:
                message = (
                    f"The process finished, but its destination workspace "
                    f"'{output_workspace.label}' was removed. No output items were saved."
                )
                self._on_process_error(task_id, message)
                QtWidgets.QMessageBox.warning(self, "Process destination removed", message)
                return
            # Re-enter with the captured destination, including custom callbacks
            # that add items through self.workspace. Never switch the UI target.
            with self._process_output_scope(output_workspace):
                self._dispatch_process_result(task_id, result, callback, input_items)
            return
        workspaces = list(self.accessible_workspaces())
        captured = getattr(self, "_process_output_workspace", None)
        if captured is not None and captured not in workspaces:
            workspaces.append(captured)
        before_ids = {
            item.item_id
            for workspace in workspaces
            for item in workspace.list_items()
        }
        callback(task_id, result)
        from angstrompro.core.processes import normalize_process_result
        structured = normalize_process_result(result)
        primary_item = next(
            (item for item in input_items if item is not None), None)
        if primary_item is not None and structured.values:
            from copy import deepcopy
            primary_item.metadata.setdefault("process_results", []).append({
                "task_id": task_id,
                "values": deepcopy(structured.values),
                "units": dict(structured.value_units),
            })
            owner = self.workspace_containing_item(primary_item)
            if owner is not None:
                owner.notify_changed(primary_item.name)
        if primary_item is not None and structured.annotations:
            for role, annotation in structured.annotations.items():
                self._apply_annotation_output(primary_item, role, annotation)
        added_items = [
            item
            for workspace in workspaces
            for item in workspace.list_items()
            if item.item_id not in before_ids
        ]
        self._apply_process_result_aliases(input_items, result, added_items)

    def _annotation_output_targets(
            self, primary_item: WorkspaceItem, role: str) -> list[WorkspaceItem]:
        """Return item-local targets for one annotation output.

        Bragg coordinates describe reciprocal-space pixels, but established
        real-space processes also consume them.  An FFT item and its source
        therefore receive equivalent copies at the moment the annotation is
        created.  Other annotation roles remain local to the primary item.
        """
        targets = [primary_item]
        if role != "bragg_peaks":
            return targets

        from angstrompro.core.data.uds_data import is_fft_uds, fft_source_name

        payload = primary_item.payload
        counterpart = None
        if is_fft_uds(payload):
            source_name = fft_source_name(payload)
            if source_name:
                counterpart = self.find_accessible_item(
                    source_name, preferred_item=primary_item)
        else:
            for candidate in self.accessible_workspace_items():
                if (candidate.item_id != primary_item.item_id
                        and is_fft_uds(candidate.payload)
                        and fft_source_name(candidate.payload)
                        == primary_item.name):
                    counterpart = candidate
                    break
        if (counterpart is not None
                and counterpart.item_id != primary_item.item_id):
            targets.append(counterpart)
        return targets

    def _apply_annotation_output(
            self, primary_item: WorkspaceItem, role: str, annotation) -> None:
        """Apply an annotation and notify every item in its ownership pair."""
        from copy import deepcopy

        for index, target in enumerate(
                self._annotation_output_targets(primary_item, role)):
            target.annotations[role] = (
                annotation if index == 0 else deepcopy(annotation)
            )
            owner = self.workspace_containing_item(target)
            if owner is not None:
                owner.notify_changed(target.name)

    def _apply_process_result_aliases(
            self, input_items: list[WorkspaceItem], result: Any,
            added_items: list[WorkspaceItem]) -> None:
        primary_item = next(
            (item for item in input_items if item is not None), None)
        if primary_item is None or not primary_item.alias:
            return

        from angstrompro.core.data.base import WorkspaceData
        from angstrompro.core.processes import iter_process_data
        outputs = list(iter_process_data(result))
        output_payload_ids = {
            id(output) for output in outputs
            if isinstance(output, WorkspaceData)
        }
        for item in added_items:
            if item.alias or id(item.payload) not in output_payload_ids:
                continue
            alias = AGuiModule._derived_process_alias(primary_item, item.name)
            if not alias:
                continue
            item.alias = alias
            owner = self.workspace_containing_item(item)
            if owner is not None:
                owner.notify_changed(item.name)

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
        from angstrompro.core.processes import iter_process_data
        items = list(iter_process_data(result))
        for item in items:
            if not isinstance(item, WorkspaceData):
                log.warning(
                    "Process returned %s which is not WorkspaceData — not added to workspace",
                    type(item).__name__,
                )
                continue
            if not item.name:
                item.name = "result"
            self.workspace.add_item(payload=item)

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

    def on_workspace_changed(self) -> None:
        """Called after any workspace mutation. Override for extra refresh logic."""

    def _window_layout_qsettings_prefix(self) -> str:
        return f"module/{self.module_id}"

    def _restore_window_layout(self) -> None:
        if not self.persist_window_layout:
            return
        from angstrompro.app.user_data_folder import get_qsettings

        qs = get_qsettings()
        prefix = self._window_layout_qsettings_prefix()
        geometry = qs.value(f"{prefix}/geometry")
        state = qs.value(f"{prefix}/layout")
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)

    def _save_window_layout(self) -> None:
        if not self.persist_window_layout:
            return
        from angstrompro.app.user_data_folder import get_qsettings

        qs = get_qsettings()
        prefix = self._window_layout_qsettings_prefix()
        qs.setValue(f"{prefix}/geometry", self.saveGeometry())
        qs.setValue(f"{prefix}/layout", self.saveState())
        qs.sync()

    def save_state_for_exit(self) -> None:
        """Persist this module before the application event loop stops."""
        self._save_window_layout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.persist_window_layout and not getattr(
                self, "_window_layout_restored", False):
            self._window_layout_restored = True
            # Restore after lazy UI construction and subclass resize calls;
            # otherwise their default geometry wins during startup.
            QtCore.QTimer.singleShot(0, self._restore_window_layout)

    def closeEvent(self, event) -> None:
        """Close the native window while retaining the reusable module object.

        Qt hides an accepted top-level window without deleting it unless
        WA_DeleteOnClose is enabled.  Using the normal close lifecycle also
        lets macOS leave a maximized/full-screen Space correctly.
        """
        self._save_window_layout()
        event.accept()
