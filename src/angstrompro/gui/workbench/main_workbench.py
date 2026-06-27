# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:30:33 2026

@author: jiahaoYan
"""

import numpy as np
from angstrompro.utils.qt_compat import QtWidgets
from angstrompro.app.context import AppContext
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.task_demo import DemoWindow


@register_module
class MainWorkbench(AGuiModule):
    module_id    = "main_workbench"
    display_name = "AngstromPro Main Workbench"
    category     = "Main Workbench"

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self._counter = 0
        self.resize(1000, 600)
        self._set_app_icon()
        context.module_manager.module_added.connect(lambda _: self._refresh_module_list())
        context.module_manager.module_removed.connect(lambda _: self._refresh_module_list())

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root_layout = QtWidgets.QHBoxLayout(central)

        # --- live modules panel ---
        modules_panel = QtWidgets.QWidget()
        modules_layout = QtWidgets.QVBoxLayout(modules_panel)

        modules_layout.addWidget(QtWidgets.QLabel("Live Modules:"))
        self._module_list = QtWidgets.QListWidget()
        modules_layout.addWidget(self._module_list)

        btn_create = QtWidgets.QPushButton("Add Test Bench")
        btn_create.clicked.connect(self._create_module)
        modules_layout.addWidget(btn_create)

        btn_show = QtWidgets.QPushButton("Show Selected")
        btn_show.clicked.connect(self._show_module)
        modules_layout.addWidget(btn_show)

        btn_remove = QtWidgets.QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._remove_module)
        modules_layout.addWidget(btn_remove)

        task_demo = DemoWindow(self._context)

        root_layout.addWidget(modules_panel)
        root_layout.addWidget(task_demo)
        self.setCentralWidget(central)

        self._refresh_module_list()

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        pass

    def on_add_item(self) -> None:
        self._counter += 1
        name = f"main_item_{self._counter}"
        payload = UdsDataStru.from_array(np.zeros(10), name)
        self.workspace.add_item(name=name, payload=payload)

    # ------------------------------------------------------------------

    def _set_app_icon(self) -> None:
        icon = self._context.icons.get("app_logo")
        if icon.isNull():
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        self.setWindowIcon(icon)

    def _refresh_module_list(self) -> None:
        self._module_list.clear()
        for inst in self._context.module_manager.list_instances():
            if inst.instance_id != self.instance_id:
                self._module_list.addItem(inst.instance_id)

    def _selected_instance_id(self) -> str | None:
        item = self._module_list.currentItem()
        return item.text() if item else None

    def _instance_by_id(self, instance_id: str):
        for inst in self._context.module_manager.list_instances():
            if inst.instance_id == instance_id:
                return inst
        return None

    def _create_module(self) -> None:
        import angstrompro.gui.modules.child_test_bench  # noqa: F401 — triggers @register_module
        inst = self._context.module_manager.create("test_bench", self._context)
        inst.show()

    def _show_module(self) -> None:
        instance_id = self._selected_instance_id()
        inst = self._instance_by_id(instance_id) if instance_id else None
        if inst:
            inst.show()
            inst.raise_()

    def _remove_module(self) -> None:
        instance_id = self._selected_instance_id()
        inst = self._instance_by_id(instance_id) if instance_id else None
        if inst:
            self._context.module_manager.remove(inst)
