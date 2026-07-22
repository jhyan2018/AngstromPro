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

from angstrompro.utils.qt_compat import QtCore, QtWidgets, event_POS

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
    previewable_exts, _LOADERS, _load_generic)
from .scanner import ScannerShared, ScannerBridge, scanner_loop
from . import thumbnail_renderers  # noqa: F401 — registers built-in renderers
from . import pref_widgets         # noqa: F401 — registers db_* pref controls

from angstrompro.gui.widgets.preferences.pref_schema import PrefSection, PrefItem

log = logging.getLogger(__name__)

_FolderRole = QtCore.Qt.ItemDataRole.UserRole


class _StayOpenMenu(QtWidgets.QMenu):
    """Menu of checkable filters: clicking toggles without closing.
    The menu still closes normally on Esc or a click outside."""

    def mouseReleaseEvent(self, event) -> None:
        act = self.actionAt(event_POS(event))
        if act is not None and act.isCheckable():
            act.trigger()   # toggle + emit, but keep the popup open
            return
        super().mouseReleaseEvent(event)


@register_module
class DataBrowserModule(AGuiModule):
    # Persists additional splitter and browser state under established keys.
    persist_window_layout = False

    module_id    = "data_browser"
    display_name = "Data Browser"
    category     = "Basic"
    description  = "Browse measurement folders with cached thumbnails; send any channel to a module."
    accepted_types: set = set()
    # one live instance only: a second browser would run a second scanner
    # thread and duplicate render submissions against the same cache
    max_instances = 1

    preferences_schema = [
        PrefSection("Watch folders", "folder", [
            PrefItem("watch_folders", "", "db_folder_list", full_width=True),
        ]),
        PrefSection("Watched formats", "file-check", [
            # unchecked formats are hidden from the gallery and skipped by
            # the background scanner
            PrefItem("formats.watched", "", "db_format_list", full_width=True),
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
                     "2D data with more curves than this renders as a colormap "
                     "(default 10)",
                     kwargs={"min": 1, "max": 500}),
            PrefItem("thumbnails.template", "Plot template", "db_template_picker",
                     "Curve-stack template applied to thumbnail rendering"),
            PrefItem("thumbnails.z_background_method",
                     "Z thumbnail background", "dropdown",
                     "Optional display-only background subtraction for the "
                     "logical Z channel; source data is unchanged",
                     kwargs={"choices": ["Off", "Polynomial surface",
                                         "Per scan line"]}),
            PrefItem("thumbnails.pixmap_cache_size", "Pixmap cache", "number",
                     "Decoded thumbnails kept in memory",
                     kwargs={"min": 16, "max": 5000}),
        ]),
        PrefSection("Channels — thumbnails follow the app-wide channel "
                    "mappings (load-by-default = rendered)", "settings", [
            # the same ChannelManager the file-open path uses; edits here
            # apply app-wide, not just to the browser
            PrefItem("", "Channel mappings", "channel_manager",
                     full_width=True, expandable=True),
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
                                     str(user_data_subpath("cache", "data_browser"))))
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
        # view-only multi-check format filter — independent of the watched-
        # formats preference; checking a format with no files just matches none
        self._format_btn = QtWidgets.QToolButton()
        self._format_btn.setText("Formats")
        self._format_btn.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self._format_menu = _StayOpenMenu(self._format_btn)
        self._format_btn.setMenu(self._format_menu)
        self._reload_format_menu()
        bar.addWidget(self._format_btn)
        bar.addWidget(QtWidgets.QLabel("Sort:"))
        self._sort_combo = QtWidgets.QComboBox()
        for label, mode in [("Newest first", "mtime_desc"),
                            ("Oldest first", "mtime_asc"),
                            ("Name A→Z",     "name_asc"),
                            ("Name Z→A",     "name_desc"),
                            ("Stars ★→☆",   "stars_desc"),
                            ("Stars ☆→★",   "stars_asc")]:
            self._sort_combo.addItem(label, mode)
        self._sort_combo.currentIndexChanged.connect(self._rescan_current)
        bar.addWidget(self._sort_combo)
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
        self._splitter = splitter

        self._restore_view_state()
        self._subfolders_cb.toggled.connect(self._save_view_state)
        self._sort_combo.currentIndexChanged.connect(self._save_view_state)
        # format menu actions are rebuilt in _reload_format_menu; per-action
        # save hooks are connected there

        self._reload_watch_folders()
        self._start_scanner()

    # ------------------------------------------------------------------
    # View state (QSettings) — transient view choices, not preferences
    # ------------------------------------------------------------------

    _QS_GROUP = "data_browser"

    def _restore_view_state(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        # window geometry, dock layout, splitter position
        geo = qs.value(f"{self._QS_GROUP}/geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        state = qs.value(f"{self._QS_GROUP}/window_state")
        if state is not None:
            self.restoreState(state)
        split = qs.value(f"{self._QS_GROUP}/splitter")
        if split is not None:
            self._splitter.restoreState(split)
        self._subfolders_cb.setChecked(
            qs.value(f"{self._QS_GROUP}/include_subfolders", False, type=bool))
        sort_mode = qs.value(f"{self._QS_GROUP}/sort_mode", "mtime_desc", type=str)
        idx = self._sort_combo.findData(sort_mode)
        if idx >= 0:
            self._sort_combo.setCurrentIndex(idx)
        # store UNCHECKED formats so formats added later default to checked
        unchecked = qs.value(f"{self._QS_GROUP}/formats_unchecked", [], type=list) or []
        for a in self._format_menu.actions():
            a.setChecked(a.text() not in unchecked)

    def _save_window_state(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        qs.setValue(f"{self._QS_GROUP}/geometry", self.saveGeometry())
        qs.setValue(f"{self._QS_GROUP}/window_state", self.saveState())
        qs.setValue(f"{self._QS_GROUP}/splitter", self._splitter.saveState())

    def _save_view_state(self, *_a) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        qs.setValue(f"{self._QS_GROUP}/include_subfolders",
                    self._subfolders_cb.isChecked())
        qs.setValue(f"{self._QS_GROUP}/sort_mode",
                    self._sort_combo.currentData())
        qs.setValue(f"{self._QS_GROUP}/formats_unchecked",
                    [a.text() for a in self._format_menu.actions()
                     if not a.isChecked()])

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
            silent=True,
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
            previewable_exts=self._watched_exts(),
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
        """Resolve the thumbnail template name → rcparams delta + per-mode
        widget extras.  One template serves both stack and colormap branches
        (missing template = bare matplotlib defaults)."""
        from angstrompro.gui.widgets.curve_stack.template_manager import (
            list_templates, load_template)
        name = str(self._cfg("thumbnails.template", ""))
        self._template_delta: dict = {}
        self._template_extras: dict = {}
        if name:
            try:
                if name in list_templates():
                    delta, extras = load_template(name)
                    self._template_delta = delta or {}
                    self._template_extras = extras or {}
                else:
                    log.warning("Thumbnail template %r not found — skipped", name)
            except Exception:
                log.warning("Could not load thumbnail template %r", name, exc_info=True)

    def _apply_config_to_panels(self, cfg: dict) -> None:
        """Live-apply from the preferences panel (base class hooks this in)."""
        self._reload_format_menu()
        self._gallery.set_thumb_size(int(self._cfg("thumbnails.size", 150)))
        self._gallery.gallery_model().set_pixmap_cache_size(
            int(self._cfg("thumbnails.pixmap_cache_size", 200)))
        self._reload_template_delta()
        # Most preferences do not affect the folder tree.  Rebuilding it on
        # every Apply collapses expanded nodes and lets Qt move the current
        # index to the first root item when the dialog closes.
        current_roots = [
            os.path.normcase(os.path.normpath(
                self._tree.topLevelItem(i).data(0, _FolderRole)))
            for i in range(self._tree.topLevelItemCount())
        ]
        configured_roots = [os.path.normcase(os.path.normpath(p))
                            for p in self._watch_folders()]
        if current_roots != configured_roots:
            self._reload_watch_folders()
        self._push_scanner_settings()
        self._rescan_current()

    # ------------------------------------------------------------------
    # Watch folder tree
    # ------------------------------------------------------------------

    def _reload_format_menu(self) -> None:
        """Toolbar view filter: one checkbox per readable format, all checked
        by default.  Purely a view filter — never touches the watch config."""
        if not hasattr(self, "_format_menu"):
            return
        previous = {a.text(): a.isChecked() for a in self._format_menu.actions()}
        self._format_menu.clear()
        for ext in sorted(previewable_exts()):
            act = self._format_menu.addAction(ext)
            act.setCheckable(True)
            act.setChecked(previous.get(ext, True))
            act.toggled.connect(self._rescan_current)
            act.toggled.connect(self._save_view_state)

    def _view_filter_exts(self) -> set:
        return {a.text() for a in self._format_menu.actions() if a.isChecked()}

    def _watched_exts(self) -> set:
        """Formats checked in preferences ∩ formats the app can read.
        "*" (default) = every readable format, including ones plugins
        register later."""
        readable = previewable_exts()
        watched = self._cfg("formats.watched", ["*"])
        if "*" in watched:
            return readable
        return {str(e).lower() for e in watched} & readable

    def _watch_folders(self) -> list[str]:
        return [p for p in self._cfg("watch_folders", []) if os.path.isdir(p)]

    def _reload_watch_folders(self) -> None:
        """Rebuild changed roots without resetting the user's tree context."""
        expanded: set[str] = set()

        def _key(path: str) -> str:
            return os.path.normcase(os.path.normpath(path))

        def _remember(item) -> None:
            folder = item.data(0, _FolderRole)
            if folder and item.isExpanded():
                expanded.add(_key(folder))
            for j in range(item.childCount()):
                _remember(item.child(j))

        for i in range(self._tree.topLevelItemCount()):
            _remember(self._tree.topLevelItem(i))

        current = self._tree.currentItem()
        selected_path = (current.data(0, _FolderRole) if current is not None
                         else self._current_folder)
        selected_key = _key(selected_path) if selected_path else ""
        restored_current = None

        # Suppress currentItemChanged/itemExpanded while reconstructing.  The
        # gallery already represents selected_path and should not jump folders.
        blocker = QtCore.QSignalBlocker(self._tree)
        try:
            self._tree.clear()
            for folder in self._watch_folders():
                item = QtWidgets.QTreeWidgetItem(self._tree, [Path(folder).name])
                item.setData(0, _FolderRole, folder)
                item.setToolTip(0, folder)
                self._add_placeholder_child(item)

            def _restore(item) -> None:
                nonlocal restored_current
                folder = item.data(0, _FolderRole) or ""
                folder_key = _key(folder) if folder else ""
                if folder_key == selected_key:
                    restored_current = item
                if folder_key in expanded:
                    self._populate_subfolders(item)
                    item.setExpanded(True)
                    for j in range(item.childCount()):
                        _restore(item.child(j))

            for i in range(self._tree.topLevelItemCount()):
                _restore(self._tree.topLevelItem(i))

            self._tree.setCurrentItem(restored_current)
        finally:
            del blocker

        if selected_path and restored_current is None:
            # The selected folder was removed from the configured roots.
            self._current_folder = ""
            self._rescan_current()
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

        # visible = watched (preference, also drives the scanner)
        #         ∩ view filter (toolbar checkboxes, view-only)
        exts = self._watched_exts() & self._view_filter_exts()

        files: list[tuple[str, float]] = []
        for root, dirs, names in os.walk(folder):
            for n in names:
                if Path(n).suffix.lower() in exts \
                        and (not needle or needle in n.lower()):
                    p = os.path.join(root, n)
                    try:
                        files.append((p, os.path.getmtime(p)))
                    except OSError:
                        continue
            if not recursive:
                dirs.clear()
        sort_mode = (self._sort_combo.currentData()
                     if hasattr(self, "_sort_combo") else "mtime_desc")
        if sort_mode == "name_asc":
            files.sort(key=lambda t: os.path.basename(t[0]).lower())
        elif sort_mode == "name_desc":
            files.sort(key=lambda t: os.path.basename(t[0]).lower(), reverse=True)
        else:   # mtime_* and stars_* start from a time ordering
            files.sort(key=lambda t: t[1], reverse=(sort_mode != "mtime_asc"))
        self._current_files = files

        rows: list[CardRow] = []
        n_cached = 0
        for path, mtime in files:
            file_rows = self._rows_for_file(path, mtime, folder)
            if file_rows and file_rows[0].state != STATE_LOADING:
                n_cached += 1
            rows.extend(file_rows)
        if sort_mode in ("stars_desc", "stars_asc"):
            # stars are per card — stable sort keeps the time order within
            # equal ratings
            rows.sort(key=lambda r: r.stars, reverse=(sort_mode == "stars_desc"))
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
            ratings = self._cache.file_ratings(path)
            rows = []
            for t in self._cache.get_thumbnails(path):
                rows.append(self._row_from_thumb(path, filename, rel, t,
                                                 ratings.get(t["channel_id"], 0)))
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
    def _row_from_thumb(path: str, filename: str, rel: str, t: dict,
                        stars: int = 0) -> CardRow:
        status_map = {"ok": STATE_READY, "not_found": STATE_NOT_FOUND,
                      "no_renderer": STATE_ICON}
        info = ""
        if t["layer_count"] > 1:
            info = f"3D · layer {t['thumbnail_layer']}/{t['layer_count']}"
        tooltip = f"{path}\n{t['channel_id']}"
        if t["status"] == "not_found":
            tooltip += ("\n\nThis file has no channel matching the aliases of "
                        f"'{t['channel_id']}'.\nConfigure channel names/aliases in "
                        "Preferences → Channel mappings\n(shared with file opening).")
        return CardRow(key=(path, t["channel_id"]), filename=filename,
                       channel=t["channel_id"], info=info, rel_path=rel,
                       png_path=t["png_path"],
                       state=status_map.get(t["status"], STATE_ICON),
                       tooltip=tooltip, stars=stars)

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
        options = {"stack_threshold": int(self._cfg("thumbnails.stack_threshold", 10)),
                   "z_background_method": str(self._cfg(
                       "thumbnails.z_background_method", "Polynomial surface")),
                   "widget_extras": dict(self._template_extras),
                   "figsize": (self._cfg("thumbnails.size", 150) / 58,) * 2}
        if layer is not None:
            options["layer"] = layer
        request = TaskRequest(
            task_func=render_file_task,
            source_id=self.instance_id,
            task_type="thumbnail_render",
            kwargs={"file_path": path,
                    "cache_dir": str(self._cache.thumb_dir),   # PNGs live in the subfolder
                    "channel_cfg": self._channel_cfg_for(path),
                    "rcparams_delta": dict(self._template_delta),
                    "options": options},
            backend="io",
            priority=priority,
            cancellable=True,
            silent=True,
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
            ratings = self._cache.file_ratings(path)
            rows = [self._row_from_thumb(path, filename, rel, t,
                                         ratings.get(t["channel_id"], 0))
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

        star_actions: dict = {}
        if channel_id != "?":
            current = self._cache.get_stars(path, channel_id)
            rating_menu = menu.addMenu("Rating")
            for n in range(6):
                label = "☆ none" if n == 0 else "★" * n
                a = rating_menu.addAction(label)
                a.setCheckable(True)
                a.setChecked(n == current)
                star_actions[a] = n

        menu.addSeparator()
        act_rerender = menu.addAction("Re-render thumbnail")

        act = menu.exec(global_pos)
        if act is None:
            return
        if act in star_actions:
            stars = star_actions[act]
            self._cache.set_stars(path, channel_id, stars)
            self._gallery.gallery_model().update_row(key, stars=stars)
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
        self._save_window_state()
        for handle in self._pending.values():
            try:
                handle.cancel()
            except Exception:
                pass
        super().closeEvent(event)

    def save_state_for_exit(self) -> None:
        self._save_window_state()
        self._save_view_state()
        super().save_state_for_exit()

    def shutdown(self) -> None:
        """Stop the scanner and release the main-thread cache connection."""
        self._save_window_state()
        if getattr(self, "_scanner_handle", None) is not None:
            try:
                self._scanner_handle.cancel()
            except Exception:
                pass
            self._scanner_handle = None
        cache = getattr(self, "_cache", None)
        if cache is not None:
            cache.close_quiet()
            self._cache = None
