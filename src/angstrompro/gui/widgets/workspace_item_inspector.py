"""
WorkspaceItemInspector — read-only view of a WorkspaceItem's attributes.

Call set_item(item) to populate; set_item(None) to clear.
Double-clicking any ndarray node opens NdarrayEditorDialog for in-place editing.
Designed to live inside a dock widget in AGuiModule.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from angstrompro.utils.qt_compat import QtCore, QtWidgets

if TYPE_CHECKING:
    from angstrompro.core.workspaces.workspace_item import WorkspaceItem

_ARRAY_ROLE = QtCore.Qt.ItemDataRole.UserRole if hasattr(
    QtCore.Qt.ItemDataRole, "UserRole") else QtCore.Qt.UserRole

_LABEL_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1 if hasattr(
    QtCore.Qt.ItemDataRole, "UserRole") else QtCore.Qt.UserRole + 1


class WorkspaceItemInspector(QtWidgets.QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_item = None
        self._setup_ui()
        # Prevent content width from propagating as window minimum size
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

        # -- metadata form --
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

        # -- payload tree --
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Attribute", "Value"])
        self._tree.header().setStretchLastSection(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.itemDoubleClicked.connect(self._on_tree_double_clicked)
        root.addWidget(self._tree)

        # hint label
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
        has_array = self._populate_payload(item.payload)
        self._tree.expandToDepth(1)
        self._hint.setVisible(has_array)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear(self) -> None:
        self._lbl_name.setText("—")
        self._lbl_type.setText("—")
        self._lbl_source.setText("—")
        self._tree.clear()
        self._hint.hide()

    def _populate_payload(self, payload) -> bool:
        """Populate the tree. Returns True if any ndarray nodes were added."""
        if payload.type_id == "uds":
            return self._populate_uds(payload)
        return self._populate_generic(payload)

    def _make_array_node(self, parent, label: str, array: np.ndarray) -> QtWidgets.QTreeWidgetItem:
        """Create a tree node for an ndarray, storing the array ref for double-click editing."""
        summary = f"ndarray  shape={array.shape}  dtype={array.dtype}  ✎"
        node = QtWidgets.QTreeWidgetItem(parent, [label, summary])
        node.setData(0, _ARRAY_ROLE, array)
        node.setData(0, _LABEL_ROLE, label)
        # italic hint that it's editable
        font = node.font(1)
        font.setItalic(True)
        node.setFont(1, font)
        return node

    def _populate_uds(self, uds) -> bool:
        has_array = False

        # main data array
        self._make_array_node(self._tree, "data", uds.data)
        has_array = True

        # shape / dtype / ndim as plain children under data
        data_node = self._tree.topLevelItem(0)
        QtWidgets.QTreeWidgetItem(data_node, ["shape", str(uds.data.shape)])
        QtWidgets.QTreeWidgetItem(data_node, ["dtype", str(uds.data.dtype)])
        QtWidgets.QTreeWidgetItem(data_node, ["ndim",  str(uds.data.ndim)])

        # axes
        axes_node = QtWidgets.QTreeWidgetItem(self._tree,
            ["axes", f"{len(uds.axes)} axis/axes"])
        for i, ax in enumerate(uds.axes):
            rng = (f"{ax.values[0]:.4g} … {ax.values[-1]:.4g}"
                   if len(ax.values) > 0 else "empty")
            ax_node = QtWidgets.QTreeWidgetItem(axes_node,
                [f"[{i}]  {ax.label}", f"{len(ax.values)} pts   {rng}  {ax.units}"])
            self._make_array_node(ax_node, "values", ax.values)
            has_array = True
            if ax.ticks:
                ticks_node = QtWidgets.QTreeWidgetItem(ax_node,
                    ["ticks", f"{len(ax.ticks)}"])
                for pos, lbl in ax.ticks.items():
                    QtWidgets.QTreeWidgetItem(ticks_node, [f"{pos:.4g}", lbl])

        # info dict
        info_node = QtWidgets.QTreeWidgetItem(self._tree,
            ["info", f"{len(uds.info)} entries"])
        for k, v in uds.info.items():
            QtWidgets.QTreeWidgetItem(info_node, [str(k), str(v)])

        # proc_history
        ph_node = QtWidgets.QTreeWidgetItem(self._tree,
            ["proc_history", f"{len(uds.proc_history)} steps"])
        for i, rec in enumerate(uds.proc_history):
            step_node = QtWidgets.QTreeWidgetItem(ph_node, [f"[{i}]", rec.step])
            if rec.params:
                for k, v in rec.params.items():
                    QtWidgets.QTreeWidgetItem(step_node, [str(k), str(v)])
            if rec.input_item_names:
                QtWidgets.QTreeWidgetItem(step_node,
                    ["inputs", ", ".join(rec.input_item_names)])

        # landmarks
        if uds.landmarks:
            lm_node = QtWidgets.QTreeWidgetItem(self._tree,
                ["landmarks", f"{len(uds.landmarks)} points"])
            for coords, lbl in uds.landmarks.items():
                key = "(" + ", ".join(f"{c:.4g}" for c in coords) + ")"
                QtWidgets.QTreeWidgetItem(lm_node, [key, lbl])

        return has_array

    def _populate_generic(self, payload) -> bool:
        """Fallback: show all public non-callable attributes."""
        has_array = False
        for attr in vars(payload):
            if attr.startswith("_"):
                continue
            val = getattr(payload, attr)
            if callable(val):
                continue
            if isinstance(val, np.ndarray):
                self._make_array_node(self._tree, attr, val)
                has_array = True
            else:
                QtWidgets.QTreeWidgetItem(self._tree, [attr, repr(val)])
        return has_array

    # ------------------------------------------------------------------
    # Double-click → editor
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
            # array edited in-place — refresh inspector to show updated summary
            if self._current_item is not None:
                self.set_item(self._current_item)
