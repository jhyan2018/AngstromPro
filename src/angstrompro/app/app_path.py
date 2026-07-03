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
    user_data_dir:   Path   # <UserDataFolder>
    user_config_dir: Path   # <UserDataFolder>/config/
    user_cache_dir:  Path   # <UserDataFolder>/cache/
    user_logs_dir:   Path   # <UserDataFolder>/logs/
    snapshot_dir:    Path   # <UserDataFolder>/cache/snapshots/

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
        user_config = user_data / "config"
        user_cache  = user_data / "cache"
        user_logs   = user_data / "logs"
        snapshots   = user_data / "cache" / "snapshots"

        return cls(
            project_root    = project_root,
            package_root    = package_root,
            user_data_dir   = user_data,
            user_config_dir = user_config,
            user_cache_dir  = user_cache,
            user_logs_dir   = user_logs,
            snapshot_dir    = snapshots,
        )

    def ensure_dirs(self) -> None:
        for d in (
            self.user_config_dir,
            self.user_cache_dir,
            self.user_logs_dir,
            self.snapshot_dir,
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

    @property
    def recent_files_json(self) -> Path:
        return self.user_data_dir / "recent_files.json"

    @property
    def process_menus_json(self) -> Path:
        return self.user_config_dir / "process_menus.json"

    @property
    def plugins_json(self) -> Path:
        return self.user_config_dir / "plugins.json"
