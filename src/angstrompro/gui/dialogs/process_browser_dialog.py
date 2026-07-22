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
from angstrompro.gui.dialogs.persistent_dialog import PersistentDialog

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext
    from angstrompro.core.processes.process_entry import ProcessEntry


class ProcessBrowserDialog(PersistentDialog):

    _settings_key = "ProcessBrowserDialog"

    def __init__(self, context: "AppContext", parent=None) -> None:
        super().__init__(parent, default_size=(820, 560))
        self._context = context
        self.setWindowTitle("Process Browser")
        self._setup_ui()
        self._populate()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # --- convention notice ---
        notice = QtWidgets.QLabel(
            "<b>Naming convention:</b>  "
            "<code>_1D</code> processes operate on ndim=2 data (curve stacks) · "
            "<code>_2D</code> processes operate on ndim=3 data (image stacks).  "
            "Check the inspector to verify axis orientation before running."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "background: palette(mid); border-radius: 4px; padding: 6px;")
        root.addWidget(notice, 0)

        # --- search bar ---
        search_row = QtWidgets.QHBoxLayout()
        search_row.addWidget(QtWidgets.QLabel("Search:"))
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Filter by name, label, or category…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_filter_changed)
        search_row.addWidget(self._search)
        root.addLayout(search_row, 0)

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

        # right: detail panel inside a scroll area
        detail_inner = QtWidgets.QWidget()
        detail_inner.setMinimumWidth(480)   # triggers horizontal scrollbar when panel is narrow
        detail_layout = QtWidgets.QVBoxLayout(detail_inner)
        detail_layout.setContentsMargins(8, 4, 8, 8)
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

        # description — word-wrapping label, auto-heights to content
        detail_layout.addWidget(QtWidgets.QLabel("Description:"))
        self._txt_description = QtWidgets.QLabel()
        self._txt_description.setWordWrap(True)
        self._txt_description.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
            if hasattr(QtCore.Qt.AlignmentFlag, "AlignTop")
            else QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self._txt_description.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            if hasattr(QtCore.Qt.TextInteractionFlag, "TextSelectableByMouse")
            else QtCore.Qt.TextSelectableByMouse)
        self._txt_description.setStyleSheet(
            "QLabel { border: 1px solid palette(mid); border-radius: 3px;"
            " padding: 4px; background: palette(base); }")
        detail_layout.addWidget(self._txt_description)

        # inputs table
        detail_layout.addWidget(QtWidgets.QLabel("Input Ports:"))
        self._tbl_inputs = _AutoHeightTable(5)
        self._tbl_inputs.setHorizontalHeaderLabels(
            ["Name", "Type", "ndim", "Axis requirements", "Description"])
        _setup_table(self._tbl_inputs)
        detail_layout.addWidget(self._tbl_inputs)

        # outputs table
        detail_layout.addWidget(QtWidgets.QLabel("Output Ports:"))
        self._tbl_outputs = _AutoHeightTable(3)
        self._tbl_outputs.setHorizontalHeaderLabels(["Type", "ndim", "Description"])
        _setup_table(self._tbl_outputs)
        detail_layout.addWidget(self._tbl_outputs)

        # params table
        detail_layout.addWidget(QtWidgets.QLabel("Parameters:"))
        self._tbl_params = _AutoHeightTable(6)
        self._tbl_params.setHorizontalHeaderLabels(
            ["Name", "Type", "Default", "Range", "Units", "Description"])
        _setup_table(self._tbl_params)
        detail_layout.addWidget(self._tbl_params)

        detail_layout.addStretch()

        detail_scroll = QtWidgets.QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setWidget(detail_inner)
        detail_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame
                                    if hasattr(QtWidgets.QFrame.Shape, "NoFrame")
                                    else QtWidgets.QFrame.NoFrame)

        splitter.addWidget(detail_scroll)
        splitter.setSizes([240, 560])
        root.addWidget(splitter, 1)

        # --- close button + hint on same row ---
        bottom_row = QtWidgets.QHBoxLayout()
        self._hint = QtWidgets.QLabel("")
        from angstrompro.gui.appearance.typography import SECONDARY, set_typography_role
        set_typography_role(self._hint, SECONDARY)
        bottom_row.addWidget(self._hint)
        bottom_row.addStretch()
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        bottom_row.addWidget(btn_box)
        root.addLayout(bottom_row)

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
        self._txt_description.setText("")
        self._tbl_inputs.setRowCount(0)
        self._tbl_outputs.setRowCount(0)
        self._tbl_params.setRowCount(0)
        QtCore.QTimer.singleShot(0, self._refit_table_rows)

    def _refit_table_rows(self) -> None:
        for tbl in (self._tbl_inputs, self._tbl_outputs, self._tbl_params):
            tbl.resizeRowsToContents()
            tbl.updateGeometry()

    def _show_entry(self, entry: "ProcessEntry") -> None:
        self._lbl_label.setText(entry.label)
        self._lbl_name.setText(entry.name)
        self._lbl_category.setText(entry.category)
        self._txt_description.setText(entry.description or "")

        # inputs
        self._tbl_inputs.setRowCount(0)
        for spec in entry.schema.inputs:
            row = self._tbl_inputs.rowCount()
            self._tbl_inputs.insertRow(row)
            ndim_str = str(spec.ndim) if spec.ndim is not None else "any"
            axis_str = _format_axis_types(spec.axis_types)
            self._tbl_inputs.setItem(row, 0, _ro_item(spec.name))
            self._tbl_inputs.setItem(row, 1, _ro_item(spec.type_id or "any"))
            self._tbl_inputs.setItem(row, 2, _ro_item(ndim_str))
            self._tbl_inputs.setItem(row, 3, _ro_item(axis_str))
            self._tbl_inputs.setItem(row, 4, _ro_item(spec.description or spec.label))
        _resize_non_last_cols(self._tbl_inputs)
        if not entry.schema.inputs:
            self._tbl_inputs.setRowCount(1)
            self._tbl_inputs.setItem(0, 0, _ro_item("(none)"))

        # outputs
        self._tbl_outputs.setRowCount(0)
        for spec in entry.schema.outputs:
            row = self._tbl_outputs.rowCount()
            self._tbl_outputs.insertRow(row)
            ndim_str = str(spec.ndim) if spec.ndim is not None else "any"
            self._tbl_outputs.setItem(row, 0, _ro_item(spec.type_id or "any"))
            self._tbl_outputs.setItem(row, 1, _ro_item(ndim_str))
            self._tbl_outputs.setItem(row, 2, _ro_item(spec.description or spec.label))
        _resize_non_last_cols(self._tbl_outputs)
        if not entry.schema.outputs:
            self._tbl_outputs.setRowCount(1)
            self._tbl_outputs.setItem(0, 0, _ro_item("(inferred)"))

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
        _resize_non_last_cols(self._tbl_params)
        if not entry.schema.params:
            self._tbl_params.setRowCount(1)
            self._tbl_params.setItem(0, 0, _ro_item("(none)"))

        # Defer row-height recalculation until after the layout engine has
        # finalized the stretch column widths, then re-notify the scroll area.
        QtCore.QTimer.singleShot(0, self._refit_table_rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _AutoHeightTable(QtWidgets.QTableWidget):
    """QTableWidget that sizes itself to show all rows without an internal scrollbar.

    Word-wrap is on, so row heights depend on column widths. resizeEvent
    recalculates row heights and notifies the parent layout whenever the
    table is resized (e.g. when the splitter or dialog is dragged).
    """

    def __init__(self, cols: int, parent=None):
        super().__init__(0, cols, parent)

    def sizeHint(self) -> QtCore.QSize:
        frame = self.frameWidth() * 2
        h = self.horizontalHeader().height() + frame
        for i in range(self.rowCount()):
            h += self.rowHeight(i)
        return QtCore.QSize(super().sizeHint().width(), h)

    def minimumSizeHint(self) -> QtCore.QSize:
        return self.sizeHint()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Recompute wrap heights after column widths change (e.g. splitter drag).
        QtCore.QTimer.singleShot(0, lambda: (self.resizeRowsToContents(), self.updateGeometry()))


# Minimum widths for the first two columns (Name, Type) and all others.
_MIN_COL_WIDTHS = {0: 140, 1: 80}
_MIN_COL_WIDTH_DEFAULT = 70


def _resize_non_last_cols(tbl: QtWidgets.QTableWidget) -> None:
    """Auto-size every column except the last (Description), which stretches."""
    for col in range(tbl.columnCount() - 1):
        tbl.resizeColumnToContents(col)
        minimum = _MIN_COL_WIDTHS.get(col, _MIN_COL_WIDTH_DEFAULT)
        if tbl.columnWidth(col) < minimum:
            tbl.setColumnWidth(col, minimum)


def _setup_table(tbl: QtWidgets.QTableWidget) -> None:
    tbl.horizontalHeader().setStretchLastSection(True)
    tbl.horizontalHeader().setDefaultAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        if hasattr(QtCore.Qt.AlignmentFlag, "AlignLeft")
        else QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    tbl.verticalHeader().setVisible(False)
    tbl.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    tbl.setAlternatingRowColors(True)
    tbl.setWordWrap(True)
    tbl.setStyleSheet(
        "QTableWidget { border: 1px solid palette(mid); }"
        "QTableWidget::item { padding: 4px 8px; }"
        "QHeaderView::section { padding: 4px 8px; }"
        "QScrollBar:vertical { width: 0px; }"
        "QScrollBar:horizontal { height: 0px; }"
    )
    tbl.setVerticalScrollBarPolicy(
        QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        if hasattr(QtCore.Qt.ScrollBarPolicy, "ScrollBarAlwaysOff")
        else QtCore.Qt.ScrollBarAlwaysOff)
    tbl.setHorizontalScrollBarPolicy(
        QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        if hasattr(QtCore.Qt.ScrollBarPolicy, "ScrollBarAlwaysOff")
        else QtCore.Qt.ScrollBarAlwaysOff)


def _format_axis_types(axis_types: dict | None) -> str:
    """Format axis_types dict as e.g. 'axis[-1]: bias · axis[-2]: spatial_y'."""
    if not axis_types:
        return "—"
    parts = []
    for idx in sorted(axis_types.keys()):
        atype = axis_types[idx]
        parts.append(f"axis[{idx}]: {atype.value}")
    return " · ".join(parts)


def _ro_item(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable
                  if hasattr(QtCore.Qt.ItemFlag, "ItemIsEditable")
                  else item.flags() & ~QtCore.Qt.ItemIsEditable)
    return item
