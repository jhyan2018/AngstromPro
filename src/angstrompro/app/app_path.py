# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:09:09 2026

@author: jiahaoYan
"""

# src/angstrompro/app/app_paths.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """
    Important filesystem paths used by AngstromPro.
    """

    project_root: Path
    package_root: Path
    user_config_dir: Path
    user_data_dir: Path
    user_cache_dir: Path

    @classmethod
    def create_default(cls) -> "AppPaths":
        package_root = Path(__file__).resolve().parents[1]
        project_root = package_root.parents[1]

        user_home = Path.home()
        user_root = user_home / ".angstrompro"

        return cls(
            project_root=project_root,
            package_root=package_root,
            user_config_dir=user_root / "config",
            user_data_dir=user_root / "data",
            user_cache_dir=user_root / "cache",
        )

    def ensure_dirs(self) -> None:
        self.user_config_dir.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.user_cache_dir.mkdir(parents=True, exist_ok=True)