# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:52:42 2026

@author: jiahaoYan
"""

from __future__ import annotations

from angstrompro.core.configs import ConfigManager
from angstrompro.core.workspaces import WorkspaceManager
from angstrompro.core.modules import AModuleManager
from angstrompro.core.tasks import TaskManager
from angstrompro.gui.appearance import ThemeManager, IconManager
from angstrompro.app.app_signals import AppSignals


class AppContext:
    """
    Shared application context — owns all managers.
    """

    def __init__(self, config: ConfigManager, theme : ThemeManager, icons : IconManager) -> None:
        self._config = config
        self._theme = theme
        self._icons = icons
        self._tasks  = TaskManager(compute_threads=config.get("tasks", "max_concurrent_tasks", 4))
        self._workspace_manager = WorkspaceManager()
        self._module_manager = AModuleManager(self._workspace_manager)
        self._signals = AppSignals()

    @property
    def config(self) -> ConfigManager:
        return self._config

    @property
    def theme(self) -> ThemeManager:
        return self._theme

    @property
    def icons(self) -> IconManager:
        return self._icons

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    @property
    def workspace_manager(self) -> WorkspaceManager:
        return self._workspace_manager

    @property
    def module_manager(self) -> AModuleManager:
        return self._module_manager

    @property
    def signals(self) -> AppSignals:
        return self._signals