# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:30:33 2026

@author: jiahaoYan
"""

import copy
import logging
from angstrompro.utils.qt_compat import QtCore, QtWidgets, Action
from angstrompro.app.context import AppContext
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.widgets.task_dashboard import TaskDashboard
from angstrompro.gui.widgets.log_panel import LogPanel
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
    staged_labels   = ["[0]", "[1]"]
    clearable_slots = {0, 1}

    _global_preferences_schema = [
        PrefSection("General", "settings", [
            PrefItem("app.log_level", "Log panel level", "dropdown",
                     "Minimum severity shown in the log panel",
                     kwargs={"choices": ["WARNING", "ERROR", "INFO", "DEBUG"]}),
            PrefItem("app.delete_after_send", "Delete after send", "checkbox",
                     "Remove the workspace item from the sender once the "
                     "receiver has it (move); unchecked keeps a copy"),
        ]),
        PrefSection("Appearance", "palette", [
            PrefItem("appearance.theme",     "Theme",     "dropdown",
                     "Colour theme for the application",
                     kwargs={"choices": ["dark", "light", "auto"]}),
            PrefItem("appearance.font_size", "Font size", "integer",
                     "Application-wide font size in points",
                     kwargs={"min": 7, "max": 24}),
            PrefItem("appearance.font_family", "Font family", "font",
                     "Choose from fonts installed on this system"),
        ]),
        PrefSection("Hidden workspace docks", "layout-sidebar", [
            # module types whose Workspace dock starts hidden;
            # reopen any time via View → Workspace (Ctrl+1)
            PrefItem("app.hide_workspace_dock", "", "module_id_list",
                     full_width=True),
        ]),
        PrefSection("Excluded send targets", "send-off", [
            # module types that never appear in the send dialogs (can still send)
            PrefItem("app.send_target_exclude", "", "module_id_list",
                     full_width=True),
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
        PrefSection("Startup", "play", [
            PrefItem("app.startup_modules", "", "startup_module_list",
                     "Modules opened automatically at startup. "
                     "Built-in defaults (🔒) can have their count changed but not removed. "
                     "Add extra modules with the + button.",
                     full_width=True),
        ]),
    ]

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self.resize(1000, 600)
        self._set_app_icon()
        QtWidgets.QApplication.instance().aboutToQuit.connect(self._save_layout)

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def _on_preferences(self) -> None:
        cfg = self._context.config

        # Assemble a flat snapshot of the global sections we expose.
        # channel_manager is excluded — it saves itself directly via ChannelManagerWidget.
        io_snap = copy.deepcopy(cfg.get_group("io"))
        io_snap.pop("channel_manager", None)
        snapshot = {
            "app":        copy.deepcopy(cfg.get_group("app")),
            "appearance": copy.deepcopy(cfg.get_group("appearance")),
            "io":         io_snap,
            "plugins":    copy.deepcopy(cfg.get_group("plugins")),
        }

        _appearance_before = copy.deepcopy(cfg.get_group("appearance"))

        def _apply(new_cfg: dict) -> None:
            nonlocal _appearance_before
            for section, values in new_cfg.items():
                for key, val in values.items():
                    cfg.set(section, key, val)
            appearance_now = cfg.get_group("appearance")
            if appearance_now != _appearance_before:
                from angstrompro.gui.appearance.theme_manager import ThemeManager
                ThemeManager(appearance_now).apply()
                _appearance_before = copy.deepcopy(appearance_now)
            from angstrompro.gui.widgets.log_panel import _LEVEL_MAP
            self._log_panel.set_min_level(
                _LEVEL_MAP.get(cfg.get("app", "log_level", "WARNING"), logging.WARNING))

        def _save(new_cfg: dict) -> None:
            _apply(new_cfg)
            cfg.save_defaults()

        def _reset() -> None:
            from angstrompro.core.configs.defaults import DEFAULTS
            from angstrompro.core.configs.config_manager import _merge_startup_modules
            io_defaults = copy.deepcopy(DEFAULTS.get("io", {}))
            io_defaults.pop("channel_manager", None)
            app_defaults = copy.deepcopy(DEFAULTS.get("app", {}))
            # reset startup_modules to defaults only (drop user additions)
            app_defaults["startup_modules"] = copy.deepcopy(
                DEFAULTS.get("app", {}).get("startup_modules", []))
            _apply({
                "app":        app_defaults,
                "appearance": copy.deepcopy(DEFAULTS.get("appearance", {})),
                "io":         io_defaults,
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

    def _populate_help_menu(self, menu) -> None:
        from angstrompro.gui.dialogs.about_dialog import show_about
        menu.addSeparator()
        act_formats = menu.addAction("Supported Formats…")
        act_formats.triggered.connect(self._on_format_browser)
        menu.addSeparator()
        act_about = menu.addAction("About AngstromPro…")
        act_about.triggered.connect(lambda: show_about(self))

    def build_ui(self) -> None:

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

        # --- Log dock (below Tasks) ---
        from angstrompro.gui.widgets.log_panel import _LEVEL_MAP
        log_level = _LEVEL_MAP.get(
            self._context.config.get("app", "log_level", "WARNING"), logging.WARNING)
        self._log_panel = LogPanel(min_level=log_level)
        self._dock_log = QtWidgets.QDockWidget("Log", self)
        self._dock_log.setObjectName("wb_dock_log")
        self._dock_log.setWidget(self._log_panel)
        self._dock_log.setAllowedAreas(DockArea.BottomDockWidgetArea | DockArea.TopDockWidgetArea |
                                       DockArea.LeftDockWidgetArea   | DockArea.RightDockWidgetArea)
        self.addDockWidget(DockArea.RightDockWidgetArea, self._dock_log)
        self.splitDockWidget(self._dock_tasks, self._dock_log, QtCore.Qt.Orientation.Vertical)

        # --- Dev: Config editor — hidden dock, toggled via Ctrl+Shift+D ---
        self._dock_config = None
        act_dev = Action(self)   # QtWidgets.QAction is Qt5-only; QtGui in Qt6
        act_dev.setShortcut("Ctrl+Shift+D")
        act_dev.triggered.connect(self._toggle_config_editor)
        self.addAction(act_dev)

    def _on_format_browser(self) -> None:
        from angstrompro.gui.dialogs.format_browser_dialog import show_format_browser
        show_format_browser(self)

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
        inputs = list(self.process_inputs)
        if not inputs:
            inputs = [item]
        else:
            inputs[0] = item
        self.process_inputs = inputs
        self._refresh_slots_panel()
        self._refresh_workspace_panel()

    def _clear_slot(self, idx: int) -> None:
        inputs = list(self.process_inputs)
        if idx < len(inputs):
            inputs[idx] = None
        self.process_inputs = inputs
        self._refresh_slots_panel()
        self._refresh_workspace_panel()

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Layout persistence
    # ------------------------------------------------------------------

    def _apply_default_layout(self) -> None:
        """Set coded default dock proportions — used on first launch."""
        self.resizeDocks([self._dock_tasks], [300], QtCore.Qt.Orientation.Vertical)
        self.resizeDocks([self._dock_log],   [150], QtCore.Qt.Orientation.Vertical)

    def _restore_layout(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        geom  = qs.value("workbench/geometry")
        state = qs.value("workbench/layout")
        if geom:
            self.restoreGeometry(geom)
        if not (state and self.restoreState(state)):
            self._apply_default_layout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not hasattr(self, "_layout_restored"):
            self._layout_restored = True
            QtCore.QTimer.singleShot(0, self._restore_layout)

    def _save_layout(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        qs.setValue("workbench/geometry", self.saveGeometry())
        qs.setValue("workbench/layout",   self.saveState())
        qs.sync()

    def closeEvent(self, event) -> None:
        self._save_layout()
        event.accept()   # main workbench close = quit; don't suppress like child modules

    def _set_app_icon(self) -> None:
        icon = self._context.icons.get("app_logo")
        if icon.isNull():
            return
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        self.setWindowIcon(icon)

