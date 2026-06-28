# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 2026

@author: jiahaoYan
"""

"""
ParamHistoryManager — persists last-used parameters per process.

Stored in params_history.json alongside config.json.
Falls back to ProcessSchema defaults when no history exists.
"""

import copy
import json
import logging
from pathlib import Path
from typing import Any

from angstrompro.core.configs.config_paths import get_config_dir

log = logging.getLogger(__name__)


def _get_history_file() -> Path:
    return get_config_dir() / "params_history.json"


class ParamHistoryManager:
    def __init__(self) -> None:
        self._history: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, process_name: str, defaults: dict) -> dict:
        """Return last-used params for process, falling back to defaults."""
        saved  = self._history.get(process_name, {})
        merged = copy.deepcopy(defaults)
        # saved overrides defaults; new default keys survive schema changes
        merged.update(saved)
        return merged

    def save(self, process_name: str, params: dict) -> None:
        """Persist params for process_name to disk."""
        self._history[process_name] = copy.deepcopy(params)
        self._flush()

    def clear(self, process_name: str | None = None) -> None:
        """Clear history for one process, or all if process_name is None."""
        if process_name:
            self._history.pop(process_name, None)
        else:
            self._history.clear()
        self._flush()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        path = _get_history_file()
        if not path.exists():
            return
        try:
            self._history = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Could not load params history (%s); starting fresh", exc)

    def _flush(self) -> None:
        path = _get_history_file()
        try:
            path.write_text(json.dumps(self._history, indent=2), encoding="utf-8")
        except OSError as exc:
            log.error("Could not save params history: %s", exc)
