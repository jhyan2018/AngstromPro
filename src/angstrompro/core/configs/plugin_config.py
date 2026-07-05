# -*- coding: utf-8 -*-
"""
Created on 2026-07-05

@author: jiahaoYan

PluginConfig — isolated diff-only JSON config for a single plugin package.

Each plugin package (identified by its namespace, e.g. "myplugin") gets its
own file at  <UserDataFolder>/config/plugins/<plugin_id>.json  so that a
misbehaving plugin cannot corrupt the core config.json.

The format and semantics are identical to ConfigManager:
  - Built-in defaults are {} (plugins supply their own via module defaults)
  - Only values differing from defaults are written to disk
  - Module configs are stored under  modules.<module_id>
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path

from angstrompro.core.configs.config_validation import validate_and_coerce

log = logging.getLogger(__name__)


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _diff(current: dict, defaults: dict) -> dict:
    result = {}
    for key, value in current.items():
        default_val = defaults.get(key)
        if isinstance(value, dict) and isinstance(default_val, dict):
            sub = _diff(value, default_val)
            if sub:
                result[key] = sub
        elif value != default_val:
            result[key] = copy.deepcopy(value)
    return result


class PluginConfig:
    """Per-plugin isolated config backed by a single JSON file."""

    def __init__(self, plugin_id: str, path: Path) -> None:
        self._plugin_id = plugin_id
        self._path      = path
        self._defaults: dict = {}
        self._data:     dict = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                saved = json.loads(self._path.read_text(encoding="utf-8"))
                saved = validate_and_coerce(saved, self._defaults)
                self._data = _deep_merge(self._defaults, saved)
            except Exception as exc:
                log.warning("PluginConfig(%s): failed to load %s — %s",
                            self._plugin_id, self._path, exc)
                self._data = copy.deepcopy(self._defaults)
        else:
            self._data = copy.deepcopy(self._defaults)

    # ── module config access ───────────────────────────────────────────────

    def get_module(self, module_id: str) -> dict:
        return copy.deepcopy(
            self._data.get("modules", {}).get(module_id, {})
        )

    def set_module(self, module_id: str, cfg: dict) -> None:
        module_defaults = self._defaults.get("modules", {}).get(module_id, {})
        validated = validate_and_coerce(cfg, module_defaults, module_id)
        self._data.setdefault("modules", {})[module_id] = validated

    def save(self) -> None:
        diff = _diff(self._data, self._defaults)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(diff, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            log.error("PluginConfig(%s): failed to save — %s", self._plugin_id, exc)
