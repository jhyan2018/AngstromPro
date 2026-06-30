"""Colormap picker — registered as widget type "colormap_picker"."""
from __future__ import annotations

import matplotlib as mpl

from angstrompro.utils.qt_compat import QtWidgets
from angstrompro.gui.widgets.color_bar import ColorBar


class ColormapPickerWidget(QtWidgets.QWidget):
    """
    Full-width widget for editing the ordered palette list.

    Protocol
    --------
    get_value() → list[str]
    set_value(v: list[str])
    """

    def __init__(self, value: list | None = None, parent=None, **kwargs):
        super().__init__(parent)
        self._build_ui()
        self.set_value(value or [])

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        from angstrompro.gui.resources.colormaps import register_all
        register_all()

        original = set(mpl.pyplot.colormaps())   # before register_all pollutes
        all_now  = set(mpl.colormaps)
        self._builtin_list    = sorted(original)
        self._customized_list = sorted(all_now - original)

        # ── available side ─────────────────────────────────────────────
        self._cb_type = QtWidgets.QComboBox()
        self._cb_type.addItems(["Built-in", "Customized"])
        self._cb_type.currentIndexChanged.connect(self._on_type_changed)

        self._lw_available = QtWidgets.QListWidget()
        self._lw_available.setMaximumWidth(200)
        self._lw_available.addItems(self._builtin_list)
        self._lw_available.itemSelectionChanged.connect(self._on_available_sel)

        self._bar_all = ColorBar()

        avail_col = QtWidgets.QVBoxLayout()
        avail_col.setContentsMargins(0, 0, 0, 0)
        avail_col.addWidget(self._cb_type)
        avail_col.addWidget(self._lw_available)

        # ── buttons ────────────────────────────────────────────────────
        btn_add    = QtWidgets.QPushButton("Add →")
        btn_up     = QtWidgets.QPushButton("Move up")
        btn_down   = QtWidgets.QPushButton("Move down")
        btn_remove = QtWidgets.QPushButton("Remove ←")
        btn_clip   = QtWidgets.QPushButton("Copy to clipboard")
        btn_add.clicked.connect(self._add)
        btn_up.clicked.connect(self._move_up)
        btn_down.clicked.connect(self._move_down)
        btn_remove.clicked.connect(self._remove)
        btn_clip.clicked.connect(self._clip)

        btn_col = QtWidgets.QVBoxLayout()
        btn_col.setContentsMargins(4, 0, 4, 0)
        btn_col.addStretch()
        for b in (btn_add, btn_up, btn_down, btn_remove, btn_clip):
            btn_col.addWidget(b)
        btn_col.addStretch()

        # ── chosen side ────────────────────────────────────────────────
        self._lw_chosen = QtWidgets.QListWidget()
        self._lw_chosen.setMaximumWidth(200)
        self._lw_chosen.itemSelectionChanged.connect(self._on_chosen_sel)

        self._bar_chosen = ColorBar()

        chosen_col = QtWidgets.QVBoxLayout()
        chosen_col.setContentsMargins(0, 0, 0, 0)
        lbl = QtWidgets.QLabel("Chosen palette")
        lbl.setObjectName("pref_row_desc")
        chosen_col.addWidget(lbl)
        chosen_col.addWidget(self._lw_chosen)

        # ── assemble ───────────────────────────────────────────────────
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(8, 8, 8, 8)
        row.addLayout(avail_col)
        row.addWidget(self._bar_all)
        row.addLayout(btn_col)
        row.addLayout(chosen_col)
        row.addWidget(self._bar_chosen)

    # ------------------------------------------------------------------
    # Protocol
    # ------------------------------------------------------------------

    def get_value(self) -> list:
        return [self._lw_chosen.item(i).text()
                for i in range(self._lw_chosen.count())]

    def set_value(self, value: list) -> None:
        self._lw_chosen.clear()
        self._lw_chosen.addItems(value or [])
        if self._lw_chosen.count():
            self._lw_chosen.setCurrentRow(0)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_type_changed(self, idx: int) -> None:
        self._lw_available.clear()
        self._lw_available.addItems(
            self._builtin_list if idx == 0 else self._customized_list
        )
        if self._lw_available.count():
            self._lw_available.setCurrentRow(0)

    def _on_available_sel(self) -> None:
        item = self._lw_available.currentItem()
        if item:
            self._bar_all.setColorMap(item.text())

    def _on_chosen_sel(self) -> None:
        item = self._lw_chosen.currentItem()
        if item:
            self._bar_chosen.setColorMap(item.text())

    def _add(self) -> None:
        item = self._lw_available.currentItem()
        if not item:
            return
        name = item.text()
        existing = [self._lw_chosen.item(i).text()
                    for i in range(self._lw_chosen.count())]
        if name not in existing:
            self._lw_chosen.addItem(name)

    def _remove(self) -> None:
        row = self._lw_chosen.currentRow()
        if self._lw_chosen.count() > 1:
            self._lw_chosen.takeItem(row)

    def _move_up(self) -> None:
        row = self._lw_chosen.currentRow()
        if row > 0:
            a = self._lw_chosen.item(row - 1).text()
            b = self._lw_chosen.item(row).text()
            self._lw_chosen.item(row - 1).setText(b)
            self._lw_chosen.item(row).setText(a)
            self._lw_chosen.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self._lw_chosen.currentRow()
        if row < self._lw_chosen.count() - 1:
            a = self._lw_chosen.item(row).text()
            b = self._lw_chosen.item(row + 1).text()
            self._lw_chosen.item(row).setText(b)
            self._lw_chosen.item(row + 1).setText(a)
            self._lw_chosen.setCurrentRow(row + 1)

    def _clip(self) -> None:
        self._bar_chosen.copyToClipboard()
