# -*- coding: utf-8 -*-
"""
AngstromPro User Data Folder — the single user-chosen root for all persistent
data (config, settings, cache, logs, snapshots).

Only the *pointer* to this folder is stored in the OS-managed location
(e.g. %APPDATA%\angstrompro\datapath.txt on Windows).  Everything else lives
under the user-chosen folder, which should be on a drive or cloud-synced
folder that survives OS reinstalls.

Folder layout under the user data folder
-----------------------------------------
<UserDataFolder>/
  config/
    config.json          ← ConfigManager (app settings, diff-only from defaults)
    settings.ini         ← QSettings (UI state: window geometry, last-used values)
    process_menus.json   ← user-customised process menu layout
    plugins.json         ← plugin search paths
  recent_files.json
  cache/
    snapshots/           ← dataset thumbnails for quick browser (regenerable)
  logs/

Public API
----------
get_user_data_folder() -> Path | None
set_user_data_folder(path: Path) -> None
is_user_data_folder_set() -> bool
default_suggestion() -> Path
user_data_subpath(*parts) -> Path   convenience: resolve a path under the folder
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Pointer file — the only thing stored in the OS-managed location
# ---------------------------------------------------------------------------

def _pointer_file() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    ptr = base / "angstrompro" / "datapath.txt"
    ptr.parent.mkdir(parents=True, exist_ok=True)
    return ptr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_user_data_folder() -> Path | None:
    """Return the configured user data folder, or None if not yet set."""
    ptr = _pointer_file()
    if not ptr.exists():
        return None
    text = ptr.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return Path(text)


def set_user_data_folder(path: Path) -> None:
    """Persist *path* as the user data folder and create required subdirectories."""
    path = Path(path).expanduser().resolve()
    # Create the folder structure
    for subdir in ("config", "cache/snapshots", "logs"):
        (path / subdir).mkdir(parents=True, exist_ok=True)
    (path / "cache" / "snapshots").mkdir(parents=True, exist_ok=True)
    _pointer_file().write_text(str(path), encoding="utf-8")


def is_user_data_folder_set() -> bool:
    return get_user_data_folder() is not None


def user_data_subpath(*parts: str) -> Path:
    """
    Resolve a path under the user data folder (or the folder itself if no parts).
    Raises RuntimeError if the folder has not been set.
    """
    folder = get_user_data_folder()
    if folder is None:
        raise RuntimeError("User data folder is not set. Call set_user_data_folder() first.")
    return folder.joinpath(*parts) if parts else folder


def get_qsettings():
    """
    Return a QSettings instance backed by <UserDataFolder>/config/settings.ini.
    All UI state (window geometry, last-used export options, etc.) should use
    this instead of QSettings() with default OS storage.

    Import is deferred so this module stays importable before Qt is initialised.
    """
    from angstrompro.utils.qt_compat import QtCore  # noqa: PLC0415
    ini = user_data_subpath("config", "settings.ini")
    ini.parent.mkdir(parents=True, exist_ok=True)
    return QtCore.QSettings(str(ini), QtCore.QSettings.Format.IniFormat
                            if hasattr(QtCore.QSettings, "Format")
                            else QtCore.QSettings.IniFormat)


def default_suggestion() -> Path:
    """
    Suggest a sensible default path to show in the setup dialog.
    Prefers a non-system drive on Windows; falls back to ~/Documents/AngstromPro.
    """
    if sys.platform == "win32":
        for drive in ("D", "E", "F", "G"):
            try:
                candidate = Path(f"{drive}:\\")
                if candidate.exists():
                    return candidate / "AngstromPro"
            except OSError:
                pass
    return Path.home() / "Documents" / "AngstromPro"
