# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 13:20:46 2026

@author: jiahaoYan
"""

from __future__ import annotations
import numpy as np
from angstrompro.app.context import AppContext
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.utils.qt_compat import QtWidgets


@register_module
class ChildTestBench(AGuiModule):
    module_id    = "test_bench"
    display_name = "Test Bench"
    category     = "Test"

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self._counter = 0
        self.resize(600, 400)
        self.setWindowTitle(f"Test Bench — {self.instance_id}")

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        pass

    def on_add_item(self) -> None:
        self._counter += 1
        name = f"{self.instance_id}_item_{self._counter}"
        payload = UdsDataStru.from_array(np.zeros(10), name)
        self.workspace.add_item(name=name, payload=payload)
