# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

Custom preference controls for the Data Browser, registered with the
schema-based PreferencesPanel:

folder_list      reorderable watch-folder list (add / remove / up / down)
                 with the no-nesting rule enforced on add
template_picker  "(none)" + saved curve-stack templates
cache_tools      cache stats + orphan sweep + full re-render reset
"""
from __future__ import annotations

import os

from angstrompro.utils.qt_compat import QtCore, QtWidgets

from angstrompro.gui.widgets.preferences.pref_schema import register_widget_type


class FolderListControl(QtWidgets.QWidget):
    """get/set a list[str] of watch folders; order = scan order."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._list = QtWidgets.QListWidget()
        self._list.setMinimumHeight(110)
        lay.addWidget(self._list, stretch=1)
        col = QtWidgets.QVBoxLayout()
        for text, slot in (("Add…", self._add), ("Remove", self._remove),
                           ("Up", self._up), ("Down", self._down)):
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(slot)
            col.addWidget(b)
        col.addStretch()
        lay.addLayout(col)

    # PreferencesPanel contract
    def get_value(self) -> list:
        return [self._list.item(i).text() for i in range(self._list.count())]

    def set_value(self, v) -> None:
        self._list.clear()
        for p in (v or []):
            self._list.addItem(str(p))

    # actions
    def _add(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Add watch folder")
        if not folder:
            return
        folder = os.path.normpath(folder)
        for other in self.get_value():
            other = os.path.normpath(other)
            if os.path.splitdrive(folder)[0] != os.path.splitdrive(other)[0]:
                continue
            common = os.path.commonpath([folder, other])
            if common in (folder, other):
                QtWidgets.QMessageBox.warning(
                    self, "Nested watch folders",
                    f"'{folder}' and '{other}' overlap.\n"
                    "Watch folders must not be subfolders of each other.")
                return
        self._list.addItem(folder)

    def _remove(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)

    def _move(self, delta: int) -> None:
        row = self._list.currentRow()
        new = row + delta
        if row < 0 or not (0 <= new < self._list.count()):
            return
        item = self._list.takeItem(row)
        self._list.insertItem(new, item)
        self._list.setCurrentRow(new)

    def _up(self) -> None:
        self._move(-1)

    def _down(self) -> None:
        self._move(+1)


class FormatListControl(QtWidgets.QWidget):
    """Check which previewable file formats the browser watches.
    Unchecked formats are hidden from the gallery and skipped by the
    background scanner.  get/set a list[str] of extensions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from .render_task import previewable_exts
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._list = QtWidgets.QListWidget()
        for ext in sorted(previewable_exts()):
            item = QtWidgets.QListWidgetItem(ext)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Checked)
            self._list.addItem(item)
        # size to the content: show every format without an inner scroll bar
        rows = max(self._list.count(), 1)
        row_h = self._list.sizeHintForRow(0) if self._list.count() else 20
        self._list.setMinimumHeight(rows * row_h + 2 * self._list.frameWidth() + 4)
        lay.addWidget(self._list)

    def get_value(self) -> list:
        checked = [self._list.item(i).text() for i in range(self._list.count())
                   if self._list.item(i).checkState() == QtCore.Qt.CheckState.Checked]
        # all checked → store the wildcard so formats registered later
        # (e.g. by a new plugin) are watched automatically
        if len(checked) == self._list.count():
            return ["*"]
        return checked

    def set_value(self, v) -> None:
        values = [str(e).lower() for e in (v or [])]
        all_on = "*" in values
        wanted = set(values)
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setCheckState(
                QtCore.Qt.CheckState.Checked
                if all_on or item.text() in wanted
                else QtCore.Qt.CheckState.Unchecked)


class TemplatePickerControl(QtWidgets.QComboBox):
    """Saved curve-stack templates; empty string = no template."""

    NONE_LABEL = "(none)"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from angstrompro.gui.widgets.curve_stack.template_manager import list_templates
        self.addItem(self.NONE_LABEL)
        try:
            self.addItems(list_templates())
        except Exception:
            pass
        self.setMinimumWidth(160)

    def get_value(self) -> str:
        text = self.currentText()
        return "" if text == self.NONE_LABEL else text

    def set_value(self, v) -> None:
        name = str(v or "")
        idx = self.findText(name) if name else 0
        if idx < 0:   # saved template was deleted — show it anyway, render skips it
            self.addItem(name)
            idx = self.count() - 1
        self.setCurrentIndex(idx)


class CacheToolsControl(QtWidgets.QWidget):
    """Cache size display + orphan sweep + wipe-and-re-render."""

    def __init__(self, cache_dir: str = "", parent=None) -> None:
        super().__init__(parent)
        self._cache_dir = cache_dir
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._info = QtWidgets.QLabel("—")
        lay.addWidget(self._info)
        row = QtWidgets.QHBoxLayout()
        b_refresh = QtWidgets.QPushButton("Refresh stats")
        b_refresh.clicked.connect(self._refresh)
        b_sweep = QtWidgets.QPushButton("Clean orphaned PNGs")
        b_sweep.clicked.connect(self._sweep)
        b_clear = QtWidgets.QPushButton("Re-render all…")
        b_clear.setToolTip("Delete every cached thumbnail; they regenerate "
                           "on view / by the background scanner")
        b_clear.clicked.connect(self._clear)
        row.addWidget(b_refresh)
        row.addWidget(b_sweep)
        row.addWidget(b_clear)
        row.addStretch()
        lay.addLayout(row)
        self._refresh()

    # PreferencesPanel contract — this control edits nothing in the config
    def get_value(self) -> str:
        return self._cache_dir

    def set_value(self, v) -> None:
        if v:
            self._cache_dir = str(v)
            self._refresh()

    def _open_cache(self):
        from .thumbnail_cache import ThumbnailCache
        from angstrompro.app.user_data_folder import user_data_subpath
        cache_dir = self._cache_dir or str(user_data_subpath("cache", "data_browser"))
        return ThumbnailCache(cache_dir)

    def _refresh(self) -> None:
        try:
            cache = self._open_cache()
            s = cache.stats()
            cache.close()
            mb = s["disk_bytes"] / 1e6
            self._info.setText(
                f"{s['files']} files · {s['thumbnails']} thumbnails · "
                f"{s['errors']} errors · {mb:.1f} MB on disk")
        except Exception as exc:
            self._info.setText(f"cache unavailable: {exc}")

    def _sweep(self) -> None:
        try:
            cache = self._open_cache()
            n = cache.cleanup_orphan_pngs()
            cache.close()
            QtWidgets.QMessageBox.information(
                self, "Cache", f"Removed {n} orphaned PNG(s).")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Cache", str(exc))
        self._refresh()

    def _clear(self) -> None:
        if QtWidgets.QMessageBox.question(
                self, "Re-render all thumbnails",
                "Delete every cached thumbnail?\nThey will regenerate on view "
                "and by the background scanner.") != \
                QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            cache = self._open_cache()
            cache.clear_all()
            cache.close()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Cache", str(exc))
        self._refresh()


register_widget_type("db_folder_list", FolderListControl)
register_widget_type("db_format_list", FormatListControl)
register_widget_type("db_template_picker", TemplatePickerControl)
register_widget_type("db_cache_tools", CacheToolsControl)
