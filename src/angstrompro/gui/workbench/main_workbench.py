# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:30:33 2026

@author: jiahaoYan
"""

import copy
import numpy as np
from angstrompro.utils.qt_compat import QtCore, QtWidgets
from angstrompro.app.context import AppContext
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.widgets.task_dashboard import TaskDashboard
from angstrompro.gui.widgets.live_modules_panel import LiveModulesPanel
from angstrompro.gui.widgets.preferences import PrefSection, PrefItem, PreferencesPanel
import angstrompro.gui.widgets.preferences.widgets  # registers custom widget types
import angstrompro.gui.widgets.channel_manager_widget  # registers channel_manager widget type


@register_module
class MainWorkbench(AGuiModule):
    module_id       = "main_workbench"
    display_name    = "AngstromPro Main Workbench"
    category        = "Main Workbench"
    config_sections = None

    _global_preferences_schema = [
        PrefSection("Appearance", "palette", [
            PrefItem("appearance.theme",     "Theme",     "dropdown",
                     "Colour theme for the application",
                     kwargs={"choices": ["dark", "light", "auto"]}),
            PrefItem("appearance.font_size", "Font size", "number",
                     "Application-wide font size in points"),
            PrefItem("appearance.icon_size", "Icon size", "number",
                     "Toolbar / button icon size in px"),
            PrefItem("appearance.font_family", "Font family", "text",
                     "Font family name; leave blank for system default"),
            PrefItem("appearance.accent_color", "Accent color", "text",
                     "Hex accent colour e.g. #4fc3f7; leave blank for theme default"),
        ]),
        PrefSection("Plugins", "plug", [
            PrefItem("plugins.path_plugins", "", "plugin_list",
                     full_width=True),
        ]),
        PrefSection("Files", "folder-open", [
            PrefItem("io.default_open_dir", "Default open folder", "text",
                     "Starting directory for file-open dialogs"),
            PrefItem("io.default_save_dir", "Default save folder", "text",
                     "Starting directory for file-save dialogs"),
        ]),
        PrefSection("Channels", "settings", [
            PrefItem("", "Channel mappings", "channel_manager",
                     "Configure which channels are loaded for each file format",
                     full_width=True, expandable=True),
        ]),
    ]

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

    def _on_preferences(self) -> None:
        cfg = self._context.config

        # Assemble a flat snapshot of the global sections we expose
        snapshot = {
            "appearance": copy.deepcopy(cfg.get_group("appearance")),
            "io":         copy.deepcopy(cfg.get_group("io")),
            "plugins":    copy.deepcopy(cfg.get_group("plugins")),
        }

        def _apply(new_cfg: dict) -> None:
            for section, values in new_cfg.items():
                for key, val in values.items():
                    cfg.set(section, key, val)
            # Re-apply appearance live
            from angstrompro.gui.appearance.theme_manager import ThemeManager
            ThemeManager(cfg.get_group("appearance")).apply()

        def _save(new_cfg: dict) -> None:
            _apply(new_cfg)
            cfg.save_defaults()

        def _reset() -> None:
            from angstrompro.core.configs.defaults import DEFAULTS
            _apply({
                "appearance": copy.deepcopy(DEFAULTS.get("appearance", {})),
                "io":         copy.deepcopy(DEFAULTS.get("io", {})),
                "plugins":    copy.deepcopy(DEFAULTS.get("plugins", {})),
            })

        from angstrompro.app.user_data_folder import get_qsettings
        _qs_key = "prefs_size/main_workbench"

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dlg.setWindowTitle("Preferences — AngstromPro")
        qs = get_qsettings()
        dlg.resize(qs.value(_qs_key, QtCore.QSize(820, 500)))
        dlg.finished.connect(lambda: get_qsettings().setValue(_qs_key, dlg.size()))
        layout = QtWidgets.QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(PreferencesPanel(
            module_name="AngstromPro",
            schema=self._global_preferences_schema,
            config=snapshot,
            on_apply=_apply,
            on_save_as_default=_save,
            on_reset=_reset,
            context=self._context,
            parent=dlg,
        ))
        dlg.show()

    def build_ui(self) -> None:
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

        # --- Dev: Config editor — hidden dock, toggled via Ctrl+Shift+D ---
        self._dock_config = None
        act_dev = QtWidgets.QAction(self)
        act_dev.setShortcut("Ctrl+Shift+D")
        act_dev.triggered.connect(self._toggle_config_editor)
        self.addAction(act_dev)

    def _toggle_config_editor(self) -> None:
        if self._dock_config is None:
            from angstrompro.gui.widgets.config_editor_widget import ConfigEditorWidget
            editor = ConfigEditorWidget(self._context)
            self._dock_config = QtWidgets.QDockWidget("Config [dev]", self)
            self._dock_config.setObjectName("wb_dock_config")
            self._dock_config.setWidget(editor)
            self._dock_config.setAllowedAreas(
                QtCore.Qt.DockWidgetArea.LeftDockWidgetArea  |
                QtCore.Qt.DockWidgetArea.RightDockWidgetArea |
                QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
            self._dock_config.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
            self._dock_config.destroyed.connect(lambda: setattr(self, "_dock_config", None))
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self._dock_config)
        else:
            self._dock_config.setVisible(not self._dock_config.isVisible())

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
        self.resizeDocks([self._dock_tasks], [300], QtCore.Qt.Orientation.Vertical)

    def _restore_geometry(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        geom = qs.value("workbench/geometry")
        if geom:
            self.restoreGeometry(geom)

    def _restore_dock_state(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        state = qs.value("workbench/layout")
        if state and self.restoreState(state):
            return
        self._apply_default_layout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._restore_dock_state)

    def _save_layout(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        qs.setValue("workbench/geometry", self.saveGeometry())
        qs.setValue("workbench/layout",   self.saveState())

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

