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
        self.config = config
        self.theme = theme
        self.icons = icons
        self.tasks  = TaskManager(max_pool_threads=config.get("tasks", "max_concurrent_tasks", 4))
        self.workspace_manager = WorkspaceManager()
        self.module_manager = AModuleManager(self.workspace_manager)
        self.signals = AppSignals()