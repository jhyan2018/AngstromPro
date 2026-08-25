# -*- coding: utf-8 -*-
"""Configure explicit, user-named submenus for each module's Process menu."""

from __future__ import annotations

from typing import TYPE_CHECKING

from angstrompro.core.processes.menu_layout import (
    LAYOUT_VERSION,
    empty_process_menu_layout,
    normalize_process_menu_layout,
    normalize_process_menu_layouts,
)
from angstrompro.gui.dialogs.persistent_dialog import PersistentDialog
from angstrompro.utils.qt_compat import IS_QT6, QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

if IS_QT6:
    _ROLE = QtCore.Qt.ItemDataRole.UserRole
    _EXTENDED_SELECTION = (
        QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    _SAVE_BUTTON = QtWidgets.QDialogButtonBox.StandardButton.Save
    _CANCEL_BUTTON = QtWidgets.QDialogButtonBox.StandardButton.Cancel
    _YES_BUTTON = QtWidgets.QMessageBox.StandardButton.Yes
    _NO_BUTTON = QtWidgets.QMessageBox.StandardButton.No
    _PALETTE_MID = QtGui.QPalette.ColorRole.Mid
else:
    _ROLE = QtCore.Qt.UserRole
    _EXTENDED_SELECTION = QtWidgets.QAbstractItemView.ExtendedSelection
    _SAVE_BUTTON = QtWidgets.QDialogButtonBox.Save
    _CANCEL_BUTTON = QtWidgets.QDialogButtonBox.Cancel
    _YES_BUTTON = QtWidgets.QMessageBox.Yes
    _NO_BUTTON = QtWidgets.QMessageBox.No
    _PALETTE_MID = QtGui.QPalette.Mid


class ProcessMenuConfigDialog(PersistentDialog):
    """Edit ordered submenu groups and their ordered process children."""

    _settings_key = "ProcessMenuConfigDialog"

    def __init__(
        self,
        context: "AppContext",
        initial_module_id: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent, default_size=(900, 560))
        self._context = context
        self._initial_module_id = initial_module_id
        self._layouts = normalize_process_menu_layouts(
            context.config.get("algorithms", "process_menu_layouts", {}))
        self._active_module_id = ""

        self.setWindowTitle("Configure Process Menu")
        self._setup_ui()
        self._populate_module_selector()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel("Module:"))
        self._module_combo = QtWidgets.QComboBox()
        self._module_combo.setMinimumWidth(250)
        self._module_combo.currentIndexChanged.connect(
            self._on_module_changed)
        top_row.addWidget(self._module_combo)
        top_row.addStretch()
        self._show_incompat_cb = QtWidgets.QCheckBox(
            "Show incompatible processes")
        self._show_incompat_cb.toggled.connect(self._refresh_available)
        top_row.addWidget(self._show_incompat_cb)
        root.addLayout(top_row)

        transfer = QtWidgets.QHBoxLayout()
        transfer.setSpacing(8)

        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("Available processes:"))
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText(
            "Filter by process name, ID, category, or description…")
        self._search.textChanged.connect(self._refresh_available)
        left.addWidget(self._search)
        self._available_list = QtWidgets.QListWidget()
        self._available_list.setSelectionMode(_EXTENDED_SELECTION)
        self._available_list.itemDoubleClicked.connect(self._add_selected)
        left.addWidget(self._available_list, 1)
        transfer.addLayout(left, 1)

        centre = QtWidgets.QVBoxLayout()
        centre.addStretch()
        self._btn_add_process = QtWidgets.QPushButton("→")
        self._btn_add_process.setFixedWidth(38)
        self._btn_add_process.setToolTip(
            "Add selected processes to the selected submenu")
        self._btn_add_process.clicked.connect(self._add_selected)
        centre.addWidget(self._btn_add_process)
        self._btn_remove = QtWidgets.QPushButton("←")
        self._btn_remove.setFixedWidth(38)
        self._btn_remove.setToolTip(
            "Remove selected processes or submenus")
        self._btn_remove.clicked.connect(self._remove_selected)
        centre.addWidget(self._btn_remove)
        centre.addStretch()
        transfer.addLayout(centre)

        right = QtWidgets.QVBoxLayout()
        right.addWidget(QtWidgets.QLabel("Process menu layout:"))
        self._menu_tree = QtWidgets.QTreeWidget()
        self._menu_tree.setHeaderLabels(["Submenus and processes"])
        self._menu_tree.setSelectionMode(_EXTENDED_SELECTION)
        self._menu_tree.itemDoubleClicked.connect(
            self._on_tree_item_double_clicked)
        right.addWidget(self._menu_tree, 1)

        group_row = QtWidgets.QHBoxLayout()
        self._btn_add_group = QtWidgets.QPushButton("Add submenu…")
        self._btn_rename_group = QtWidgets.QPushButton("Rename…")
        self._btn_delete = QtWidgets.QPushButton("Delete")
        self._btn_move_to = QtWidgets.QPushButton("Move to…")
        self._btn_up = QtWidgets.QPushButton("↑")
        self._btn_down = QtWidgets.QPushButton("↓")
        self._btn_add_group.clicked.connect(self._add_group)
        self._btn_rename_group.clicked.connect(self._rename_group)
        self._btn_delete.clicked.connect(self._remove_selected)
        self._btn_move_to.clicked.connect(self._move_processes_to_group)
        self._btn_up.clicked.connect(lambda: self._move_selected(-1))
        self._btn_down.clicked.connect(lambda: self._move_selected(+1))
        group_row.addWidget(self._btn_add_group)
        group_row.addWidget(self._btn_rename_group)
        group_row.addWidget(self._btn_delete)
        group_row.addWidget(self._btn_move_to)
        group_row.addStretch()
        group_row.addWidget(self._btn_up)
        group_row.addWidget(self._btn_down)
        right.addLayout(group_row)
        transfer.addLayout(right, 1)
        root.addLayout(transfer, 1)

        note = QtWidgets.QLabel(
            "Only the submenus shown in this tree appear beneath Process. "
            "An empty tree leaves only Process Browser and Configure Process Menu."
        )
        note.setWordWrap(True)
        from angstrompro.gui.appearance.typography import (
            SECONDARY, set_typography_role,
        )
        set_typography_role(note, SECONDARY)
        root.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(
            _SAVE_BUTTON | _CANCEL_BUTTON,
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    # Module selection and layout persistence
    # ------------------------------------------------------------------

    def _populate_module_selector(self) -> None:
        self._module_combo.blockSignals(True)
        self._module_combo.clear()

        seen: set[str] = set()
        self._module_entries: list[tuple[str, str]] = []
        for instance in self._context.module_manager.list_instances():
            if instance.module_id in seen:
                continue
            seen.add(instance.module_id)
            display = instance.display_name or instance.module_id
            self._module_entries.append((instance.module_id, display))
            self._module_combo.addItem(
                f"{display}  [{instance.module_id}]", instance.module_id)

        self._module_combo.blockSignals(False)
        initial_index = 0
        for index, (module_id, _display) in enumerate(self._module_entries):
            if module_id == self._initial_module_id:
                initial_index = index
                break
        self._module_combo.setCurrentIndex(initial_index)
        self._on_module_changed(initial_index)

    def _current_module_id(self) -> str:
        index = self._module_combo.currentIndex()
        if index < 0 or index >= len(self._module_entries):
            return ""
        return self._module_entries[index][0]

    def _current_module_instance(self):
        module_id = self._current_module_id()
        for instance in self._context.module_manager.list_instances():
            if instance.module_id == module_id:
                return instance
        return None

    def _on_module_changed(self, _index: int) -> None:
        if self._active_module_id:
            self._store_tree(self._active_module_id)
        self._active_module_id = self._current_module_id()
        self._refresh_tree()
        self._refresh_available()

    def _store_tree(self, module_id: str | None = None) -> None:
        module_id = module_id or self._active_module_id
        if not module_id:
            return
        groups = []
        for group_index in range(self._menu_tree.topLevelItemCount()):
            group_item = self._menu_tree.topLevelItem(group_index)
            processes = [
                group_item.child(child_index).data(0, _ROLE)
                for child_index in range(group_item.childCount())
                if group_item.child(child_index).data(0, _ROLE)
            ]
            groups.append({
                "title": group_item.text(0).strip(),
                "processes": processes,
            })
        layout = normalize_process_menu_layout({
            "version": LAYOUT_VERSION,
            "groups": groups,
        })
        if layout["groups"]:
            self._layouts[module_id] = layout
        else:
            self._layouts.pop(module_id, None)

    # ------------------------------------------------------------------
    # Tree and available-process population
    # ------------------------------------------------------------------

    def _refresh_tree(self) -> None:
        self._menu_tree.clear()
        module_id = self._current_module_id()
        layout = self._layouts.get(
            module_id, empty_process_menu_layout())
        registry = self._context.processes

        for group in layout["groups"]:
            group_item = QtWidgets.QTreeWidgetItem([group["title"]])
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            self._menu_tree.addTopLevelItem(group_item)
            for process_name in group["processes"]:
                self._append_process_item(
                    group_item, process_name, registry)
            group_item.setExpanded(True)

    def _append_process_item(self, group_item, process_name: str, registry) -> None:
        if registry.has(process_name):
            entry = registry.get(process_name)
            label = f"{entry.label}  ({process_name})"
            tooltip = (
                f"Category: {entry.category}\n"
                f"{entry.description or process_name}"
            )
        else:
            label = f"{process_name}  ⚠ not registered"
            tooltip = "This process is not currently registered."
        item = QtWidgets.QTreeWidgetItem([label])
        item.setData(0, _ROLE, process_name)
        item.setToolTip(0, tooltip)
        group_item.addChild(item)

    def _assigned_processes(self) -> set[str]:
        assigned = set()
        for group_index in range(self._menu_tree.topLevelItemCount()):
            group_item = self._menu_tree.topLevelItem(group_index)
            for child_index in range(group_item.childCount()):
                name = group_item.child(child_index).data(0, _ROLE)
                if name:
                    assigned.add(name)
        return assigned

    def _refresh_available(self) -> None:
        self._available_list.clear()
        instance = self._current_module_instance()
        if instance is None:
            return

        query = self._search.text().strip().casefold()
        show_incompatible = self._show_incompat_cb.isChecked()
        assigned = self._assigned_processes()
        entries = sorted(
            self._context.processes.all_entries(),
            key=lambda entry: (entry.label.casefold(), entry.name.casefold()),
        )
        for entry in entries:
            if entry.kind != "process" or entry.name in assigned:
                continue
            searchable = " ".join((
                entry.label,
                entry.name,
                entry.category,
                entry.description or "",
            )).casefold()
            if query and query not in searchable:
                continue

            compatible = self._is_compatible(entry, instance)
            if not compatible and not show_incompatible:
                continue
            label = f"{entry.label}  ({entry.name})"
            if not compatible:
                label += "  ⚠ incompatible"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(_ROLE, entry.name)
            item.setToolTip(
                f"Category: {entry.category}\n"
                f"{entry.description or entry.name}")
            if not compatible:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
                item.setForeground(
                    QtWidgets.QApplication.palette().color(
                        _PALETTE_MID))
            self._available_list.addItem(item)

    @staticmethod
    def _is_compatible(entry, instance) -> bool:
        accepted_types = getattr(instance, "accepted_types", set())
        accepted_ndim = getattr(instance, "accepted_ndim", None)
        specs = entry.schema.inputs if entry.schema.inputs else entry.schema.outputs
        for spec in specs:
            if accepted_types and spec.type_id and spec.type_id not in accepted_types:
                return False
            if (accepted_ndim is not None and spec.ndim is not None and
                    spec.ndim != accepted_ndim):
                return False
        return True

    # ------------------------------------------------------------------
    # Submenu editing
    # ------------------------------------------------------------------

    def _existing_titles(self, exclude=None) -> set[str]:
        return {
            self._menu_tree.topLevelItem(index).text(0).strip().casefold()
            for index in range(self._menu_tree.topLevelItemCount())
            if self._menu_tree.topLevelItem(index) is not exclude
        }

    def _request_title(self, caption: str, initial: str = "", exclude=None):
        title, accepted = QtWidgets.QInputDialog.getText(
            self, caption, "Submenu name:", text=initial)
        if not accepted:
            return None
        title = title.strip()
        if not title:
            QtWidgets.QMessageBox.warning(
                self, "Invalid name", "The submenu name cannot be empty.")
            return None
        if title.casefold() in self._existing_titles(exclude):
            QtWidgets.QMessageBox.warning(
                self, "Duplicate name",
                "Each submenu must have a different name.")
            return None
        return title

    def _add_group(self) -> None:
        title = self._request_title("Add submenu")
        if title is None:
            return
        item = QtWidgets.QTreeWidgetItem([title])
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        self._menu_tree.addTopLevelItem(item)
        item.setExpanded(True)
        self._menu_tree.setCurrentItem(item)
        self._after_tree_changed()

    def _selected_group(self):
        item = self._menu_tree.currentItem()
        if item is None:
            return None
        return item if item.parent() is None else item.parent()

    def _rename_group(self) -> None:
        group = self._selected_group()
        if group is None:
            return
        title = self._request_title(
            "Rename submenu", group.text(0), exclude=group)
        if title is None:
            return
        group.setText(0, title)
        self._after_tree_changed(refresh_available=False)

    def _on_tree_item_double_clicked(self, item, _column: int) -> None:
        if item.parent() is None:
            self._menu_tree.setCurrentItem(item)
            self._rename_group()

    # ------------------------------------------------------------------
    # Process transfer and ordering
    # ------------------------------------------------------------------

    def _add_selected(self, *_args) -> None:
        selected = self._available_list.selectedItems()
        if not selected:
            return
        group = self._selected_group()
        if group is None:
            if self._menu_tree.topLevelItemCount() == 1:
                group = self._menu_tree.topLevelItem(0)
            else:
                QtWidgets.QMessageBox.information(
                    self, "Select a submenu",
                    "Create or select a submenu before adding processes.")
                return

        registry = self._context.processes
        for available_item in selected:
            process_name = available_item.data(_ROLE)
            if process_name:
                self._append_process_item(group, process_name, registry)
        group.setExpanded(True)
        self._menu_tree.setCurrentItem(group)
        self._after_tree_changed()

    def _remove_selected(self) -> None:
        selected = self._menu_tree.selectedItems()
        if not selected:
            return
        groups = [item for item in selected if item.parent() is None]
        if groups and any(group.childCount() for group in groups):
            answer = QtWidgets.QMessageBox.question(
                self,
                "Delete submenu",
                "Delete the selected submenu and all processes inside it?",
                _YES_BUTTON | _NO_BUTTON,
            )
            if answer != _YES_BUTTON:
                return

        group_ids = {id(group) for group in groups}
        for item in list(selected):
            parent = item.parent()
            if parent is None:
                index = self._menu_tree.indexOfTopLevelItem(item)
                if index >= 0:
                    self._menu_tree.takeTopLevelItem(index)
            elif id(parent) not in group_ids:
                parent.removeChild(item)
        self._after_tree_changed()

    def _move_selected(self, direction: int) -> None:
        item = self._menu_tree.currentItem()
        if item is None:
            return
        parent = item.parent()
        if parent is None:
            row = self._menu_tree.indexOfTopLevelItem(item)
            new_row = row + direction
            if (row < 0 or new_row < 0 or
                    new_row >= self._menu_tree.topLevelItemCount()):
                return
            item = self._menu_tree.takeTopLevelItem(row)
            self._menu_tree.insertTopLevelItem(new_row, item)
        else:
            row = parent.indexOfChild(item)
            new_row = row + direction
            if row < 0 or new_row < 0 or new_row >= parent.childCount():
                return
            item = parent.takeChild(row)
            parent.insertChild(new_row, item)
        self._menu_tree.setCurrentItem(item)
        self._after_tree_changed(refresh_available=False)

    def _move_processes_to_group(self) -> None:
        processes = [
            item for item in self._menu_tree.selectedItems()
            if item.parent() is not None
        ]
        if not processes:
            QtWidgets.QMessageBox.information(
                self, "Select processes",
                "Select one or more processes to move.")
            return
        if self._menu_tree.topLevelItemCount() < 2:
            return

        titles = [
            self._menu_tree.topLevelItem(index).text(0)
            for index in range(self._menu_tree.topLevelItemCount())
        ]
        title, accepted = QtWidgets.QInputDialog.getItem(
            self, "Move processes", "Destination submenu:", titles, 0, False)
        if not accepted:
            return
        target = self._menu_tree.topLevelItem(titles.index(title))
        for item in processes:
            parent = item.parent()
            if parent is target:
                continue
            parent.takeChild(parent.indexOfChild(item))
            target.addChild(item)
        target.setExpanded(True)
        self._menu_tree.setCurrentItem(target)
        self._after_tree_changed(refresh_available=False)

    def _after_tree_changed(self, *, refresh_available: bool = True) -> None:
        self._store_tree()
        if refresh_available:
            self._refresh_available()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._store_tree()
        self._layouts = normalize_process_menu_layouts(self._layouts)
        self._context.config.set(
            "algorithms", "process_menu_layouts", self._layouts)
        self._context.config.save_defaults()
        self.accept()


__all__ = ["ProcessMenuConfigDialog"]
