# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 2026

@author: jiahaoYan

ProcessMenuConfigDialog — end-user UI for configuring which registered
processes appear in each module's Process menu.

Only writes to the "user_process_menus" config key. The developer defaults
(class-level default_process_menu and algorithms.process_menus config) are
shown as read-only context but are never modified here.

After accepting, the caller should emit context.signals.processes_updated
so all open module windows rebuild their menus immediately.

Usage
-----
    dlg = ProcessMenuConfigDialog(context, initial_module_id="image2u3", parent=self)
    if dlg.exec():
        context.signals.processes_updated.emit()
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

_ROLE = QtCore.Qt.ItemDataRole.UserRole if hasattr(
    QtCore.Qt.ItemDataRole, "UserRole") else QtCore.Qt.UserRole


class ProcessMenuConfigDialog(QtWidgets.QDialog):

    def __init__(
        self,
        context:           "AppContext",
        initial_module_id: str  = "",
        parent:            QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._initial_module_id = initial_module_id

        # working copy of user_process_menus — only written on accept
        raw = context.config.get("algorithms", "user_process_menus", {})
        self._user_menus: dict[str, list[str]] = copy.deepcopy(raw)

        self.setWindowTitle("Configure Process Menu")
        self.resize(700, 480)
        self._setup_ui()
        self._populate_module_selector()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # --- module selector ---
        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel("Module:"))
        self._module_combo = QtWidgets.QComboBox()
        self._module_combo.setMinimumWidth(200)
        self._module_combo.currentIndexChanged.connect(self._on_module_changed)
        top_row.addWidget(self._module_combo)
        top_row.addStretch()

        self._show_incompat_cb = QtWidgets.QCheckBox("Show incompatible processes")
        self._show_incompat_cb.toggled.connect(self._refresh_available)
        top_row.addWidget(self._show_incompat_cb)
        root.addLayout(top_row)

        # --- two-panel transfer area ---
        transfer = QtWidgets.QHBoxLayout()
        transfer.setSpacing(6)

        # left: available processes
        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("Available processes:"))
        self._available_list = QtWidgets.QListWidget()
        self._available_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._available_list.itemDoubleClicked.connect(self._add_selected)
        left.addWidget(self._available_list)
        transfer.addLayout(left)

        # centre: add / remove buttons
        btn_col = QtWidgets.QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.addStretch()
        self._btn_add = QtWidgets.QPushButton("→")
        self._btn_add.setFixedWidth(36)
        self._btn_add.setToolTip("Add to menu")
        self._btn_add.clicked.connect(self._add_selected)
        btn_col.addWidget(self._btn_add)
        self._btn_remove = QtWidgets.QPushButton("←")
        self._btn_remove.setFixedWidth(36)
        self._btn_remove.setToolTip("Remove from menu")
        self._btn_remove.clicked.connect(self._remove_selected)
        btn_col.addWidget(self._btn_remove)
        btn_col.addStretch()
        transfer.addLayout(btn_col)

        # right: current user menu additions
        right = QtWidgets.QVBoxLayout()
        right.addWidget(QtWidgets.QLabel("Your additions to menu:"))
        self._menu_list = QtWidgets.QListWidget()
        self._menu_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._menu_list.itemDoubleClicked.connect(self._remove_selected)
        right.addWidget(self._menu_list)

        # up/down ordering
        order_row = QtWidgets.QHBoxLayout()
        self._btn_up   = QtWidgets.QPushButton("↑")
        self._btn_down = QtWidgets.QPushButton("↓")
        self._btn_up.setFixedWidth(36)
        self._btn_down.setFixedWidth(36)
        self._btn_up.clicked.connect(self._move_up)
        self._btn_down.clicked.connect(self._move_down)
        order_row.addStretch()
        order_row.addWidget(self._btn_up)
        order_row.addWidget(self._btn_down)
        right.addLayout(order_row)
        transfer.addLayout(right)

        root.addLayout(transfer)

        # --- info label: what's already in menu via developer defaults ---
        self._info_label = QtWidgets.QLabel("")
        self._info_label.setStyleSheet("color: grey; font-size: 10px;")
        self._info_label.setWordWrap(True)
        root.addWidget(self._info_label)

        # --- bottom buttons ---
        bottom_row = QtWidgets.QHBoxLayout()
        self._btn_reset = QtWidgets.QPushButton("Reset to defaults")
        self._btn_reset.setToolTip("Remove all your additions for this module")
        self._btn_reset.clicked.connect(self._reset_current_module)
        bottom_row.addWidget(self._btn_reset)
        bottom_row.addStretch()
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel,
        )
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        bottom_row.addWidget(btn_box)
        root.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Module selector
    # ------------------------------------------------------------------

    def _populate_module_selector(self) -> None:
        self._module_combo.blockSignals(True)
        self._module_combo.clear()

        instances = self._context.module_manager.list_instances()
        # Deduplicate by module_id — config is per module type, not per instance
        seen: set[str] = set()
        self._module_entries: list[tuple[str, str]] = []  # (module_id, display_name)
        for inst in instances:
            if inst.module_id not in seen:
                seen.add(inst.module_id)
                label = f"{inst.display_name or inst.module_id}  [{inst.module_id}]"
                self._module_entries.append((inst.module_id, inst.display_name or inst.module_id))
                self._module_combo.addItem(label, inst.module_id)

        self._module_combo.blockSignals(False)

        # Pre-select initial module
        initial_idx = 0
        for i, (mid, _) in enumerate(self._module_entries):
            if mid == self._initial_module_id:
                initial_idx = i
                break
        self._module_combo.setCurrentIndex(initial_idx)
        self._on_module_changed(initial_idx)

    def _current_module_id(self) -> str:
        idx = self._module_combo.currentIndex()
        if idx < 0 or idx >= len(self._module_entries):
            return ""
        return self._module_entries[idx][0]

    def _current_module_instance(self):
        mid = self._current_module_id()
        for inst in self._context.module_manager.list_instances():
            if inst.module_id == mid:
                return inst
        return None

    # ------------------------------------------------------------------
    # Panel population
    # ------------------------------------------------------------------

    def _on_module_changed(self, _index: int) -> None:
        self._refresh_available()
        self._refresh_menu_list()
        self._update_info_label()

    def _refresh_available(self) -> None:
        self._available_list.clear()
        mid  = self._current_module_id()
        inst = self._current_module_instance()
        show_incompat = self._show_incompat_cb.isChecked()

        registry = self._context.processes
        # accepted constraints from module class (may be None/empty = any)
        accepted_types = getattr(inst, "accepted_types", set()) if inst else set()
        accepted_ndim  = getattr(inst, "accepted_ndim",  None)  if inst else None

        # already in user menu for this module
        already_added = set(self._user_menus.get(mid, []))
        # already covered by developer defaults
        dev_names = set(
            self._context.config.get("algorithms", "process_menus", {}).get(mid, [])
        )
        class_names = set(getattr(inst, "default_process_menu", []) if inst else [])
        developer_set = dev_names | class_names

        for entry in sorted(registry.all_entries(), key=lambda e: (e.category, e.label)):
            # skip already-added to user menu
            if entry.name in already_added:
                continue

            # compatibility check
            compatible = True
            for spec in entry.schema.inputs:
                if accepted_types and spec.type_id and spec.type_id not in accepted_types:
                    compatible = False
                    break
                if (accepted_ndim is not None and
                        spec.ndim is not None and
                        spec.ndim != accepted_ndim):
                    compatible = False
                    break

            if not compatible and not show_incompat:
                continue

            label = f"[{entry.category}]  {entry.label}  ({entry.name})"
            if entry.name in developer_set:
                label += "  ✓ default"
            if not compatible:
                label += "  ⚠ incompatible"

            item = QtWidgets.QListWidgetItem(label)
            item.setData(_ROLE, entry.name)
            if entry.name in developer_set:
                item.setForeground(
                    QtWidgets.QApplication.palette().color(
                        QtWidgets.QPalette.ColorRole.Mid
                        if hasattr(QtWidgets.QPalette.ColorRole, "Mid")
                        else QtWidgets.QPalette.Mid
                    )
                )
            if not compatible:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
            self._available_list.addItem(item)

    def _refresh_menu_list(self) -> None:
        self._menu_list.clear()
        mid = self._current_module_id()
        registry = self._context.processes
        for name in self._user_menus.get(mid, []):
            if registry.has(name):
                entry = registry.get(name)
                label = f"[{entry.category}]  {entry.label}  ({name})"
            else:
                label = f"{name}  ⚠ not registered"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(_ROLE, name)
            self._menu_list.addItem(item)

    def _update_info_label(self) -> None:
        mid  = self._current_module_id()
        inst = self._current_module_instance()
        class_names = list(getattr(inst, "default_process_menu", []) if inst else [])
        dev_names   = self._context.config.get(
            "algorithms", "process_menus", {}).get(mid, [])
        combined = list(dict.fromkeys(class_names + list(dev_names)))
        if combined:
            self._info_label.setText(
                f"Already in menu by default: {', '.join(combined)}  "
                f"(set by developer — not editable here)"
            )
        else:
            self._info_label.setText("No developer defaults for this module.")

    # ------------------------------------------------------------------
    # Transfer actions
    # ------------------------------------------------------------------

    def _add_selected(self) -> None:
        mid = self._current_module_id()
        if not mid:
            return
        names = [
            item.data(_ROLE)
            for item in self._available_list.selectedItems()
            if item.data(_ROLE)
        ]
        current = self._user_menus.setdefault(mid, [])
        for name in names:
            if name not in current:
                current.append(name)
        self._refresh_available()
        self._refresh_menu_list()

    def _remove_selected(self) -> None:
        mid = self._current_module_id()
        if not mid:
            return
        names = {
            item.data(_ROLE)
            for item in self._menu_list.selectedItems()
            if item.data(_ROLE)
        }
        current = self._user_menus.get(mid, [])
        self._user_menus[mid] = [n for n in current if n not in names]
        self._refresh_available()
        self._refresh_menu_list()

    def _move_up(self) -> None:
        self._move_selected(-1)

    def _move_down(self) -> None:
        self._move_selected(+1)

    def _move_selected(self, direction: int) -> None:
        mid = self._current_module_id()
        if not mid:
            return
        row = self._menu_list.currentRow()
        lst = self._user_menus.get(mid, [])
        new_row = row + direction
        if row < 0 or new_row < 0 or new_row >= len(lst):
            return
        lst[row], lst[new_row] = lst[new_row], lst[row]
        self._refresh_menu_list()
        self._menu_list.setCurrentRow(new_row)

    def _reset_current_module(self) -> None:
        mid = self._current_module_id()
        if not mid:
            return
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Reset",
            f"Remove all your process menu additions for '{mid}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            self._user_menus.pop(mid, None)
            self._refresh_available()
            self._refresh_menu_list()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        # Remove empty lists to keep config clean
        cleaned = {k: v for k, v in self._user_menus.items() if v}
        self._context.config.set("algorithms", "user_process_menus", cleaned)
        self._context.config.save_defaults()
        self.accept()
