# -*- coding: utf-8 -*-
"""
Created on 2026-07-05

@author: jiahaoYan

LogPanel — dock widget that captures Python log records and displays them
in a scrolling list. Minimum level is configured via app.log_level preference.
"""
from __future__ import annotations

import logging
import time
from collections import deque

from angstrompro.utils.qt_compat import QtCore, QtGui, QtWidgets, Signal

_MAX_RECORDS = 500

_LEVEL_MAP = {
    "DEBUG":   logging.DEBUG,
    "INFO":    logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR":   logging.ERROR,
}

# ── shared in-process log handler ─────────────────────────────────────────────

class _LogEmitter(QtCore.QObject):
    record_emitted = Signal(logging.LogRecord)


class _QtLogHandler(logging.Handler):
    """Pure-Python logging.Handler holding a QObject emitter.

    Deliberately NOT a QObject itself: logging.shutdown() runs at interpreter
    exit, after Qt has torn down its C++ objects — a QObject-based handler
    still registered with the root logger raises
    'wrapped C/C++ object has been deleted' there.  Only the emitter is a
    QObject, and signal emission is guarded for the post-teardown window."""

    def __init__(self) -> None:
        logging.Handler.__init__(self)
        self._emitter = _LogEmitter()
        self.record_emitted = self._emitter.record_emitted
        self._buffer: deque[logging.LogRecord] = deque(maxlen=_MAX_RECORDS)

    def emit(self, record: logging.LogRecord) -> None:
        self._buffer.append(record)
        try:
            self._emitter.record_emitted.emit(record)
        except RuntimeError:
            pass   # emitter already destroyed during app teardown

    @property
    def buffer(self) -> deque[logging.LogRecord]:
        return self._buffer


_handler: _QtLogHandler | None = None


def _get_handler() -> _QtLogHandler:
    global _handler
    if _handler is None:
        _handler = _QtLogHandler()
        _handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(_handler)
    return _handler


# ── colours per level ─────────────────────────────────────────────────────────

_LEVEL_COLOR = {
    logging.DEBUG:    "#888888",
    logging.INFO:     "#cccccc",
    logging.WARNING:  "#f0a040",
    logging.ERROR:    "#e05050",
    logging.CRITICAL: "#ff3030",
}

_LEVEL_LABEL = {
    logging.DEBUG:    "DBG",
    logging.INFO:     "INF",
    logging.WARNING:  "WRN",
    logging.ERROR:    "ERR",
    logging.CRITICAL: "CRT",
}


# ── widget ────────────────────────────────────────────────────────────────────

class LogPanel(QtWidgets.QWidget):

    def __init__(self, min_level: int = logging.WARNING, parent=None) -> None:
        super().__init__(parent)
        self._min_level = min_level
        self._handler   = _get_handler()
        self._setup_ui()
        self._load_buffer()
        self._handler.record_emitted.connect(self._on_record)

    def set_min_level(self, level: int) -> None:
        if level == self._min_level:
            return
        self._min_level = level
        self._list.clear()
        self._load_buffer()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        bar = QtWidgets.QHBoxLayout()
        btn_copy = QtWidgets.QPushButton("Copy")
        btn_copy.setToolTip("Copy selected line to clipboard")
        btn_copy.clicked.connect(self._on_copy)
        btn_clear = QtWidgets.QPushButton("Clear")
        btn_clear.clicked.connect(self._on_clear)
        bar.addStretch()
        bar.addWidget(btn_copy)
        bar.addWidget(btn_clear)
        layout.addLayout(bar)

        self._list = QtWidgets.QListWidget()
        self._list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setWordWrap(True)
        self._list.setFont(QtGui.QFont("Consolas, Courier New", 9))
        self._list.setSpacing(1)
        layout.addWidget(self._list)

    def _load_buffer(self) -> None:
        for record in self._handler.buffer:
            self._append(record)

    def _on_record(self, record: logging.LogRecord) -> None:
        self._append(record)

    def _append(self, record: logging.LogRecord) -> None:
        if record.levelno < self._min_level:
            return
        label = _LEVEL_LABEL.get(record.levelno, "???")
        color = _LEVEL_COLOR.get(record.levelno, "#cccccc")
        name  = record.name.split(".")[-1]
        ts    = time.strftime("%H:%M:%S", time.localtime(record.created))
        text  = f"[{label} {ts}] {name}: {record.getMessage()}"
        item  = QtWidgets.QListWidgetItem(text)
        item.setForeground(QtGui.QColor(color))
        self._list.addItem(item)
        if self._list.count() > _MAX_RECORDS:
            self._list.takeItem(0)
        self._list.scrollToBottom()

    def _on_copy(self) -> None:
        item = self._list.currentItem()
        if item:
            QtWidgets.QApplication.clipboard().setText(item.text())

    def _on_clear(self) -> None:
        self._list.clear()
