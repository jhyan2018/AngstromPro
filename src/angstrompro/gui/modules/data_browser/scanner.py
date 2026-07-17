# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

Background scanner for the Data Browser.

One long-lived thread (task system backend="persistent") that walks the
watch folders, finds files with no fresh cache record, and asks the main
thread to render them — fire-and-forget, throttled to one request per
interval so the io pool is never flooded and viewport (HIGH) renders
always find a free thread quickly.

The scanner is stateless: SQLite IS its progress record.  After a restart
it re-walks from the first folder, skips everything cached (mtime match,
milliseconds per file) and naturally resumes where rendering left off.

Thread-safety model
-------------------
- ScannerShared: lock-protected settings snapshot.  Main thread writes on
  preference/watch-folder changes; scanner reads a copy each pass and
  re-checks folder membership per file so a removed folder aborts quickly.
- ScannerBridge: QObject owned by the MAIN thread.  The scanner emits its
  signal from the worker thread; Qt delivers queued to the main thread,
  where the module submits the actual LOW render task.  The scanner never
  touches TaskManager or any main-thread state directly.
- The scanner opens its OWN ThumbnailCache (sqlite connection); WAL allows
  the concurrent main-thread writer safely.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from angstrompro.utils.qt_compat import QtCore, Signal

from .thumbnail_cache import ThumbnailCache

log = logging.getLogger(__name__)

_SLEEP_STEP = 0.1   # granularity of interruptible sleeps


class ScannerShared:
    """Settings shared main thread → scanner thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = {
            "enabled":          True,
            "watch_folders":    [],
            "previewable_exts": set(),
            "request_interval": 1.5,    # seconds between LOW requests
            "idle_interval":    60.0,   # seconds between passes
            "scan_order":       "newest_first",  # | "oldest_first" | "name"
        }

    def update(self, **kwargs) -> None:
        with self._lock:
            self._data.update(kwargs)

    def snapshot(self) -> dict:
        with self._lock:
            d = dict(self._data)
            d["watch_folders"] = list(d["watch_folders"])
            d["previewable_exts"] = set(d["previewable_exts"])
            return d

    def has_folder(self, folder: str) -> bool:
        with self._lock:
            return folder in self._data["watch_folders"]

    def is_enabled(self) -> bool:
        with self._lock:
            return bool(self._data["enabled"])


class ScannerBridge(QtCore.QObject):
    """Owned by the main thread; the scanner emits from the worker thread."""
    render_requested = Signal(str)   # file_path


def _sleep_cancellable(seconds: float, cancel_token) -> bool:
    """Sleep in small steps.  Returns False when cancelled."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cancel_token is not None and cancel_token.is_cancelled():
            return False
        time.sleep(_SLEEP_STEP)
    return True


def _gather_files(folder: str, exts: set, order: str) -> list[tuple[str, float]]:
    files: list[tuple[str, float]] = []
    for root, _dirs, names in os.walk(folder):
        for n in names:
            if Path(n).suffix.lower() in exts:
                p = os.path.join(root, n)
                try:
                    files.append((p, os.path.getmtime(p)))
                except OSError:
                    continue
    if order == "name":
        files.sort(key=lambda t: t[0].lower())
    else:
        files.sort(key=lambda t: t[1], reverse=(order == "newest_first"))
    return files


def scanner_loop(cache_dir: str, shared: ScannerShared,
                 bridge: ScannerBridge, cancel_token=None) -> None:
    """Task function for backend="persistent".  Loops until cancelled."""
    cache = ThumbnailCache(cache_dir)
    log.info("Data Browser scanner started")
    try:
        while cancel_token is None or not cancel_token.is_cancelled():
            snap = shared.snapshot()
            did_work = False

            if snap["enabled"]:
                for folder in snap["watch_folders"]:
                    if not shared.is_enabled():
                        break   # disabled mid-pass — skip remaining folders
                    if not os.path.isdir(folder):
                        continue
                    files = _gather_files(folder, snap["previewable_exts"],
                                          snap["scan_order"])
                    for path, mtime in files:
                        if cancel_token is not None and cancel_token.is_cancelled():
                            return
                        if not shared.is_enabled():
                            break   # user disabled scanning mid-pass — stop now
                        if not shared.has_folder(folder):
                            break   # folder removed mid-pass — abort it
                        if not cache.should_render(path, mtime):
                            continue
                        bridge.render_requested.emit(path)
                        did_work = True
                        if not _sleep_cancellable(snap["request_interval"],
                                                  cancel_token):
                            return

            # idle between passes; a busy pass re-scans sooner so freshly
            # errored files get their retry without the full idle wait
            idle = snap["idle_interval"] if not did_work else \
                min(snap["idle_interval"], 10.0)
            if not _sleep_cancellable(idle, cancel_token):
                return
    finally:
        cache.close()
        log.info("Data Browser scanner stopped")
