"""
WorkspaceItemInspector — read-only view of a WorkspaceItem's attributes.

Call set_item(item) to populate; set_item(None) to clear.
Double-clicking any ndarray node opens NdarrayEditorDialog for in-place editing.
Designed to live inside a dock widget in AGuiModule.

Each data type controls what is shown by implementing inspect_fields() on its
WorkspaceData subclass — the inspector is a pure generic renderer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from angstrompro.core.data.uds_data import AxisType
from angstrompro.utils.qt_compat import QtCore, QtWidgets

if TYPE_CHECKING:
    from angstrompro.core.workspaces.workspace_item import WorkspaceItem

_ARRAY_ROLE = QtCore.Qt.ItemDataRole.UserRole if hasattr(
    QtCore.Qt.ItemDataRole, "UserRole") else QtCore.Qt.UserRole

_LABEL_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1 if hasattr(
    QtCore.Qt.ItemDataRole, "UserRole") else QtCore.Qt.UserRole + 1

_AXIS_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2 if hasattr(
    QtCore.Qt.ItemDataRole, "UserRole") else QtCore.Qt.UserRole + 2


class WorkspaceItemInspector(QtWidgets.QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_item = None
        self._setup_ui()
        self.setMinimumSize(QtCore.QSize(0, 0))

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(50, 50)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        form_widget = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(8)

        self._lbl_name   = QtWidgets.QLabel("—")
        self._lbl_type   = QtWidgets.QLabel("—")
        self._lbl_source = QtWidgets.QLabel("—")
        for lbl in (self._lbl_name, self._lbl_type, self._lbl_source):
            lbl.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse if
                hasattr(QtCore.Qt.TextInteractionFlag, "TextSelectableByMouse")
                else QtCore.Qt.TextSelectableByMouse
            )
        form.addRow("Name:",   self._lbl_name)
        form.addRow("Type:",   self._lbl_type)
        form.addRow("Source:", self._lbl_source)
        root.addWidget(form_widget)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Attribute", "Value"])
        self._tree.header().setStretchLastSection(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.itemDoubleClicked.connect(self._on_tree_double_clicked)
        self._tree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu if
            hasattr(QtCore.Qt.ContextMenuPolicy, "CustomContextMenu")
            else QtCore.Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        root.addWidget(self._tree)

        self._hint = QtWidgets.QLabel("Double-click an array node to view/edit values.")
        self._hint.setStyleSheet("color: grey; font-size: 10px;")
        self._hint.hide()
        root.addWidget(self._hint)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_item(self, item: "WorkspaceItem | None") -> None:
        self._current_item = item
        if item is None:
            self._clear()
            return
        self._lbl_name.setText(item.name)
        self._lbl_type.setText(item.type_id)
        self._lbl_source.setText(str(item.source_path) if item.source_path else "—")
        self._tree.clear()
        has_array = self._render(item.payload)
        self._tree.expandToDepth(1)
        self._hint.setVisible(has_array)

    # ------------------------------------------------------------------
    # Generic renderer
    # ------------------------------------------------------------------

    def _render(self, payload) -> bool:
        """Render inspect_fields() output into the tree. Returns True if any arrays."""
        fields = payload.inspect_fields()
        has_array = False
        for node_dict in fields:
            item, arr = self._build_tree_item(self._tree, node_dict)
            if arr:
                has_array = True
        return has_array

    def _build_tree_item(self, parent, node: dict) -> tuple[QtWidgets.QTreeWidgetItem, bool]:
        """Recursively build one QTreeWidgetItem from a node dict.
        Returns (item, has_array)."""
        kind = node.get("kind", "value")
        label = node.get("label", "")
        has_array = False

        if kind == "array":
            array = node["array"]
            summary = f"ndarray  shape={array.shape}  dtype={array.dtype}  ✎"
            item = QtWidgets.QTreeWidgetItem(parent, [label, summary])
            item.setData(0, _ARRAY_ROLE, array)
            item.setData(0, _LABEL_ROLE, label)
            font = item.font(1)
            font.setItalic(True)
            item.setFont(1, font)
            has_array = True
            for child_dict in node.get("children", []):
                _, ch_arr = self._build_tree_item(item, child_dict)
                if ch_arr:
                    has_array = True

        elif kind in ("group", "axis"):
            summary = node.get("summary", "")
            item = QtWidgets.QTreeWidgetItem(parent, [label, summary])
            if kind == "axis":
                ax = node.get("axis")
                if ax is not None:
                    item.setData(0, _AXIS_ROLE, ax)
            for child_dict in node.get("children", []):
                _, ch_arr = self._build_tree_item(item, child_dict)
                if ch_arr:
                    has_array = True

        else:  # "value"
            value = node.get("value", "")
            item = QtWidgets.QTreeWidgetItem(parent, [label, value])

        return item, has_array

    # ------------------------------------------------------------------
    # Double-click → ndarray editor
    # ------------------------------------------------------------------

    def _on_tree_double_clicked(self, tree_item: QtWidgets.QTreeWidgetItem,
                                _column: int) -> None:
        array = tree_item.data(0, _ARRAY_ROLE)
        if not isinstance(array, np.ndarray):
            return
        label = tree_item.data(0, _LABEL_ROLE) or "array"
        from angstrompro.gui.widgets.ndarray_editor_dialog import NdarrayEditorDialog
        dlg = NdarrayEditorDialog(array, label=label, parent=self)
        if dlg.exec():
            if self._current_item is not None:
                self.set_item(self._current_item)

    # ------------------------------------------------------------------
    # Right-click → axis type editor
    # ------------------------------------------------------------------

    def _on_tree_context_menu(self, pos: QtCore.QPoint) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return
        ax = item.data(0, _AXIS_ROLE)
        if ax is None:
            return
        menu = QtWidgets.QMenu(self)
        act = menu.addAction("Edit axis type…")
        if menu.exec(self._tree.viewport().mapToGlobal(pos)) == act:
            self._edit_axis_type(ax)

    def _edit_axis_type(self, ax) -> None:
        type_names = [t.value for t in AxisType]
        current    = ax.axis_type.value
        current_idx = type_names.index(current) if current in type_names else 0
        chosen, ok = QtWidgets.QInputDialog.getItem(
            self, "Edit Axis Type",
            f"Axis:  {ax.label}\nSelect type:",
            type_names, current_idx, editable=False,
        )
        if not ok:
            return
        ax.axis_type = AxisType(chosen)
        if self._current_item is not None:
            self.set_item(self._current_item)

    # ------------------------------------------------------------------

    def _clear(self) -> None:
        self._lbl_name.setText("—")
        self._lbl_type.setText("—")
        self._lbl_source.setText("—")
        self._tree.clear()
        self._hint.hide()
