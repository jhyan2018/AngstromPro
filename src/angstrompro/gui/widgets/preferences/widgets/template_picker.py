# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

Template picker — registered as preference widget type "template_picker".
Shows a combo box populated from tmgr.list_templates() at build time.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtWidgets


class TemplatePickerWidget(QtWidgets.QWidget):
    """
    Combo-box preference widget listing available scene templates.

    Protocol
    --------
    get_value() → str   (template name, or "" for none)
    set_value(v: str)
    """

    def __init__(self, value: str = "", parent=None, **kwargs):
        super().__init__(parent)
        self._build_ui()
        self.set_value(value)

    def _build_ui(self) -> None:
        from angstrompro.gui.widgets.curve_stack import template_manager as tmgr

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._combo = QtWidgets.QComboBox()
        self._combo.setMinimumWidth(160)
        self._combo.addItem("(none)", "")
        for name in tmgr.list_templates():
            self._combo.addItem(name, name)

        btn_refresh = QtWidgets.QPushButton("Refresh")
        btn_refresh.setToolTip("Refresh template list")
        btn_refresh.clicked.connect(self._refresh)

        layout.addWidget(self._combo)
        layout.addWidget(btn_refresh)
        layout.addStretch()

    def _refresh(self) -> None:
        from angstrompro.gui.widgets.curve_stack import template_manager as tmgr
        current = self.get_value()
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("(none)", "")
        for name in tmgr.list_templates():
            self._combo.addItem(name, name)
        self._combo.blockSignals(False)
        self.set_value(current)

    def get_value(self) -> str:
        return self._combo.currentData() or ""

    def set_value(self, v: str) -> None:
        idx = self._combo.findData(v or "")
        self._combo.setCurrentIndex(idx if idx >= 0 else 0)
