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
from angstrompro.gui.transfer_target_editor import TransferTargetEditor
from angstrompro.gui.config_editor_widget import ConfigEditorWidget
from angstrompro.gui.task_demo import DemoWindow
from angstrompro.gui.appearance import IconManager, ThemeManager


@register_module
class MainWorkbench(AGuiModule):
    module_id    = "main_workbench"
    display_name = "AngstromPro Main Workbench"

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self._counter = 0
        self.resize(1000, 600)
        self._set_app_icon()

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root_layout = QtWidgets.QHBoxLayout(central)

        # --- left panel: workspace items ---
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)

        left_layout.addWidget(QtWidgets.QLabel("Main Workspace Items:"))
        self._item_list = QtWidgets.QListWidget()
        left_layout.addWidget(self._item_list)

        btn_add = QtWidgets.QPushButton("Add Item")
        btn_add.clicked.connect(self._add_item)
        left_layout.addWidget(btn_add)

        btn_remove = QtWidgets.QPushButton("Remove Selected Item")
        btn_remove.clicked.connect(self._remove_item)
        left_layout.addWidget(btn_remove)

        btn_send = QtWidgets.QPushButton("Send Selected Item to Selected Child")
        btn_send.clicked.connect(self._send_item)
        left_layout.addWidget(btn_send)

        # --- right panel: child benches ---
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        right_layout.addWidget(QtWidgets.QLabel("Child Benches:"))
        self._child_list = QtWidgets.QListWidget()
        right_layout.addWidget(self._child_list)

        btn_new_child = QtWidgets.QPushButton("New Child Bench")
        btn_new_child.clicked.connect(self._new_child)
        right_layout.addWidget(btn_new_child)

        btn_show_child = QtWidgets.QPushButton("Show Selected Child")
        btn_show_child.clicked.connect(self._show_child)
        right_layout.addWidget(btn_show_child)

        btn_close_child = QtWidgets.QPushButton("Close Selected Child")
        btn_close_child.clicked.connect(self._close_child)
        right_layout.addWidget(btn_close_child)

        btn_targets = QtWidgets.QPushButton("Edit Transfer Targets")
        btn_targets.clicked.connect(self._open_target_editor)
        right_layout.addWidget(btn_targets)
        
        task_demo = DemoWindow()
        self._tabs = QtWidgets.QTabWidget()
        self._config_editor = ConfigEditorWidget(self._context, parent=self)
        self._tabs.addTab(self._config_editor, "Config")

        root_layout.addWidget(left)
        root_layout.addWidget(right)
        root_layout.addWidget(task_demo)
        #root_layout.addWidget(self._tabs)
        self.setCentralWidget(central)

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        pass

    def on_workspace_changed(self) -> None:
        self._refresh_item_list()

    # ------------------------------------------------------------------

    def _set_app_icon(self) -> None:
        icon = self._context.icons.get("app_logo")
        if icon.isNull():
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        self.setWindowIcon(icon)

    def _refresh_item_list(self) -> None:
        self._item_list.clear()
        for name in self.workspace.list_names():
            self._item_list.addItem(name)

    def _refresh_child_list(self) -> None:
        self._child_list.clear()
        for inst in self._context.module_manager.list_instances("child_bench"):
            self._child_list.addItem(inst.instance_id)

    def _selected_item_name(self) -> str | None:
        item = self._item_list.currentItem()
        return item.text() if item else None

    def _selected_child_id(self) -> str | None:
        item = self._child_list.currentItem()
        return item.text() if item else None

    def _child_by_id(self, instance_id: str):
        for inst in self._context.module_manager.list_instances("child_bench"):
            if inst.instance_id == instance_id:
                return inst
        return None

    def _add_item(self) -> None:
        self._counter += 1
        name = f"main_item_{self._counter}"
        payload = UdsDataStru.from_array(np.zeros(10), name)
        self.workspace.add_item(name=name, payload=payload)

    def _remove_item(self) -> None:
        name = self._selected_item_name()
        if name:
            self.workspace.remove_item(name)

    def _send_item(self) -> None:
        name = self._selected_item_name()
        child_id = self._selected_child_id()
        if not name or not child_id:
            return
        child = self._child_by_id(child_id)
        if not child:
            return
        self._context.workspace_manager.transfer_item(
            src_workspace_id=self.workspace.workspace_id,
            dst_workspace_id=child.workspace.workspace_id,
            item_name=name,
        )
        print(f"[Main] sent '{name}' to '{child_id}'")

    def _new_child(self) -> None:
        import angstrompro.gui.child_test_bench  # noqa: F401 — triggers @register_module
        child = self._context.module_manager.create("child_bench", self._context)
        self._refresh_child_list()
        child.show()

    def _show_child(self) -> None:
        child_id = self._selected_child_id()
        child = self._child_by_id(child_id) if child_id else None
        if child:
            child.show()
            child.raise_()

    def _close_child(self) -> None:
        child_id = self._selected_child_id()
        child = self._child_by_id(child_id) if child_id else None
        if child:
            self._context.module_manager.close(child)
            self._refresh_child_list()

    def _open_target_editor(self) -> None:
        editor = TransferTargetEditor(self._context, parent=self)
        editor.exec()
