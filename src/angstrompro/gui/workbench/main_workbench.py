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
from angstrompro.gui.widgets.task_dashboard import TaskDashboard
from angstrompro.gui.widgets.live_modules_panel import LiveModulesPanel


@register_module
class MainWorkbench(AGuiModule):
    module_id       = "main_workbench"
    display_name    = "AngstromPro Main Workbench"
    category        = "Main Workbench"
    config_sections = None   # show full config tree

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self._counter = 0
        self.resize(1000, 600)
        self._set_app_icon()
        # Restore geometry immediately (before show), defer dock state until after show
        self._restore_geometry()
        QtWidgets.QApplication.instance().aboutToQuit.connect(self._save_layout)

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        from angstrompro.utils.qt_compat import QtCore
        from angstrompro.gui.widgets.config_editor_widget import ConfigEditorWidget
        from angstrompro.gui.dialogs.about_dialog import show_about

        help_menu = self.menuBar().addMenu("Help")
        act_about = help_menu.addAction("About AngstromPro…")
        act_about.triggered.connect(lambda: show_about(self))

        DockArea = QtCore.Qt.DockWidgetArea

        # --- Live Modules panel — central widget ---
        self.setCentralWidget(LiveModulesPanel(self._context))

        # --- Tasks dock (right) ---
        task_demo = TaskDashboard(self._context)
        self._dock_tasks = QtWidgets.QDockWidget("Tasks", self)
        self._dock_tasks.setObjectName("wb_dock_tasks")
        self._dock_tasks.setWidget(task_demo)
        self._dock_tasks.setAllowedAreas(DockArea.LeftDockWidgetArea  | DockArea.RightDockWidgetArea |
                                         DockArea.TopDockWidgetArea   | DockArea.BottomDockWidgetArea)
        self.addDockWidget(DockArea.RightDockWidgetArea, self._dock_tasks)

        # --- Config dock (split below Tasks) ---
        config_editor = ConfigEditorWidget(self._context)
        self._dock_config = QtWidgets.QDockWidget("Config", self)
        self._dock_config.setObjectName("wb_dock_config")
        self._dock_config.setWidget(config_editor)
        self._dock_config.setAllowedAreas(DockArea.LeftDockWidgetArea  | DockArea.RightDockWidgetArea |
                                          DockArea.TopDockWidgetArea   | DockArea.BottomDockWidgetArea)
        self.addDockWidget(DockArea.RightDockWidgetArea, self._dock_config)
        self.splitDockWidget(self._dock_tasks, self._dock_config, QtCore.Qt.Orientation.Vertical)

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        pass

    def on_add_item(self) -> None:
        self._counter += 1
        name = f"main_item_{self._counter}"
        payload = UdsDataStru.from_array(np.zeros(10), name)
        self.workspace.add_item(name=name, payload=payload)

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Layout persistence
    # ------------------------------------------------------------------

    def _apply_default_layout(self) -> None:
        """Set coded default dock proportions — used on first launch."""
        from angstrompro.utils.qt_compat import QtCore
        self.resizeDocks(
            [self._dock_tasks, self._dock_config],
            [300, 300],
            QtCore.Qt.Orientation.Vertical,
        )

    def _restore_geometry(self) -> None:
        from angstrompro.utils.qt_compat import QtCore
        geom = self._context.config.get("gui", "workbench_geometry", "")
        if geom:
            self.restoreGeometry(QtCore.QByteArray.fromBase64(geom.encode()))

    def _restore_dock_state(self) -> None:
        from angstrompro.utils.qt_compat import QtCore
        state = self._context.config.get("gui", "workbench_layout", "")
        if state:
            if self.restoreState(QtCore.QByteArray.fromBase64(state.encode())):
                return
        self._apply_default_layout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Restore dock sizes after the window is fully shown so Qt knows the pixel dimensions
        from angstrompro.utils.qt_compat import QtCore
        QtCore.QTimer.singleShot(0, self._restore_dock_state)

    def _save_layout(self) -> None:
        cfg = self._context.config
        cfg.set("gui", "workbench_geometry",
                self.saveGeometry().toBase64().data().decode())
        cfg.set("gui", "workbench_layout",
                self.saveState().toBase64().data().decode())
        cfg.save_defaults()

    def closeEvent(self, event) -> None:
        super().closeEvent(event)   # hides the window, ignores the event

    def _set_app_icon(self) -> None:
        icon = self._context.icons.get("app_logo")
        if icon.isNull():
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        self.setWindowIcon(icon)

