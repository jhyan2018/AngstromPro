"""
ConfigManager — owns the merged, in-memory config for the app lifetime.

Lifecycle
---------
1. Created once at app startup (in AppContext.__init__):
       config = ConfigManager()
   Loads: built-in defaults  ←  deep-merged with  →  saved config file (if any)
2. Passed into AppContext; all consumers receive it via context.config.
3. Consumers call get_group("gui") → receive a deep copy for local use.
4. "Save as Default"   → save_defaults()    writes diff-only to disk.
5. "Reset to Default"  → reset_to_defaults() reloads from built-in DEFAULTS.
6. "Reload Saved"      → reload_saved()      reloads from config file.

Save strategy
-------------
Only values that differ from built-in DEFAULTS are written to the config file.
On the next startup _load() merges that sparse file back onto DEFAULTS, so
changed values override defaults and unmentioned keys keep their default.
"""

import copy
import json
import logging
from typing import Any

from angstrompro.core.configs.defaults import DEFAULTS  # assembled from defaults/ subpackage
from angstrompro.core.configs.config_paths import get_config_file
from angstrompro.core.configs.config_validation import validate_and_coerce

log = logging.getLogger(__name__)


def _merge_startup_modules(base: list, user: list) -> list:
    """
    Merge startup_modules lists: base (defaults) + user additions.
    - All default entries are always preserved.
    - User entries with matching module_id override the default count.
    - User entries with new module_ids are appended.
    """
    result = {entry["module_id"]: copy.deepcopy(entry) for entry in base}
    for entry in user:
        mid = entry.get("module_id", "")
        if mid:
            result[mid] = copy.deepcopy(entry)
    return list(result.values())


def _deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict: override values layered onto base recursively."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key == "startup_modules" and isinstance(result.get(key), list) and isinstance(value, list):
            result[key] = _merge_startup_modules(result[key], value)
        elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _diff_from_defaults(current: dict, defaults: dict) -> dict:
    """Return only the key/value pairs in current that differ from defaults."""
    result = {}
    for key, value in current.items():
        default_val = defaults.get(key)
        if isinstance(value, dict) and isinstance(default_val, dict):
            sub = _diff_from_defaults(value, default_val)
            if sub:
                result[key] = sub
        elif key not in defaults or value != default_val:
            result[key] = copy.deepcopy(value)
    return result


class ConfigManager:
    def __init__(self) -> None:
        self._config: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_group(self, group: str) -> dict:
        """Return a deep copy of a top-level config group for local use."""
        if group not in self._config:
            raise KeyError(f"Unknown config group: {group!r}")
        return copy.deepcopy(self._config[group])

    def get_all(self) -> dict:
        """Return a deep copy of the full config (used by the editor widget)."""
        return copy.deepcopy(self._config)

    def apply_all(self, new_config: dict) -> None:
        """Replace the full in-memory config (used by the editor widget after editing)."""
        self._config = copy.deepcopy(new_config)

    def get(self, group: str, key: str, default: Any = None) -> Any:
        """Convenience accessor for a single value within a group."""
        return copy.deepcopy(self._config.get(group, {}).get(key, default))

    def set(self, group: str, key: str, value: Any) -> None:
        """Update a single value in the live config (does not persist)."""
        if group not in self._config:
            raise KeyError(f"Unknown config group: {group!r}")
        self._config[group][key] = copy.deepcopy(value)

    def set_module_config(self, module_key: str, config: dict) -> None:
        """Replace a single module's config slice in the live config (does not persist)."""
        defaults = DEFAULTS.get("modules", {}).get(module_key, {})
        validated = validate_and_coerce(config, defaults, module_key)
        self._config.setdefault("modules", {})[module_key] = validated

    def save_defaults(self) -> None:
        """Persist only values that differ from built-in defaults to the config file."""
        path = get_config_file()
        if path is None:
            log.warning("Config not saved: user data folder is not set")
            return
        diff = _diff_from_defaults(self._config, DEFAULTS)
        try:
            path.write_text(json.dumps(diff, indent=2), encoding="utf-8")
            log.info("Config saved to %s (%d top-level group(s) changed)", path, len(diff))
        except OSError as exc:
            log.error("Failed to save config: %s", exc)

    def reset_to_defaults(self) -> None:
        """Discard file and in-memory overrides; reload built-in defaults."""
        self._config = copy.deepcopy(DEFAULTS)
        log.info("Config reset to built-in defaults")

    def reload_saved(self) -> None:
        """Discard in-memory changes; reload from file (merged onto defaults)."""
        self._load()
        log.info("Config reloaded from saved file")

    def diff_count(self) -> int:
        """Return the number of leaf values that differ from built-in defaults."""
        return _count_leaves(_diff_from_defaults(self._config, DEFAULTS))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._config = copy.deepcopy(DEFAULTS)
        path = get_config_file()
        if path is None:
            log.debug("Config file unavailable (user data folder not set); using defaults")
            return
        if path.exists():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                saved = validate_and_coerce(saved, DEFAULTS)
                self._config = _deep_merge(self._config, saved)
                log.debug("Config loaded from %s", path)
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("Could not read config file (%s); using defaults", exc)


def _count_leaves(d: dict) -> int:
    count = 0
    for v in d.values():
        count += _count_leaves(v) if isinstance(v, dict) else 1
    return count
