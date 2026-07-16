# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

DataBrowser — the disk → app front door.

Left: watch-folder tree (folders only, lazily populated).
Right: virtual thumbnail gallery (GalleryView).

Coordinator role (all on the main thread, no locks):
  _pending      file_path → TaskHandle   deduplicates render submissions
  _task_file    task_id  → file_path     routes error signals back
  cache         ThumbnailCache           SQLite WAL + uuid PNGs

Flow: folder click → fresh os.scandir (listings are never cached) →
rows from cache (fresh) or provisional "Loading" cards → viewport_settled
→ HIGH render tasks for uncached visible files → _on_render_done writes
the cache and swaps cards in place.

Send is a courier: load the channel, add a workspace item, run the
standard send dialog/transfer, then remove the item — the browser's
workspace stays empty except during the hand-off.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from angstrompro.utils.qt_compat import QtCore, QtWidgets

from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.tasks import TaskRequest
from angstrompro.app.user_data_folder import user_data_subpath

from .gallery_widget import (
    GalleryView, CardRow,
    STATE_READY, STATE_LOADING, STATE_ERROR, STATE_NOT_FOUND, STATE_ICON)
from .thumbnail_cache import ThumbnailCache
from .render_task import (
    render_file_task, channel_cfg_to_plain, MULTI_CHANNEL_FORMATS,
    _LOADERS, _load_generic)
from .scanner import ScannerShared, ScannerBridge, scanner_loop
from . import thumbnail_renderers  # noqa: F401 — registers built-in renderers
from . import pref_widgets         # noqa: F401 — registers db_* pref controls

from angstrompro.gui.widgets.preferences.pref_schema import PrefSection, PrefItem

log = logging.getLogger(__name__)

PREVIEWABLE_EXTS = set(MULTI_CHANNEL_FORMATS) | {".uds", ".scplot"}

_FolderRole = QtCore.Qt.ItemDataRole.UserRole


