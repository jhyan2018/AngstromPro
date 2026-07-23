# -*- coding: utf-8 -*-
"""
AppPaths — typed container for all filesystem paths used by AngstromPro.

All user-writable paths are derived from the User Data Folder chosen on
first launch (see user_data_folder.py).  Only the pointer to that folder
is stored in the OS-managed location so data survives OS reinstalls.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from angstrompro.app.user_data_folder import get_user_data_folder


@dataclass(frozen=True)
class AppPaths:
    """Important filesystem paths used by AngstromPro."""

    project_root:    Path   # source tree root (dev only)
    package_root:    Path   # angstrompro package directory
    user_data_dir:    Path   # <UserDataFolder>
    user_config_dir:  Path   # <UserDataFolder>/config/
    user_plugins_dir: Path   # <UserDataFolder>/config/plugins/
    user_cache_dir:   Path   # <UserDataFolder>/cache/
    user_logs_dir:    Path   # <UserDataFolder>/logs/

    @classmethod
    def create(cls) -> "AppPaths":
        package_root = Path(__file__).resolve().parents[1]
        project_root = package_root.parents[1]

        user_data = get_user_data_folder()
        if user_data is None:
            raise RuntimeError(
                "AppPaths.create() called before the user data folder was set. "
                "Call _ensure_user_data_folder() in main() first."
            )
        user_config  = user_data / "config"
        user_plugins = user_data / "config" / "plugins"
        user_cache   = user_data / "cache"
        user_logs    = user_data / "logs"

        return cls(
            project_root     = project_root,
            package_root     = package_root,
            user_data_dir    = user_data,
            user_config_dir  = user_config,
            user_plugins_dir = user_plugins,
            user_cache_dir   = user_cache,
            user_logs_dir    = user_logs,
        )

    def ensure_dirs(self) -> None:
        for d in (
            self.user_config_dir,
            self.user_plugins_dir,
            self.user_cache_dir,
            self.user_logs_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Convenience path helpers
    # ------------------------------------------------------------------

    @property
    def settings_ini(self) -> Path:
        """QSettings INI file path."""
        return self.user_config_dir / "settings.ini"

    @property
    def config_json(self) -> Path:
        """ConfigManager JSON file path."""
        return self.user_config_dir / "config.json"

    def plugin_config_json(self, plugin_id: str) -> Path:
        """Per-plugin config file: <UserDataFolder>/config/plugins/<plugin_id>.json"""
        return self.user_plugins_dir / f"{plugin_id}.json"
