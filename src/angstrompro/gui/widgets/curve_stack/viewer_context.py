# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

ViewerContext — identity object for the CurveStackViewer.

Answers "what is currently active?": the plot widget, its axes/canvas, and
the selected artist.  Panels (docks) subscribe to its signals and PULL the
values they need from the referenced objects; the context never copies or
carries property values itself.

Signals
-------
target_changed()     — plot widget (and its ax/canvas) was swapped/rebuilt.
                       Subscribers must drop old references and re-pull.
selection_changed()  — the selected artist changed (or was cleared).
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore


class ViewerContext(QtCore.QObject):
    """Identity of the active view objects. Notify-only — no value copies."""

    target_changed    = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._plot_widget = None
        self._selected_key: tuple | None = None   # (ds_name, curve_idx)

    # ── Target (plot widget / ax / canvas) ────────────────────────────────

    @property
    def plot_widget(self):
        return self._plot_widget

    @property
    def ax(self):
        return getattr(self._plot_widget, "_ax", None)

    @property
    def canvas(self):
        return getattr(self._plot_widget, "_canvas", None)

    def set_plot_widget(self, widget) -> None:
        """Called by the viewer when the plot widget is swapped or rebuilt."""
        self._plot_widget = widget
        self._selected_key = None
        self.target_changed.emit()
        self.selection_changed.emit()   # old selection is gone with the widget

    # ── Selection ─────────────────────────────────────────────────────────

    @property
    def selected_key(self) -> tuple | None:
        return self._selected_key

    @property
    def selected_artist(self):
        """Live artist for the selected key, or None."""
        if self._selected_key is None:
            return None
        lines = getattr(self._plot_widget, "_lines", None)
        if lines is None:
            return None
        return lines.get(self._selected_key)

    def set_selected_key(self, key: tuple | None) -> None:
        if key == self._selected_key:
            return
        self._selected_key = key
        self.selection_changed.emit()

    def refresh_selection(self) -> None:
        """Re-emit selection_changed (e.g. after a rebuild replaced artists)."""
        self.selection_changed.emit()