@register_module
class DataBrowserModule(AGuiModule):
    module_id    = "data_browser"
    display_name = "Data Browser"
    category     = "Basic"
    description  = "Browse measurement folders with cached thumbnails; send any channel to a module."
    accepted_types: set = set()

    preferences_schema = [
        PrefSection("Watch folders", "folder", [
            PrefItem("watch_folders", "", "db_folder_list", full_width=True),
        ]),
        PrefSection("Background scanner", "radar", [
            PrefItem("scanner.enabled", "Enable scanning", "checkbox",
                     "Pre-render thumbnails for all watch folders in the background"),
            PrefItem("scanner.request_interval", "Request interval (s)", "number",
                     "Pause between background render requests",
                     kwargs={"min": 0.1, "max": 60.0}),
            PrefItem("scanner.idle_interval", "Idle interval (s)", "number",
                     "Sleep between full passes when nothing changed",
                     kwargs={"min": 5.0, "max": 3600.0}),
            PrefItem("scanner.order", "Scan order", "dropdown",
                     "Order files are pre-rendered within each folder",
                     kwargs={"choices": ["newest_first", "oldest_first", "name"]}),
        ]),
        PrefSection("Thumbnails", "photo", [
            PrefItem("thumbnails.size", "Thumbnail size (px)", "number",
                     "Card image size; also sets the render figure size",
                     kwargs={"min": 80, "max": 400}),
            PrefItem("thumbnails.stack_threshold", "Stack threshold", "number",
                     "2D data with more curves than this renders as a colormap",
                     kwargs={"min": 1, "max": 500}),
            PrefItem("thumbnails.template", "Plot template", "db_template_picker",
                     "Curve-stack template applied to thumbnail rendering"),
            PrefItem("thumbnails.pixmap_cache_size", "Pixmap cache", "number",
                     "Decoded thumbnails kept in memory",
                     kwargs={"min": 16, "max": 5000}),
        ]),
        PrefSection("Cache", "database", [
            PrefItem("cache.cleanup_orphans", "Clean orphans at startup", "checkbox",
                     "Remove crash-leftover PNGs when the module starts"),
            PrefItem("cache.tools", "", "db_cache_tools", full_width=True),
        ]),
    ]

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        self._cache = ThumbnailCache(self._cfg("cache.dir",
                                     str(user_data_subpath("data_browser_cache"))))
        if self._cfg("cache.cleanup_orphans", True):
            self._cache.cleanup_orphan_pngs()
        self._reload_template_delta()

        self._pending: dict[str, object] = {}     # file_path → TaskHandle
        self._task_file: dict[str, str] = {}      # task_id → file_path
        self._current_files: list[tuple[str, float]] = []   # (path, mtime) listed now
        self._current_folder = ""

        splitter = QtWidgets.QSplitter()

        # left: watch-folder tree
        left = QtWidgets.QWidget()
        lv = QtWidgets.QVBoxLayout(left)
        lv.setContentsMargins(4, 4, 4, 4)
        lv.setSpacing(4)
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemExpanded.connect(self._on_tree_expanded)
        self._tree.itemCollapsed.connect(lambda _i: self._update_watched_paths())
        self._tree.currentItemChanged.connect(self._on_folder_selected)
        lv.addWidget(self._tree)
        self._subfolders_cb = QtWidgets.QCheckBox("include subfolders")
        self._subfolders_cb.toggled.connect(self._rescan_current)
        lv.addWidget(self._subfolders_cb)
        row = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Add folder…")
        btn_add.clicked.connect(self._on_add_watch_folder)
        btn_rm = QtWidgets.QPushButton("Remove")
        btn_rm.clicked.connect(self._on_remove_watch_folder)
        row.addWidget(btn_add)
        row.addWidget(btn_rm)
        lv.addLayout(row)
        splitter.addWidget(left)

        # right: search bar + gallery + status
        right = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(4, 4, 4, 4)
        rv.setSpacing(4)
        bar = QtWidgets.QHBoxLayout()
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("filter by filename…")
        self._search.textChanged.connect(self._rescan_current)
        bar.addWidget(self._search)
        rv.addLayout(bar)
        self._gallery = GalleryView(thumb_size=int(self._cfg("thumbnails.size", 150)))
        self._gallery.gallery_model().set_pixmap_cache_size(
            int(self._cfg("thumbnails.pixmap_cache_size", 200)))
        self._gallery.viewport_settled.connect(self._on_viewport_settled)
        self._gallery.send_requested.connect(self._on_send_card)
        self._gallery.context_menu_requested.connect(self._on_card_menu)
        rv.addWidget(self._gallery)
        self._status = QtWidgets.QLabel("")
        rv.addWidget(self._status)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 700])
        self.setCentralWidget(splitter)

        self._reload_watch_folders()
        self._start_scanner()

        from angstrompro.utils.qt_compat import QtGui
        _QShortcut = getattr(QtGui, "QShortcut", None) or QtWidgets.QShortcut
        sc = _QShortcut(QtGui.QKeySequence("F5"), self)
        sc.activated.connect(self._refresh_tree)

        # live updates: watch expanded tree folders + the gallery folder.
        # bursts of fs events (file copies, saves) are debounced to one refresh
        self._fs_watcher = QtCore.QFileSystemWatcher(self)
        self._fs_watcher.directoryChanged.connect(self._on_fs_changed)
        self._fs_pending: set[str] = set()
        self._fs_debounce = QtCore.QTimer(self)
        self._fs_debounce.setSingleShot(True)
        self._fs_debounce.setInterval(300)
        self._fs_debounce.timeout.connect(self._apply_fs_changes)
        self._update_watched_paths()

    # ------------------------------------------------------------------
    # Background scanner
    # ------------------------------------------------------------------

    def _start_scanner(self) -> None:
        self._scanner_shared = ScannerShared()
        self._scanner_bridge = ScannerBridge(self)
        self._scanner_bridge.render_requested.connect(self._on_scanner_request)
        self._push_scanner_settings()

        request = TaskRequest(
            task_func=scanner_loop,
            source_id=self.instance_id,
            task_type="thumbnail_scanner",
            kwargs={"cache_dir": str(self._cache.cache_dir),
                    "shared": self._scanner_shared,
                    "bridge": self._scanner_bridge},
            backend="persistent",
            priority="low",
            cancellable=True,
        )
        self._scanner_handle = self._context.tasks.submit(request)
        # cancel the loop before the event loop dies so the thread exits cleanly
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def _push_scanner_settings(self) -> None:
        """Refresh the scanner's lock-protected settings snapshot."""
        self._scanner_shared.update(
            enabled=bool(self._cfg("scanner.enabled", True)),
            watch_folders=list(self._cfg("watch_folders", [])),
            previewable_exts=PREVIEWABLE_EXTS,
            request_interval=float(self._cfg("scanner.request_interval", 1.5)),
            idle_interval=float(self._cfg("scanner.idle_interval", 60.0)),
            scan_order=str(self._cfg("scanner.order", "newest_first")),
        )

    def _on_scanner_request(self, path: str) -> None:
        """Queued from the scanner thread — submit a LOW render on the main thread."""
        if path in self._pending:
            return
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return
        if not self._cache.should_render(path, mtime):
            return   # rendered since the scanner looked
        self._submit_render(path, priority="low")

    def _cfg(self, path: str, default):
        """Dot-path lookup into the module config dict."""
        node = self._config
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def _reload_template_delta(self) -> None:
        """Resolve the thumbnail template name → rcparams delta (missing = skip)."""
        from angstrompro.gui.widgets.curve_stack.template_manager import (
            list_templates, load_template)
        name = str(self._cfg("thumbnails.template", ""))
        self._template_delta: dict = {}
        if name:
            try:
                if name in list_templates():
                    delta, _extras = load_template(name)
                    self._template_delta = delta or {}
                else:
                    log.warning("Thumbnail template %r not found — skipped", name)
            except Exception:
                log.warning("Could not load thumbnail template %r", name, exc_info=True)

    def _apply_config_to_panels(self, cfg: dict) -> None:
        """Live-apply from the preferences panel (base class hooks this in)."""
        self._gallery.set_thumb_size(int(self._cfg("thumbnails.size", 150)))
        self._gallery.gallery_model().set_pixmap_cache_size(
            int(self._cfg("thumbnails.pixmap_cache_size", 200)))
        self._reload_template_delta()
        self._reload_watch_folders()
        self._push_scanner_settings()
        self._rescan_current()

    # ------------------------------------------------------------------
    # Watch folder tree
    # ------------------------------------------------------------------

    def _watch_folders(self) -> list[str]:
        return [p for p in self._cfg("watch_folders", []) if os.path.isdir(p)]

    def _reload_watch_folders(self) -> None:
        self._tree.clear()
        for folder in self._watch_folders():
            item = QtWidgets.QTreeWidgetItem(self._tree, [Path(folder).name])
            item.setData(0, _FolderRole, folder)
            item.setToolTip(0, folder)
            self._add_placeholder_child(item)
        self._update_watched_paths()

    def _add_placeholder_child(self, item) -> None:
        if any(e.is_dir() for e in self._safe_scandir(item.data(0, _FolderRole))):
            QtWidgets.QTreeWidgetItem(item, ["…"])

    @staticmethod
    def _safe_scandir(folder: str):
        try:
            return list(os.scandir(folder))
        except OSError:
            return []

    def _populate_subfolders(self, item) -> None:
        """(Re-)scan the folder's subfolders on every expand, so folders
        created after the first expansion appear on collapse/expand or F5.
        Grandchildren re-scan lazily on their own expand, so losing their
        placeholder state here is harmless."""
        folder = item.data(0, _FolderRole)
        item.takeChildren()
        for e in sorted(self._safe_scandir(folder), key=lambda e: e.name.lower()):
            if e.is_dir():
                child = QtWidgets.QTreeWidgetItem(item, [e.name])
                child.setData(0, _FolderRole, e.path)
                child.setToolTip(0, e.path)
                self._add_placeholder_child(child)

    def _on_tree_expanded(self, item) -> None:
        self._populate_subfolders(item)
        self._update_watched_paths()

    # ------------------------------------------------------------------
    # File system watcher
    # ------------------------------------------------------------------

    def _update_watched_paths(self) -> None:
        """Watch every expanded tree folder plus the current gallery folder."""
        if not hasattr(self, "_fs_watcher"):
            return   # build_ui still initialising
        wanted: set[str] = set()

        def _walk(item):
            folder = item.data(0, _FolderRole)
            if folder and os.path.isdir(folder):
                wanted.add(folder)
            if item.isExpanded():
                for i in range(item.childCount()):
                    _walk(item.child(i))
        for i in range(self._tree.topLevelItemCount()):
            _walk(self._tree.topLevelItem(i))
        if self._current_folder and os.path.isdir(self._current_folder):
            wanted.add(self._current_folder)

        current = set(self._fs_watcher.directories())
        stale = list(current - wanted)
        fresh = list(wanted - current)
        if stale:
            self._fs_watcher.removePaths(stale)
        if fresh:
            self._fs_watcher.addPaths(fresh)

    def _on_fs_changed(self, path: str) -> None:
        self._fs_pending.add(path)
        self._fs_debounce.start()   # restart — bursts collapse into one apply

    def _apply_fs_changes(self) -> None:
        pending, self._fs_pending = self._fs_pending, set()
        rescan_gallery = False

        def _walk(item):
            nonlocal rescan_gallery
            folder = item.data(0, _FolderRole)
            if folder in pending and item.isExpanded():
                self._populate_subfolders(item)
            for i in range(item.childCount()):
                _walk(item.child(i))
        for i in range(self._tree.topLevelItemCount()):
            _walk(self._tree.topLevelItem(i))

        cur = self._current_folder
        if cur:
            if cur in pending:
                rescan_gallery = True
            elif self._subfolders_cb.isChecked():
                # recursive scope: a change anywhere under the current folder
                # affects the listing
                rescan_gallery = any(
                    os.path.commonpath([p, cur]) == os.path.normpath(cur)
                    for p in map(os.path.normpath, pending)
                    if os.path.splitdrive(p)[0] == os.path.splitdrive(cur)[0])
        if rescan_gallery:
            self._rescan_current()
        self._update_watched_paths()

    def _refresh_tree(self) -> None:
        """F5: re-scan expanded tree nodes in place and re-list the gallery."""
        def _walk(item):
            if item.isExpanded():
                self._populate_subfolders(item)
                for i in range(item.childCount()):
                    _walk(item.child(i))
        for i in range(self._tree.topLevelItemCount()):
            _walk(self._tree.topLevelItem(i))
        self._rescan_current()

    def _on_add_watch_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Add watch folder")
        if not folder:
            return
        folder = os.path.normpath(folder)
        existing = [os.path.normpath(p) for p in self._cfg("watch_folders", [])]
        for other in existing:
            common = os.path.commonpath([folder, other]) if \
                os.path.splitdrive(folder)[0] == os.path.splitdrive(other)[0] else ""
            if common in (folder, other) and common:
                QtWidgets.QMessageBox.warning(
                    self, "Nested watch folders",
                    f"'{folder}' and '{other}' overlap.\n"
                    "Watch folders must not be subfolders of each other.")
                return
        self._config.setdefault("watch_folders", []).append(folder)
        self._reload_watch_folders()
        self._push_scanner_settings()

    def _on_remove_watch_folder(self) -> None:
        item = self._tree.currentItem()
        if item is None or item.parent() is not None:
            return   # only top-level entries are watch folders
        folder = item.data(0, _FolderRole)
        folders = self._cfg("watch_folders", [])
        if folder in folders:
            folders.remove(folder)
        self._reload_watch_folders()
        self._push_scanner_settings()

    # ------------------------------------------------------------------
    # Folder listing → gallery rows
    # ------------------------------------------------------------------

    def _on_folder_selected(self, current, _prev=None) -> None:
        if current is None:
            return
        self._current_folder = current.data(0, _FolderRole) or ""
        self._rescan_current()
        self._update_watched_paths()

    def _rescan_current(self, *_a) -> None:
        folder = self._current_folder
        if not folder or not os.path.isdir(folder):
            self._gallery.gallery_model().set_rows([])
            self._current_files = []
            self._status.setText("")
            return

        recursive = self._subfolders_cb.isChecked()
        needle = self._search.text().strip().lower()
        self._gallery.set_show_rel_path(recursive)

        files: list[tuple[str, float]] = []
        for root, dirs, names in os.walk(folder):
            for n in names:
                if Path(n).suffix.lower() in PREVIEWABLE_EXTS \
                        and (not needle or needle in n.lower()):
                    p = os.path.join(root, n)
                    try:
                        files.append((p, os.path.getmtime(p)))
                    except OSError:
                        continue
            if not recursive:
                dirs.clear()
        files.sort(key=lambda t: t[1], reverse=True)   # newest first
        self._current_files = files

        rows: list[CardRow] = []
        n_cached = 0
        for path, mtime in files:
            file_rows = self._rows_for_file(path, mtime, folder)
            if file_rows and file_rows[0].state != STATE_LOADING:
                n_cached += 1
            rows.extend(file_rows)
        self._gallery.gallery_model().set_rows(rows)
        self._status.setText(
            f"{len(files)} files · {n_cached} cached · {len(rows)} cards")
        self._gallery.settle_now()

    def _rows_for_file(self, path: str, mtime: float,
                       base_folder: str) -> list[CardRow]:
        filename = os.path.basename(path)
        rel = os.path.relpath(path, base_folder)
        rel = "" if rel == filename else rel

        if self._cache.is_fresh(path, mtime):
            rows = []
            for t in self._cache.get_thumbnails(path):
                rows.append(self._row_from_thumb(path, filename, rel, t))
            if rows:
                return rows
        f = self._cache.get_file(path)
        if f is not None and f["status"] == "error" \
                and f["mtime"] == mtime and f["retry_count"] >= 3:
            return [CardRow(key=(path, "?"), filename=filename, rel_path=rel,
                            state=STATE_ERROR, tooltip=path)]
        # unknown / stale → one provisional loading card
        return [CardRow(key=(path, "?"), filename=filename, rel_path=rel,
                        state=STATE_LOADING, tooltip=path)]

    @staticmethod
    def _row_from_thumb(path: str, filename: str, rel: str, t: dict) -> CardRow:
        status_map = {"ok": STATE_READY, "not_found": STATE_NOT_FOUND,
                      "no_renderer": STATE_ICON}
        info = ""
        if t["layer_count"] > 1:
            info = f"3D · layer {t['thumbnail_layer']}/{t['layer_count']}"
        return CardRow(key=(path, t["channel_id"]), filename=filename,
                       channel=t["channel_id"], info=info, rel_path=rel,
                       png_path=t["png_path"],
                       state=status_map.get(t["status"], STATE_ICON),
                       tooltip=f"{path}\n{t['channel_id']}")

    # ------------------------------------------------------------------
    # Render submission (coordinator)
    # ------------------------------------------------------------------

    def _on_viewport_settled(self, keys: list) -> None:
        listed = dict(self._current_files)
        for key in keys:
            path = key[0]
            mtime = listed.get(path)
            if mtime is None or path in self._pending:
                continue
            if not self._cache.should_render(path, mtime):
                continue
            self._submit_render(path, priority="high")

    def _channel_cfg_for(self, path: str) -> list[dict]:
        fmt_id = MULTI_CHANNEL_FORMATS.get(Path(path).suffix.lower())
        if fmt_id is None:
            return []
        return channel_cfg_to_plain(self._context.channel_manager.get(fmt_id))

    def _submit_render(self, path: str, priority: str = "high",
                       layer: int | None = None) -> None:
        options = {"stack_threshold": int(self._cfg("thumbnails.stack_threshold", 20)),
                   "figsize": (self._cfg("thumbnails.size", 150) / 58,) * 2}
        if layer is not None:
            options["layer"] = layer
        request = TaskRequest(
            task_func=render_file_task,
            source_id=self.instance_id,
            task_type="thumbnail_render",
            kwargs={"file_path": path,
                    "cache_dir": str(self._cache.cache_dir),
                    "channel_cfg": self._channel_cfg_for(path),
                    "rcparams_delta": dict(self._template_delta),
                    "options": options},
            backend="io",
            priority=priority,
            cancellable=True,
        )
        handle = self._context.tasks.submit(request)
        self._pending[path] = handle
        self._task_file[request.task_id] = path
        handle.result.connect(self._on_render_done)
        handle.error.connect(self._on_render_error)
        handle.cancelled.connect(self._on_render_cancelled)

    def _on_render_done(self, task_id: str, result: dict) -> None:
        path = self._task_file.pop(task_id, None)
        if path is not None:
            self._pending.pop(path, None)
        if not result:
            return   # cancelled mid-task
        path = result["file_path"]
        self._cache.upsert_file(path, result["mtime"], result["format"],
                                result["channels"])
        for t in result["thumbs"]:
            self._cache.upsert_thumbnail(
                path, t["channel_id"], t["png_path"],
                layer_count=t["layer_count"],
                thumbnail_layer=t["thumbnail_layer"],
                status=t["status"] if t["status"] != "no_renderer" else "no_renderer")
        # update gallery if this file is in the current listing
        model = self._gallery.gallery_model()
        if any(p == path for p, _ in self._current_files):
            filename = os.path.basename(path)
            rel = os.path.relpath(path, self._current_folder)
            rel = "" if rel == filename else rel
            rows = [self._row_from_thumb(path, filename, rel, t)
                    for t in self._cache.get_thumbnails(path)]
            if rows:
                model.replace_file_rows(path, rows)
            else:
                model.update_row((path, "?"), state=STATE_ICON)

    def _on_render_error(self, task_id: str, error_text: str) -> None:
        path = self._task_file.pop(task_id, None)
        if path is None:
            return
        self._pending.pop(path, None)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0.0
        self._cache.record_error(path, mtime)
        self._gallery.gallery_model().update_row(
            (path, "?"), state=STATE_ERROR, tooltip=error_text.splitlines()[-1])
        log.warning("Thumbnail render failed for %s:\n%s", path, error_text)

    def _on_render_cancelled(self, task_id: str) -> None:
        path = self._task_file.pop(task_id, None)
        if path is not None:
            self._pending.pop(path, None)

    # ------------------------------------------------------------------
    # Send (courier)
    # ------------------------------------------------------------------

    def _load_channel_payload(self, path: str, channel_id: str):
        """Load one channel of *path* headlessly; returns payload or None."""
        p = Path(path)
        loader = _LOADERS.get(p.suffix.lower())
        if loader is not None:
            cfg = [cc for cc in self._channel_cfg_for(path)
                   if cc["display_name"] == channel_id]
            if cfg:
                cfg = [{**cfg[0], "load_by_default": True}]
                _channels, payloads, _missing = loader(p, cfg)
                if payloads:
                    return payloads[0][1]
            return None
        payloads = _load_generic(p)
        return payloads[0][1] if payloads else None

    def _on_send_card(self, key: tuple) -> None:
        path, channel_id = key
        row = self._gallery.gallery_model().row_for_key(key)
        if row is not None and row.state in (STATE_ERROR, STATE_NOT_FOUND):
            return
        try:
            QtWidgets.QApplication.setOverrideCursor(
                QtCore.Qt.CursorShape.WaitCursor)
            payload = self._load_channel_payload(path, channel_id)
        except Exception as exc:
            QtWidgets.QApplication.restoreOverrideCursor()
            QtWidgets.QMessageBox.critical(self, "Load failed", str(exc))
            return
        QtWidgets.QApplication.restoreOverrideCursor()
        if payload is None:
            QtWidgets.QMessageBox.warning(
                self, "Load failed", f"Could not load '{channel_id}' from\n{path}")
            return
        if not payload.name:
            payload.name = Path(path).stem

        item = self.workspace.add_item(payload=payload)
        item_name = item.name if item is not None else payload.name

        from angstrompro.gui.dialogs.send_item_dialog import SendItemDialog
        dlg = SendItemDialog(self._context, exclude_instance_id=self.instance_id,
                             parent=self)
        sent = False
        if dlg.exec() and dlg.selected_module:
            target = dlg.selected_module
            self._context.workspace_manager.transfer_item(
                src_workspace_id=self.workspace.workspace_id,
                dst_workspace_id=target.workspace.workspace_id,
                item_name=item_name,
            )
            sent = True
        # transfer_item COPIES.  Successful send follows the app-level
        # delete_after_send preference (same rule as every module); a
        # cancelled send always drops the temporary courier copy.
        if sent:
            self._after_send(item_name)
        elif self.workspace.has_item(item_name):
            self.workspace.remove_item(item_name)

    # ------------------------------------------------------------------
    # Card context menu
    # ------------------------------------------------------------------

    def _on_card_menu(self, key: tuple, global_pos) -> None:
        path, channel_id = key
        row = self._gallery.gallery_model().row_for_key(key)
        menu = QtWidgets.QMenu(self)
        act_send = menu.addAction("Send to module…")
        act_send.setEnabled(row is not None and
                            row.state not in (STATE_ERROR, STATE_NOT_FOUND))
        t = self._cache.get_thumbnail(path, channel_id) if channel_id != "?" else None
        act_layer = None
        if t is not None and t["layer_count"] > 1:
            act_layer = menu.addAction("Set thumbnail layer…")
        menu.addSeparator()
        act_rerender = menu.addAction("Re-render thumbnail")

        act = menu.exec(global_pos)
        if act is None:
            return
        if act == act_send:
            self._on_send_card(key)
        elif act_layer is not None and act == act_layer:
            layer, ok = QtWidgets.QInputDialog.getInt(
                self, "Thumbnail layer",
                f"Layer for {channel_id} (0–{t['layer_count'] - 1}):",
                t["thumbnail_layer"], 0, t["layer_count"] - 1)
            if ok:
                self._rerender_file(path, layer=layer)
        elif act == act_rerender:
            self._rerender_file(path)

    def _rerender_file(self, path: str, layer: int | None = None) -> None:
        if path in self._pending:
            return
        self._cache.delete_file(path)
        model = self._gallery.gallery_model()
        for key in list(model.keys()):
            if key[0] == path:
                model.update_row(key, state=STATE_LOADING)
        self._submit_render(path, priority="high", layer=layer)

    # ------------------------------------------------------------------
    # Module hooks
    # ------------------------------------------------------------------

    def on_item_loaded(self, item) -> None:
        """The browser sends data out; it does not display workspace items."""

    def closeEvent(self, event) -> None:
        # base class hides (module keeps living) — the scanner keeps working
        # in the background; that is its purpose.  Only in-flight viewport
        # renders are cancelled: their results have no viewer anyway, and
        # completed ones still land in the cache.
        for handle in self._pending.values():
            try:
                handle.cancel()
            except Exception:
                pass
        super().closeEvent(event)

    def shutdown(self) -> None:
        """Stop the scanner thread (app exit / module removal)."""
        if getattr(self, "_scanner_handle", None) is not None:
            try:
                self._scanner_handle.cancel()
            except Exception:
                pass
            self._scanner_handle = None
