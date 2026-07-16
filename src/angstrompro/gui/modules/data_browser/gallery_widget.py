# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

Virtual thumbnail gallery for the Data Browser.

Model/view design (no per-card widgets):

GalleryModel (QAbstractListModel)
    Holds one light CardRow per (file, channel).  Decoded QPixmaps live in
    a bounded LRU cache (~200 entries); evicted thumbnails reload from the
    PNG cache on disk in under a millisecond.

CardDelegate (QStyledItemDelegate)
    One shared painter draws every visible cell: thumbnail (or the
    loading / error / channel-not-found placeholder), filename, info line,
    optional relative-path line.  sizeHint derives from the configured
    thumbnail size.

GalleryView (QListView, IconMode)
    Wrap-to-row grid, rubber-band selection.  A single debounce QTimer
    fires viewport_settled(keys) ~200 ms after scrolling stops; the
    coordinator (DataBrowserModule) submits HIGH renders for uncached
    visible cards and cancels stale ones.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field

from angstrompro.utils.qt_compat import QtCore, QtGui, QtWidgets, Signal

log = logging.getLogger(__name__)

# row states
STATE_READY     = "ready"       # png_path valid, paint pixmap
STATE_LOADING   = "loading"     # render pending / in flight
STATE_ERROR     = "error"       # file unreadable / render failed
STATE_NOT_FOUND = "not_found"   # selected channel absent in this file
STATE_ICON      = "icon"        # readable but no renderer — icon-only card

KeyRole   = QtCore.Qt.ItemDataRole.UserRole
StateRole = QtCore.Qt.ItemDataRole.UserRole + 1


@dataclass
class CardRow:
    key:       tuple            # (file_path, channel_id)
    filename:  str
    channel:   str  = ""
    info:      str  = ""        # e.g. "2D · 128 curves" / "3D · layer 0/256"
    rel_path:  str  = ""        # shown when include-subfolders is on
    png_path:  str  = ""
    state:     str  = STATE_LOADING
    tooltip:   str  = ""
    extra:     dict = field(default_factory=dict)


