# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

ThumbnailCache — SQLite-backed thumbnail cache for the Data Browser.

One database file (cache.db, WAL mode) with two tables:

files        one row per source file: mtime, format, discovered channel list
             (JSON), error status + retry count
thumbnails   one row per (file, logical channel): uuid PNG path, layer count,
             chosen thumbnail layer, per-channel status

Design rules (settled in the Data Browser design discussion):
- WAL mode + immediate commit per write: fast, durable, no batching timer,
  no crash-loss window.
- The cache is self-validating: freshness = stored mtime == current mtime.
  Nothing else is ever trusted or persisted about the file system.
- PNG files are uuid-named; a metadata row is the only link back to the
  source file, so orphaned PNGs (crash between savefig and commit) are
  swept by cleanup_orphan_pngs() at startup.
- sqlite3 connections are not shared across threads: the main thread and
  the scanner thread each construct their own ThumbnailCache on the same
  db_path.  WAL allows the concurrent reader + writer safely.
- channel_id stores the LOGICAL display name from the ChannelManager
  ("dI/dV"), not the raw file channel name, so keys are stable across
  files from setups with different naming.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

MAX_RETRIES = 3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    file_path   TEXT PRIMARY KEY,
    mtime       REAL NOT NULL,
    format      TEXT NOT NULL DEFAULT '',
    channels    TEXT NOT NULL DEFAULT '[]',
    status      TEXT NOT NULL DEFAULT 'ok',
    retry_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS thumbnails (
    file_path       TEXT NOT NULL,
    channel_id      TEXT NOT NULL,
    png_path        TEXT NOT NULL DEFAULT '',
    layer_count     INTEGER NOT NULL DEFAULT 1,
    thumbnail_layer INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'ok',
    PRIMARY KEY (file_path, channel_id)
);
CREATE TABLE IF NOT EXISTS ratings (
    file_path   TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    stars       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (file_path, channel_id)
);
"""

# files.status:      'ok' | 'error'
# thumbnails.status: 'ok' | 'not_found'   (channel selected but absent in file)


class ThumbnailCache:
    """One instance per thread; all instances share the same db/cache dir."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)             # e.g. <user>/cache/data_browser
        self.thumb_dir = self.cache_dir / "thumbnails"
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        try:
            self._conn = self._open()
            return
        except sqlite3.Error as exc:
            log.warning("Thumbnail cache open failed (%s): %s", exc, self.db_path)

        # Recovery ladder — the cache is disposable, so escalate rather than
        # ever failing module startup:
        # 1. transient lock (antivirus / indexer on a fresh file): brief
        #    retries with backoff
        # 2. corrupt db / stale -wal/-shm sidecars: delete and rebuild
        # 3. location fundamentally unusable: local temp-dir cache (thumbnails
        #    regenerate; nothing of value is lost)
        import time
        for attempt in range(3):
            time.sleep(0.3 * (attempt + 1))
            self._delete_db_files()
            try:
                self._conn = self._open()
                log.warning("Thumbnail cache rebuilt after %d attempt(s): %s",
                            attempt + 1, self.db_path)
                return
            except sqlite3.Error:
                continue

        import tempfile
        fallback = Path(tempfile.gettempdir()) / "angstrompro" / "data_browser_cache"
        log.error("Thumbnail cache unusable at %s — using local fallback %s "
                  "for this session", self.cache_dir, fallback)
        self.cache_dir = fallback
        self.thumb_dir = fallback / "thumbnails"
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = fallback / "cache.db"
        try:
            self._conn = self._open()
        except sqlite3.Error:
            self._delete_db_files()
            self._conn = self._open()

    def _delete_db_files(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            try:
                p = Path(str(self.db_path) + suffix)
                if p.exists():
                    p.unlink()
            except OSError:
                pass

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                # WAL needs shared-memory sidecars; unsupported on some
                # network / cloud-synced / exFAT locations.  TRUNCATE keeps
                # commits durable, just without concurrent-reader support.
                log.warning("WAL unavailable for %s — falling back to "
                            "TRUNCATE journal mode", self.db_path)
                conn.execute("PRAGMA journal_mode=TRUNCATE")
            conn.executescript(_SCHEMA)
            conn.commit()
        except sqlite3.Error:
            # close before the caller deletes the file — an open handle
            # blocks unlink on Windows
            conn.close()
            raise
        return conn

    def close_quiet(self) -> None:
        try:
            if getattr(self, "_conn", None) is not None:
                self._conn.close()
        except Exception:
            pass

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # files table
    # ------------------------------------------------------------------

    def get_file(self, file_path: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM files WHERE file_path=?", (file_path,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["channels"] = json.loads(d["channels"])
        return d

    def is_fresh(self, file_path: str, mtime: float) -> bool:
        """True when a non-error record exists and matches the file's mtime."""
        row = self._conn.execute(
            "SELECT mtime, status FROM files WHERE file_path=?",
            (file_path,)).fetchone()
        return (row is not None and row["status"] == "ok"
                and row["mtime"] == mtime)

    def should_render(self, file_path: str, mtime: float) -> bool:
        """Scanner-side test: render unless fresh, or errored out of retries."""
        row = self._conn.execute(
            "SELECT mtime, status, retry_count FROM files WHERE file_path=?",
            (file_path,)).fetchone()
        if row is None or row["mtime"] != mtime:
            return True                       # unknown or modified → render
        if row["status"] == "ok":
            return False                      # fresh → skip
        return row["retry_count"] < MAX_RETRIES

    def upsert_file(self, file_path: str, mtime: float, format_id: str,
                    channels: list[str]) -> None:
        """Successful read: record file facts, reset error state."""
        self._conn.execute(
            "INSERT OR REPLACE INTO files "
            "(file_path, mtime, format, channels, status, retry_count) "
            "VALUES (?,?,?,?,'ok',0)",
            (file_path, mtime, format_id, json.dumps(channels)))
        self._conn.commit()

    def record_error(self, file_path: str, mtime: float) -> None:
        """Failed read/render: keep the row, bump retry_count.
        A changed mtime resets the count (user replaced the file)."""
        row = self._conn.execute(
            "SELECT mtime, retry_count FROM files WHERE file_path=?",
            (file_path,)).fetchone()
        retries = 1
        if row is not None and row["mtime"] == mtime:
            retries = row["retry_count"] + 1
        self._conn.execute(
            "INSERT OR REPLACE INTO files "
            "(file_path, mtime, format, channels, status, retry_count) "
            "VALUES (?,?,'','[]','error',?)",
            (file_path, mtime, retries))
        self._conn.commit()

    # ------------------------------------------------------------------
    # thumbnails table
    # ------------------------------------------------------------------

    def get_thumbnails(self, file_path: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM thumbnails WHERE file_path=? ORDER BY channel_id",
            (file_path,)).fetchall()
        return [dict(r) for r in rows]

    def get_thumbnail(self, file_path: str, channel_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM thumbnails WHERE file_path=? AND channel_id=?",
            (file_path, channel_id)).fetchone()
        return dict(row) if row else None

    def upsert_thumbnail(self, file_path: str, channel_id: str,
                         png_path: str, layer_count: int = 1,
                         thumbnail_layer: int = 0,
                         status: str = "ok") -> None:
        old = self.get_thumbnail(file_path, channel_id)
        self._conn.execute(
            "INSERT OR REPLACE INTO thumbnails "
            "(file_path, channel_id, png_path, layer_count, thumbnail_layer, status) "
            "VALUES (?,?,?,?,?,?)",
            (file_path, channel_id, png_path, layer_count,
             thumbnail_layer, status))
        self._conn.commit()
        # a replaced PNG (re-render, layer change) leaves the old file behind
        if old and old["png_path"] and old["png_path"] != png_path:
            self._delete_png(old["png_path"])

    def delete_file(self, file_path: str) -> None:
        """Remove one file's rows and its PNGs (source deleted / cache reset)."""
        for t in self.get_thumbnails(file_path):
            self._delete_png(t["png_path"])
        self._conn.execute("DELETE FROM thumbnails WHERE file_path=?", (file_path,))
        self._conn.execute("DELETE FROM files WHERE file_path=?", (file_path,))
        self._conn.commit()

    # ------------------------------------------------------------------
    # ratings table — user data: survives re-renders, delete_file and
    # clear_all on purpose
    # ------------------------------------------------------------------

    def get_stars(self, file_path: str, channel_id: str) -> int:
        row = self._conn.execute(
            "SELECT stars FROM ratings WHERE file_path=? AND channel_id=?",
            (file_path, channel_id)).fetchone()
        return int(row["stars"]) if row else 0

    def file_ratings(self, file_path: str) -> dict[str, int]:
        return {r["channel_id"]: int(r["stars"]) for r in self._conn.execute(
            "SELECT channel_id, stars FROM ratings WHERE file_path=?",
            (file_path,))}

    def set_stars(self, file_path: str, channel_id: str, stars: int) -> None:
        stars = max(0, min(5, int(stars)))
        if stars == 0:
            self._conn.execute(
                "DELETE FROM ratings WHERE file_path=? AND channel_id=?",
                (file_path, channel_id))
        else:
            self._conn.execute(
                "INSERT OR REPLACE INTO ratings (file_path, channel_id, stars) "
                "VALUES (?,?,?)", (file_path, channel_id, stars))
        self._conn.commit()

    # ------------------------------------------------------------------
    # PNG files
    # ------------------------------------------------------------------

    def new_png_path(self) -> str:
        return str(self.thumb_dir / f"{uuid.uuid4().hex}.png")

    def _delete_png(self, png_path: str) -> None:
        try:
            if png_path and os.path.isfile(png_path):
                os.remove(png_path)
        except OSError:
            log.debug("Could not delete cached PNG: %s", png_path)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def cleanup_orphan_pngs(self) -> int:
        """Delete cache-dir PNGs with no metadata row (crash leftovers).
        Returns the number of files removed."""
        known = {row["png_path"] for row in
                 self._conn.execute("SELECT png_path FROM thumbnails")}
        removed = 0
        for f in self.thumb_dir.glob("*.png"):
            if str(f) not in known:
                try:
                    f.unlink()
                    removed += 1
                except OSError:
                    pass
        if removed:
            log.info("Thumbnail cache: removed %d orphaned PNGs", removed)
        return removed

    def stats(self) -> dict:
        n_files = self._conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        n_thumbs = self._conn.execute("SELECT COUNT(*) FROM thumbnails").fetchone()[0]
        n_errors = self._conn.execute(
            "SELECT COUNT(*) FROM files WHERE status='error'").fetchone()[0]
        disk = sum(f.stat().st_size for f in self.thumb_dir.glob("*.png"))
        disk += self.db_path.stat().st_size if self.db_path.exists() else 0
        return {"files": n_files, "thumbnails": n_thumbs,
                "errors": n_errors, "disk_bytes": disk}

    def clear_all(self) -> None:
        """Wipe everything — the 'Re-render all thumbnails' button."""
        self._conn.execute("DELETE FROM thumbnails")
        self._conn.execute("DELETE FROM files")
        self._conn.commit()
        for f in self.thumb_dir.glob("*.png"):
            try:
                f.unlink()
            except OSError:
                pass
