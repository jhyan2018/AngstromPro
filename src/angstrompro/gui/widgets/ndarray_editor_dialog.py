"""
NdarrayEditorDialog — view and edit a numpy ndarray in a table.

Supports 1D, 2D, and ND arrays (slice navigation for dims beyond 2).
Edits are written back in-place on OK; Cancel discards all changes.
"""

from __future__ import annotations

import numpy as np

from angstrompro.utils.qt_compat import QtCore, QtWidgets

_USER_ROLE = QtCore.Qt.ItemDataRole.UserRole if hasattr(
    QtCore.Qt.ItemDataRole, "UserRole") else QtCore.Qt.UserRole


class NdarrayEditorDialog(QtWidgets.QDialog):

    def __init__(self, array: np.ndarray, label: str = "array",
                 parent=None) -> None:
        super().__init__(parent)
        self._array   = array
        self._label   = label
        self._pending = np.array(array, dtype=array.dtype, copy=True)
        self._slice_indices: list[int] = [0] * max(0, array.ndim - 2)

        self.setWindowTitle(f"Edit array — {label}  shape={array.shape}  dtype={array.dtype}")
        self.resize(640, 480)
        self._setup_ui()
        self._refresh_table()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)

        # slice selectors (only for ndim > 2)
        if self._array.ndim > 2:
            slice_bar = QtWidgets.QWidget()
            hbox = QtWidgets.QHBoxLayout(slice_bar)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.addWidget(QtWidgets.QLabel("Slice:"))
            self._spinboxes: list[QtWidgets.QSpinBox] = []
            for dim in range(self._array.ndim - 2):
                hbox.addWidget(QtWidgets.QLabel(f"dim[{dim}]:"))
                sb = QtWidgets.QSpinBox()
                sb.setRange(0, self._array.shape[dim] - 1)
                sb.setValue(0)
                sb.valueChanged.connect(self._on_slice_changed)
                hbox.addWidget(sb)
                self._spinboxes.append(sb)
            hbox.addStretch()
            root.addWidget(slice_bar)
        else:
            self._spinboxes = []

        # table
        self._table = QtWidgets.QTableWidget()
        self._table.currentCellChanged.connect(self._on_cell_selected)
        root.addWidget(self._table)

        # status bar
        self._status = QtWidgets.QLabel("")
        self._status.setStyleSheet("color: grey; font-size: 11px;")
        root.addWidget(self._status)

        # buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Slice navigation
    # ------------------------------------------------------------------

    def _current_slice(self) -> tuple:
        """Build the index tuple for the current 2D slice."""
        outer = tuple(sb.value() for sb in self._spinboxes)
        return outer + (slice(None), slice(None)) if self._array.ndim > 2 else (
            (slice(None),) if self._array.ndim == 1 else (slice(None), slice(None))
        )

    def _get_2d_view(self) -> np.ndarray:
        sliced = self._pending[self._current_slice()]
        if sliced.ndim == 1:
            return sliced.reshape(-1, 1)
        return sliced  # 2D

    def _on_slice_changed(self) -> None:
        self._flush_table_to_pending()
        for dim, sb in enumerate(self._spinboxes):
            self._slice_indices[dim] = sb.value()
        self._refresh_table()

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        view = self._get_2d_view()
        nrows, ncols = view.shape

        self._table.blockSignals(True)
        self._table.setRowCount(nrows)
        self._table.setColumnCount(ncols)

        # headers
        if self._array.ndim == 1:
            self._table.setHorizontalHeaderLabels(["value"])
        else:
            self._table.setHorizontalHeaderLabels([str(c) for c in range(ncols)])
        self._table.setVerticalHeaderLabels([str(r) for r in range(nrows)])

        for r in range(nrows):
            for c in range(ncols):
                val = view[r, c]
                self._table.setItem(r, c, QtWidgets.QTableWidgetItem(self._fmt(val)))

        self._table.blockSignals(False)
        self._table.resizeColumnsToContents()

    def _fmt(self, val) -> str:
        if np.issubdtype(self._array.dtype, np.complexfloating):
            return f"{val.real}+{val.imag}j"
        if np.issubdtype(self._array.dtype, np.floating):
            return f"{val:.10g}"
        return str(val)

    # ------------------------------------------------------------------
    # Flush table edits → _pending
    # ------------------------------------------------------------------

    def _flush_table_to_pending(self) -> bool:
        """Parse all visible table cells into _pending. Returns False on error."""
        view = self._get_2d_view()
        nrows, ncols = view.shape
        errors = []
        new_vals = np.empty((nrows, ncols), dtype=self._array.dtype)
        for r in range(nrows):
            for c in range(ncols):
                cell = self._table.item(r, c)
                text = cell.text().strip() if cell else ""
                try:
                    new_vals[r, c] = self._parse(text)
                except (ValueError, TypeError):
                    errors.append(f"[{r},{c}] = {text!r}")
        if errors:
            QtWidgets.QMessageBox.warning(
                self, "Parse error",
                "Could not convert the following cells to "
                f"{self._array.dtype}:\n" + "\n".join(errors[:10])
            )
            return False
        view[:] = new_vals
        return True

    def _parse(self, text: str):
        dtype = self._array.dtype
        if np.issubdtype(dtype, np.complexfloating):
            return complex(text.replace(" ", ""))
        if np.issubdtype(dtype, np.floating):
            return float(text)
        if np.issubdtype(dtype, np.integer):
            return int(text)
        return dtype.type(text)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _on_cell_selected(self, row, col, _pr, _pc) -> None:
        if row < 0 or col < 0:
            return
        outer = tuple(sb.value() for sb in self._spinboxes)
        coords = outer + (row, col) if self._array.ndim > 2 else (
            (row,) if self._array.ndim == 1 else (row, col)
        )
        coord_str = ", ".join(str(i) for i in coords)
        self._status.setText(f"  [{coord_str}]  =  {self._fmt(self._pending[coords])}")

    def _on_ok(self) -> None:
        if not self._flush_table_to_pending():
            return
        self._array[:] = self._pending
        self.accept()