class GalleryModel(QtCore.QAbstractListModel):
    """Light rows + bounded LRU pixmap cache."""

    def __init__(self, pixmap_cache_size: int = 200, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[CardRow] = []
        self._index_of: dict[tuple, int] = {}
        self._pixmaps: OrderedDict[tuple, QtGui.QPixmap] = OrderedDict()
        self._cache_size = max(16, int(pixmap_cache_size))

    # ------------------------------------------------------------------
    # Qt model API
    # ------------------------------------------------------------------

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return row.filename
        if role == QtCore.Qt.ItemDataRole.DecorationRole:
            return self._pixmap_for(row)
        if role == QtCore.Qt.ItemDataRole.ToolTipRole:
            return row.tooltip or row.key[0]
        if role == KeyRole:
            return row.key
        if role == StateRole:
            return row.state
        return None

    def flags(self, index):
        return (QtCore.Qt.ItemFlag.ItemIsEnabled |
                QtCore.Qt.ItemFlag.ItemIsSelectable)

    # ------------------------------------------------------------------
    # Row management (main thread only)
    # ------------------------------------------------------------------

    def set_rows(self, rows: list[CardRow]) -> None:
        """Replace all rows (folder selection changed)."""
        self.beginResetModel()
        self._rows = list(rows)
        self._reindex()
        self._pixmaps.clear()
        self.endResetModel()

    def row_for_key(self, key: tuple) -> CardRow | None:
        i = self._index_of.get(key)
        return self._rows[i] if i is not None else None

    def keys(self) -> list[tuple]:
        return [r.key for r in self._rows]

    def update_row(self, key: tuple, *, png_path: str | None = None,
                   state: str | None = None, info: str | None = None,
                   tooltip: str | None = None) -> None:
        """Update one card in place (render completed / failed) and repaint it."""
        i = self._index_of.get(key)
        if i is None:
            return
        row = self._rows[i]
        if png_path is not None:
            row.png_path = png_path
            self._pixmaps.pop(key, None)   # force reload from the new PNG
        if state is not None:
            row.state = state
        if info is not None:
            row.info = info
        if tooltip is not None:
            row.tooltip = tooltip
        idx = self.index(i)
        self.dataChanged.emit(idx, idx)

    def replace_file_rows(self, file_path: str, rows: list[CardRow]) -> None:
        """First contact: swap a provisional file card for its channel cards."""
        keep = [r for r in self._rows if r.key[0] != file_path]
        insert_at = next((i for i, r in enumerate(self._rows)
                          if r.key[0] == file_path), len(keep))
        self.beginResetModel()
        self._rows = keep[:insert_at] + list(rows) + keep[insert_at:]
        self._reindex()
        self.endResetModel()

    def _reindex(self) -> None:
        self._index_of = {r.key: i for i, r in enumerate(self._rows)}

    # ------------------------------------------------------------------
    # LRU pixmap cache
    # ------------------------------------------------------------------

    def _pixmap_for(self, row: CardRow) -> QtGui.QPixmap | None:
        if row.state != STATE_READY or not row.png_path:
            return None
        pm = self._pixmaps.get(row.key)
        if pm is not None:
            self._pixmaps.move_to_end(row.key)
            return pm
        pm = QtGui.QPixmap(row.png_path)
        if pm.isNull():
            return None
        self._pixmaps[row.key] = pm
        if len(self._pixmaps) > self._cache_size:
            self._pixmaps.popitem(last=False)
        return pm

    def set_pixmap_cache_size(self, n: int) -> None:
        self._cache_size = max(16, int(n))
        while len(self._pixmaps) > self._cache_size:
            self._pixmaps.popitem(last=False)


class CardDelegate(QtWidgets.QStyledItemDelegate):
    """Paints one card: thumbnail / placeholder + filename + info lines."""

    PAD = 8

    def __init__(self, thumb_size: int = 150, show_rel_path: bool = False,
                 parent=None) -> None:
        super().__init__(parent)
        self._thumb = int(thumb_size)
        self.show_rel_path = show_rel_path
        # real font height (DPI-aware); a fixed pixel count clips glyphs
        self._line_h = QtGui.QFontMetrics(
            QtWidgets.QApplication.font()).height() + 2

    def set_thumb_size(self, px: int) -> None:
        self._thumb = int(px)

    def sizeHint(self, option, index) -> QtCore.QSize:
        lines = 3 if self.show_rel_path else 2
        # + 8: 4 px thumb→text gap and 2×2 px border inset (see paint)
        return QtCore.QSize(self._thumb + 2 * self.PAD + 4,
                            self._thumb + 2 * self.PAD + 8 + lines * self._line_h)

    def paint(self, painter: QtGui.QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = option.rect.adjusted(2, 2, -2, -2)
        pal = option.palette

        selected = bool(option.state & QtWidgets.QStyle.StateFlag.State_Selected)
        border = pal.highlight().color() if selected else pal.mid().color()
        painter.setPen(QtGui.QPen(border, 2 if selected else 1))
        painter.setBrush(pal.base())
        painter.drawRoundedRect(rect, 6, 6)

        thumb_rect = QtCore.QRect(rect.left() + self.PAD, rect.top() + self.PAD,
                                  rect.width() - 2 * self.PAD, self._thumb)
        state = index.data(StateRole) or STATE_LOADING
        pm = index.data(QtCore.Qt.ItemDataRole.DecorationRole)

        if state == STATE_READY and pm is not None:
            scaled = pm.scaled(thumb_rect.size(),
                               QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                               QtCore.Qt.TransformationMode.SmoothTransformation)
            x = thumb_rect.left() + (thumb_rect.width() - scaled.width()) // 2
            y = thumb_rect.top() + (thumb_rect.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(pal.alternateBase())
            painter.drawRoundedRect(thumb_rect, 4, 4)
            text, color = {
                STATE_LOADING:   ("Loading…",          pal.mid().color()),
                STATE_ERROR:     ("Error",             QtGui.QColor(178, 60, 60)),
                STATE_NOT_FOUND: ("channel not found", pal.mid().color()),
                STATE_ICON:      ("no preview",        pal.mid().color()),
            }.get(state, ("", pal.mid().color()))
            painter.setPen(color)
            painter.drawText(thumb_rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)

        # text lines
        row_y = thumb_rect.bottom() + 4
        text_rect = QtCore.QRect(rect.left() + self.PAD, row_y,
                                 rect.width() - 2 * self.PAD, self._line_h)
        fm = painter.fontMetrics()

        painter.setPen(pal.text().color())
        name = fm.elidedText(index.data(QtCore.Qt.ItemDataRole.DisplayRole) or "",
                             QtCore.Qt.TextElideMode.ElideMiddle, text_rect.width())
        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignLeft, name)

        model = index.model()
        row = model.row_for_key(index.data(KeyRole)) if hasattr(model, "row_for_key") else None
        painter.setPen(pal.mid().color())
        if row is not None:
            info_rect = text_rect.translated(0, self._line_h)
            info = " · ".join(p for p in (row.channel, row.info) if p)
            painter.drawText(info_rect, QtCore.Qt.AlignmentFlag.AlignLeft,
                             fm.elidedText(info, QtCore.Qt.TextElideMode.ElideRight,
                                           info_rect.width()))
            if self.show_rel_path and row.rel_path:
                rel_rect = info_rect.translated(0, self._line_h)
                painter.drawText(rel_rect, QtCore.Qt.AlignmentFlag.AlignLeft,
                                 fm.elidedText(row.rel_path,
                                               QtCore.Qt.TextElideMode.ElideLeft,
                                               rel_rect.width()))
        painter.restore()


class GalleryView(QtWidgets.QListView):
    """IconMode grid with scroll-settle detection."""

    viewport_settled = Signal(list)          # list of visible keys
    send_requested = Signal(tuple)           # key — double-click / context "Send"
    context_menu_requested = Signal(tuple, QtCore.QPoint)   # key, global pos

    SETTLE_MS = 200

    def __init__(self, thumb_size: int = 150, parent=None) -> None:
        super().__init__(parent)
        self._model = GalleryModel(parent=self)
        self._delegate = CardDelegate(thumb_size, parent=self)
        self.setModel(self._model)
        self.setItemDelegate(self._delegate)

        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.setUniformItemSizes(True)
        self.setSpacing(6)
        self.setMovement(QtWidgets.QListView.Movement.Static)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)

        self._settle = QtCore.QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(self.SETTLE_MS)
        self._settle.timeout.connect(self._emit_settled)
        self.verticalScrollBar().valueChanged.connect(
            lambda _v: self._settle.start())

        self.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.doubleClicked.connect(self._on_double_click)

    # ------------------------------------------------------------------

    def gallery_model(self) -> GalleryModel:
        return self._model

    def set_thumb_size(self, px: int) -> None:
        self._delegate.set_thumb_size(px)
        self._model.layoutChanged.emit()

    def set_show_rel_path(self, show: bool) -> None:
        self._delegate.show_rel_path = bool(show)
        self._model.layoutChanged.emit()

    def visible_keys(self) -> list[tuple]:
        """Keys of the cards currently intersecting the viewport."""
        keys: list[tuple] = []
        if self._model.rowCount() == 0:
            return keys
        vp = self.viewport().rect()
        for i in range(self._model.rowCount()):
            r = self.visualRect(self._model.index(i))
            if r.isValid() and r.intersects(vp):
                keys.append(self._model.index(i).data(KeyRole))
        return keys

    def settle_now(self) -> None:
        """Force an immediate viewport_settled emit (initial folder load)."""
        self._settle.stop()
        self._emit_settled()

    # ------------------------------------------------------------------

    def _emit_settled(self) -> None:
        self.viewport_settled.emit(self.visible_keys())

    def _on_double_click(self, index) -> None:
        key = index.data(KeyRole)
        if key is not None:
            self.send_requested.emit(key)

    def _on_context_menu(self, pos: QtCore.QPoint) -> None:
        index = self.indexAt(pos)
        if index.isValid():
            key = index.data(KeyRole)
            self.context_menu_requested.emit(
                key, self.viewport().mapToGlobal(pos))
