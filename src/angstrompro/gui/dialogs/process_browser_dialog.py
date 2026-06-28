# -*- coding: utf-8 -*-
"""
Created on Sat Jun 28 2026

@author: jiahaoYan

ProcessBrowserDialog — browse all registered processes by category.

Shows a filterable tree of every @register_process entry grouped by
category. Selecting an entry populates a detail panel with its description,
input ports, and parameter specifications.

Usage
-----
    dlg = ProcessBrowserDialog(context, parent=self)
    dlg.exec()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext
    from angstrompro.core.processes.process_entry import ProcessEntry


class ProcessBrowserDialog(QtWidgets.QDialog):

    def __init__(self, context: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.setWindowTitle("Process Browser")
        self.resize(820, 520)
        self._setup_ui()
        self._populate()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # --- search bar ---
        search_row = QtWidgets.QHBoxLayout()
        search_row.addWidget(QtWidgets.QLabel("Search:"))
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Filter by name, label, or category…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_filter_changed)
        search_row.addWidget(self._search)
        root.addLayout(search_row)

        # --- splitter: tree | detail ---
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal
                                       if hasattr(QtCore.Qt.Orientation, "Horizontal")
                                       else QtCore.Qt.Horizontal)

        # left: process tree
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setMinimumWidth(220)
        self._tree.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._tree)

        # right: detail panel
        detail_widget = QtWidgets.QWidget()
        detail_layout = QtWidgets.QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(8, 0, 0, 0)
        detail_layout.setSpacing(8)

        # name + id row
        name_form = QtWidgets.QFormLayout()
        name_form.setHorizontalSpacing(12)
        self._lbl_label    = QtWidgets.QLabel("—")
        self._lbl_name     = QtWidgets.QLabel("—")
        self._lbl_category = QtWidgets.QLabel("—")
        for lbl in (self._lbl_label, self._lbl_name, self._lbl_category):
            lbl.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
                if hasattr(QtCore.Qt.TextInteractionFlag, "TextSelectableByMouse")
                else QtCore.Qt.TextSelectableByMouse
            )
        name_form.addRow("Label:",    self._lbl_label)
        name_form.addRow("ID:",       self._lbl_name)
        name_form.addRow("Category:", self._lbl_category)
        detail_layout.addLayout(name_form)

        # description
        detail_layout.addWidget(QtWidgets.QLabel("Description:"))
        self._txt_description = QtWidgets.QTextEdit()
        self._txt_description.setReadOnly(True)
        self._txt_description.setMaximumHeight(72)
        self._txt_description.setPlaceholderText("No description.")
        detail_layout.addWidget(self._txt_description)

        # inputs table
        detail_layout.addWidget(QtWidgets.QLabel("Input Ports:"))
        self._tbl_inputs = QtWidgets.QTableWidget(0, 3)
        self._tbl_inputs.setHorizontalHeaderLabels(["Name", "Type", "Description"])
        self._tbl_inputs.horizontalHeader().setStretchLastSection(True)
        self._tbl_inputs.verticalHeader().setVisible(False)
        self._tbl_inputs.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_inputs.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_inputs.setAlternatingRowColors(True)
        self._tbl_inputs.setMaximumHeight(110)
        detail_layout.addWidget(self._tbl_inputs)

        # params table
        detail_layout.addWidget(QtWidgets.QLabel("Parameters:"))
        self._tbl_params = QtWidgets.QTableWidget(0, 6)
        self._tbl_params.setHorizontalHeaderLabels(
            ["Name", "Type", "Default", "Range", "Units", "Description"])
        self._tbl_params.horizontalHeader().setStretchLastSection(True)
        self._tbl_params.verticalHeader().setVisible(False)
        self._tbl_params.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_params.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_params.setAlternatingRowColors(True)
        detail_layout.addWidget(self._tbl_params)

        splitter.addWidget(detail_widget)
        splitter.setSizes([240, 560])
        root.addWidget(splitter)

        # --- close button ---
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

        # hint label at bottom
        self._hint = QtWidgets.QLabel("")
        self._hint.setStyleSheet("color: grey; font-size: 10px;")
        root.addWidget(self._hint)

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def _populate(self) -> None:
        self._tree.clear()
        registry = self._context.processes
        by_cat   = registry.by_category()
        total    = sum(len(v) for v in by_cat.values())

        for category in sorted(by_cat.keys()):
            entries = sorted(by_cat[category], key=lambda e: e.label)
            cat_item = QtWidgets.QTreeWidgetItem(self._tree, [category])
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            cat_item.setFlags(cat_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable
                              if hasattr(QtCore.Qt.ItemFlag, "ItemIsSelectable")
                              else cat_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            for entry in entries:
                child = QtWidgets.QTreeWidgetItem(cat_item, [entry.label])
                child.setData(0, QtCore.Qt.ItemDataRole.UserRole
                              if hasattr(QtCore.Qt.ItemDataRole, "UserRole")
                              else QtCore.Qt.UserRole, entry.name)
                child.setToolTip(0, entry.description or entry.label)

        self._tree.expandAll()
        self._hint.setText(
            f"{total} process{'es' if total != 1 else ''} registered  "
            f"across {len(by_cat)} categor{'ies' if len(by_cat) != 1 else 'y'}."
        )

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _on_filter_changed(self, text: str) -> None:
        text = text.strip().lower()
        _role = (QtCore.Qt.ItemDataRole.UserRole
                 if hasattr(QtCore.Qt.ItemDataRole, "UserRole")
                 else QtCore.Qt.UserRole)

        for cat_idx in range(self._tree.topLevelItemCount()):
            cat_item  = self._tree.topLevelItem(cat_idx)
            cat_label = cat_item.text(0).lower()
            any_visible = False
            for child_idx in range(cat_item.childCount()):
                child      = cat_item.child(child_idx)
                entry_name = (child.data(0, _role) or "").lower()
                entry_label = child.text(0).lower()
                visible = (not text or
                           text in entry_name or
                           text in entry_label or
                           text in cat_label)
                child.setHidden(not visible)
                if visible:
                    any_visible = True
            cat_item.setHidden(not any_visible)

    # ------------------------------------------------------------------
    # Detail panel
    # ------------------------------------------------------------------

    def _on_selection_changed(self, current, _previous) -> None:
        if current is None:
            self._clear_detail()
            return
        _role = (QtCore.Qt.ItemDataRole.UserRole
                 if hasattr(QtCore.Qt.ItemDataRole, "UserRole")
                 else QtCore.Qt.UserRole)
        name = current.data(0, _role)
        if not name:
            self._clear_detail()
            return
        entry = self._context.processes.get(name)
        self._show_entry(entry)

    def _clear_detail(self) -> None:
        self._lbl_label.setText("—")
        self._lbl_name.setText("—")
        self._lbl_category.setText("—")
        self._txt_description.setPlainText("")
        self._tbl_inputs.setRowCount(0)
        self._tbl_params.setRowCount(0)

    def _show_entry(self, entry: "ProcessEntry") -> None:
        self._lbl_label.setText(entry.label)
        self._lbl_name.setText(entry.name)
        self._lbl_category.setText(entry.category)
        self._txt_description.setPlainText(entry.description or "")

        # inputs
        self._tbl_inputs.setRowCount(0)
        for spec in entry.schema.inputs:
            row = self._tbl_inputs.rowCount()
            self._tbl_inputs.insertRow(row)
            self._tbl_inputs.setItem(row, 0, _ro_item(spec.name))
            self._tbl_inputs.setItem(row, 1, _ro_item(spec.type_id or "any"))
            self._tbl_inputs.setItem(row, 2, _ro_item(spec.description or spec.label))
        self._tbl_inputs.resizeColumnsToContents()
        if not entry.schema.inputs:
            self._tbl_inputs.setRowCount(1)
            self._tbl_inputs.setItem(0, 0, _ro_item("(none)"))

        # params
        self._tbl_params.setRowCount(0)
        for spec in entry.schema.params:
            row = self._tbl_params.rowCount()
            self._tbl_params.insertRow(row)
            lo = spec.min if spec.min is not None else "—"
            hi = spec.max if spec.max is not None else "—"
            rng = f"{lo} … {hi}" if (spec.min is not None or spec.max is not None) else "—"
            self._tbl_params.setItem(row, 0, _ro_item(spec.name))
            self._tbl_params.setItem(row, 1, _ro_item(spec.type.__name__))
            self._tbl_params.setItem(row, 2, _ro_item(str(spec.default)))
            self._tbl_params.setItem(row, 3, _ro_item(rng))
            self._tbl_params.setItem(row, 4, _ro_item(spec.units or "—"))
            self._tbl_params.setItem(row, 5, _ro_item(spec.description or spec.label))
        self._tbl_params.resizeColumnsToContents()
        if not entry.schema.params:
            self._tbl_params.setRowCount(1)
            self._tbl_params.setItem(0, 0, _ro_item("(none)"))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _ro_item(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable
                  if hasattr(QtCore.Qt.ItemFlag, "ItemIsEditable")
                  else item.flags() & ~QtCore.Qt.ItemIsEditable)
    return item
