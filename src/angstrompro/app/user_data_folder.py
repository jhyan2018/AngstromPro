# -*- coding: utf-8 -*-
"""
AngstromPro User Data Folder — the single user-chosen root for all persistent
data (config, settings, cache, and logs).

Only the *pointer* to this folder is stored in the OS-managed location
(e.g. ``%APPDATA%\\angstrompro\\datapath.txt`` on Windows). Everything else lives
under the user-chosen folder, which should be on a drive or cloud-synced
folder that survives OS reinstalls.

Folder layout under the user data folder
-----------------------------------------
<UserDataFolder>/
  config/
    config.json          ← ConfigManager (app settings, diff-only from defaults)
    settings.ini         ← QSettings (UI state: window geometry, last-used values)
    plugins.json         ← plugin search paths
  cache/
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

import json
import logging
import os
import shutil
import sys
import uuid
from pathlib import Path


USER_DATA_DIRNAME = "angstrompro-user"
_RUNTIME_ID = getattr(sys, "_angstrompro_runtime_id", "")
if not _RUNTIME_ID:
    _RUNTIME_ID = uuid.uuid4().hex
    # Keep the identifier stable if this module is reloaded inside the same
    # Spyder kernel. A restarted kernel receives a new sys module and ID.
    setattr(sys, "_angstrompro_runtime_id", _RUNTIME_ID)


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


def _pending_pointer_file() -> Path:
    return _pointer_file().with_name("datapath.pending.json")


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
    for subdir in ("config", "cache", "logs"):
        (path / subdir).mkdir(parents=True, exist_ok=True)
    ptr = _pointer_file()
    tmp = ptr.with_suffix(".tmp")
    tmp.write_text(str(path), encoding="utf-8")
    tmp.replace(ptr)


def user_data_folder_from_parent(parent: Path) -> Path:
    """Return the dedicated data root for a user-selected parent location."""
    parent = Path(parent).expanduser().resolve()
    if parent.name.casefold() == USER_DATA_DIRNAME.casefold():
        return parent
    return parent / USER_DATA_DIRNAME


def get_pending_user_data_folder() -> Path | None:
    """Return a queued user-data folder change, if one is valid."""
    pending = _pending_pointer_file()
    if not pending.exists():
        return None
    try:
        payload = json.loads(pending.read_text(encoding="utf-8"))
        path = str(payload.get("path", "")).strip()
    except (OSError, ValueError, TypeError):
        return None
    return Path(path) if path else None


def queue_user_data_folder(path: Path) -> Path:
    """
    Queue *path* for the next genuinely new Python runtime.

    The active pointer is deliberately left unchanged so a live application
    cannot split configuration, logging, QSettings, and SQLite across roots.
    """
    path = Path(path).expanduser().resolve()
    source = get_user_data_folder()
    if source is not None:
        source = source.expanduser().resolve()
        if (
            path != source
            and (path.is_relative_to(source) or source.is_relative_to(path))
        ):
            raise ValueError(
                "The new user-data folder cannot contain, or be contained by, "
                "the current user-data folder."
            )
    for subdir in ("config", "cache", "logs"):
        (path / subdir).mkdir(parents=True, exist_ok=True)

    pending = _pending_pointer_file()
    tmp = pending.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(
            {
                "path": str(path),
                "source_path": str(source) if source is not None else "",
                "runtime_id": _RUNTIME_ID,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    tmp.replace(pending)
    return path


def cancel_pending_user_data_folder() -> None:
    """Discard a queued folder change without affecting the active pointer."""
    try:
        _pending_pointer_file().unlink()
    except FileNotFoundError:
        pass


def apply_pending_user_data_folder_for_new_runtime() -> bool:
    """
    Promote a queued path only when this is not the runtime that queued it.

    A second launch in the same Spyder kernel retains the same runtime ID and
    therefore cannot redirect a live hosted session. A standalone relaunch or
    Spyder kernel restart imports this module afresh and receives a new ID.
    """
    pending = _pending_pointer_file()
    if not pending.exists():
        return False
    try:
        payload = json.loads(pending.read_text(encoding="utf-8"))
        path = str(payload.get("path", "")).strip()
        source_path = str(payload.get("source_path", "")).strip()
        origin_runtime = str(payload.get("runtime_id", "")).strip()
    except (OSError, ValueError, TypeError):
        try:
            pending.unlink()
        except OSError:
            pass
        return False
    if not path or not origin_runtime or origin_runtime == _RUNTIME_ID:
        return False

    target = Path(path).expanduser().resolve()
    source = Path(source_path).expanduser().resolve() if source_path else None
    if source is not None and source.is_dir() and source != target:
        def _ignore_legacy_snapshots(directory: str, names: list[str]):
            if Path(directory).name.casefold() == "cache" and "snapshots" in names:
                return {"snapshots"}
            return set()

        try:
            shutil.copytree(
                source,
                target,
                dirs_exist_ok=True,
                ignore=_ignore_legacy_snapshots,
            )
        except (OSError, shutil.Error) as exc:
            logging.getLogger(__name__).warning(
                "Could not copy user data from %s to %s: %s",
                source,
                target,
                exc,
            )
            return False

    set_user_data_folder(target)
    try:
        pending.unlink()
    except FileNotFoundError:
        pass
    return True


def is_user_data_folder_set() -> bool:
    folder = get_user_data_folder()
    return folder is not None and folder.is_dir()


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


def setup_file_logging() -> None:
    """
    Attach a rotating file handler to the root logger writing to
    <UserDataFolder>/logs/angstrompro.log (max 1 MB, keep 3 backups).
    Safe to call multiple times — installs only once.
    """
    import logging
    import logging.handlers

    root = logging.getLogger()
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        return
    try:
        log_path = user_data_subpath("logs", "angstrompro.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        root.addHandler(fh)
    except Exception as exc:
        logging.warning("Could not set up file logging: %s", exc)


def default_suggestion() -> Path:
    """
    Suggest a parent location for the first-launch setup dialog.
    Prefers a non-system drive on Windows; falls back to ~/Documents.
    """
    if sys.platform == "win32":
        for drive in ("D", "E", "F", "G"):
            try:
                candidate = Path(f"{drive}:\\")
                if candidate.exists():
                    return candidate
            except OSError:
                pass
    return Path.home() / "Documents"
