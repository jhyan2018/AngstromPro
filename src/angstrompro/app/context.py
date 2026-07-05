# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:52:42 2026

@author: jiahaoYan
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points

from angstrompro.core.configs import ConfigManager
from angstrompro.core.configs.plugin_config import PluginConfig
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
        self._channel_manager  = ChannelManager(config)
        self._plugin_configs:  dict[str, PluginConfig] = {}

    # ------------------------------------------------------------------
    # Plugin discovery
    # ------------------------------------------------------------------

    def _load_plugins(self) -> None:
        """Load plugins in two passes: private config-path plugins first, then entry-points."""
        import sys
        import importlib
        log = logging.getLogger(__name__)

        # Pass 1: path-based plugins declared in config
        for entry in self._config.get("plugins", "path_plugins", []):
            path   = entry.get("path", "").strip()
            module = entry.get("module", "").strip()
            if not path or not module:
                continue
            if module in sys.modules:
                log.warning("Plugin %r skipped (already loaded by another mechanism)", module)
                continue
            if path not in sys.path:
                sys.path.insert(0, path)
            try:
                importlib.import_module(module)
                log.debug("Loaded plugin: %s", module)
            except Exception as exc:
                log.warning("Failed to load plugin %r: %s", module, exc)

        # Pass 2: public plugins registered via 'angstrompro.plugins' entry-point group
        eps = entry_points(group="angstrompro.plugins")
        for ep in eps:
            module_name = ep.value.split(":")[0].split(".")[0]
            if module_name in sys.modules:
                log.warning("Plugin %r skipped (already loaded via config path)", ep.name)
                continue
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

    def get_plugin_config(self, plugin_id: str) -> PluginConfig:
        """Return the isolated PluginConfig for the given plugin namespace."""
        if plugin_id not in self._plugin_configs:
            from angstrompro.app.app_path import AppPaths
            path = AppPaths.create().plugin_config_json(plugin_id)
            self._plugin_configs[plugin_id] = PluginConfig(plugin_id, path)
        return self._plugin_configs[plugin_id]
