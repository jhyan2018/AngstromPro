# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:52:42 2026

@author: jiahaoYan
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points

from angstrompro.core.configs import ConfigManager
from angstrompro.core.workspaces import WorkspaceManager
from angstrompro.core.modules import AModuleManager
from angstrompro.core.tasks import TaskManager
from angstrompro.core.processes import ProcessRegistry, ParamHistoryManager
from angstrompro.gui.appearance import ThemeManager, IconManager
from angstrompro.app.app_signals import AppSignals
from angstrompro.io.channel_manager import ChannelManager


class AppContext:
    """
    Shared application context — owns all managers.
    """

    def __init__(self, config: ConfigManager, theme: ThemeManager, icons: IconManager) -> None:
        self._config          = config
        self._theme           = theme
        self._icons           = icons
        self._signals         = AppSignals()
        self._tasks           = TaskManager(compute_threads=config.get("tasks", "max_concurrent_tasks", 4))
        self._workspace_manager = WorkspaceManager()
        self._module_manager  = AModuleManager(self._workspace_manager)
        self._load_plugins()   # must run before ProcessRegistry() snapshots _PENDING
        self._processes       = ProcessRegistry()
        self._param_history   = ParamHistoryManager()
        self._channel_manager = ChannelManager(config)

    # ------------------------------------------------------------------
    # Plugin discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _load_plugins() -> None:
        """Import every package registered under the 'angstrompro.plugins' entry-point group."""
        log = logging.getLogger(__name__)
        eps = entry_points(group="angstrompro.plugins")
        for ep in eps:
            try:
                ep.load()
                log.info("Loaded plugin: %s (%s)", ep.name, ep.value)
            except Exception as exc:
                log.warning("Failed to load plugin %r: %s", ep.name, exc)

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
    def signals(self) -> AppSignals:
        return self._signals

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
    def processes(self) -> ProcessRegistry:
        return self._processes

    @property
    def param_history(self) -> ParamHistoryManager:
        return self._param_history

    @property
    def channel_manager(self) -> ChannelManager:
        return self._channel_manager
