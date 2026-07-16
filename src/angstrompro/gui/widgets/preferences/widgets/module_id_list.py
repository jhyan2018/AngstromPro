# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

ModuleIdListWidget — editable list of module type ids (module_id) for
app-level per-type preferences (hide workspace dock, exclude as send
target, …).  New entries are added from a dropdown of registered module
types so ids cannot be mistyped; the user config value REPLACES the
hardcoded default wholesale, so emptying the list is a valid override.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets


class ModuleIdListWidget(QtWidgets.QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._context = None
        self._choices: list[tuple[str, str]] = []   # (module_id, display_name)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._list = QtWidgets.QListWidget()
        self._list.setMinimumHeight(70)
        self._list.setMaximumHeight(110)
        lay.addWidget(self._list, stretch=1)

        col = QtWidgets.QVBoxLayout()
        self._combo = QtWidgets.QComboBox()
        self._combo.setMinimumWidth(150)
        col.addWidget(self._combo)
        b_add = QtWidgets.QPushButton("Add")
        b_add.clicked.connect(self._add)
        col.addWidget(b_add)
        b_rm = QtWidgets.QPushButton("Remove")
        b_rm.clicked.connect(self._remove)
        col.addWidget(b_rm)
        col.addStretch()
        lay.addLayout(col)

    # ── PreferencesPanel contract ───────────────────────────────────────────

    def set_context(self, context) -> None:
        self._context = context
        self._choices = sorted(
            [(cls.module_id, getattr(cls, "display_name", cls.module_id))
             for cls in context.module_manager.list_all()
             if cls.module_id != "main_workbench"],
            key=lambda x: x[1].lower(),
        )
        self._refresh_combo()

    def get_value(self) -> list:
        return [self._list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
                for i in range(self._list.count())]

    def set_value(self, v) -> None:
        self._list.clear()
        for mid in (v or []):
            self._append(str(mid))
        self._refresh_combo()

    # ── internals ───────────────────────────────────────────────────────────

    def _display_for(self, mid: str) -> str:
        for m, dname in self._choices:
            if m == mid:
                return f"{dname}  ({mid})"
        return mid   # unknown/plugin id not currently registered — keep as-is

    def _append(self, mid: str) -> None:
        item = QtWidgets.QListWidgetItem(self._display_for(mid))
        item.setData(QtCore.Qt.ItemDataRole.UserRole, mid)
        self._list.addItem(item)

    def _refresh_combo(self) -> None:
        used = set(self.get_value())
        self._combo.clear()
        for mid, dname in self._choices:
            if mid not in used:
                self._combo.addItem(f"{dname}  ({mid})", mid)
        if self._combo.count() == 0:
            self._combo.addItem("(no more modules)", "")

    def _add(self) -> None:
        mid = self._combo.currentData()
        if mid:
            self._append(mid)
            self._refresh_combo()

    def _remove(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)
            self._refresh_combo()
