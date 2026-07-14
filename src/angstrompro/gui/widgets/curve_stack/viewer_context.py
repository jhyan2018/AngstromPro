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
target_changed()     — plot widget (and its ax/canvas) was swapped/rebuilt,
                       OR the active Y-side changed (left ↔ right twin).
                       Subscribers must drop old references and re-pull.
plot_rebuilt()       — the active plot widget finished a rebuild (artists,
                       axes limits, etc. have changed).  Fired whenever the
                       active widget emits artists_rebuilt.  The axes panel
                       uses this to auto-refresh without a Reload button.
selection_changed()  — the selected artist changed (or was cleared).
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore


class ViewerContext(QtCore.QObject):
    """Identity of the active view objects. Notify-only — no value copies."""

    target_changed    = QtCore.pyqtSignal()
    plot_rebuilt      = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._plot_widget = None
        self._selected_key: tuple | None = None   # (ds_name, curve_idx)
        self._y_side: str = "left"                # "left" | "right"

    # ── Target (plot widget / ax / canvas) ────────────────────────────────

    @property
    def plot_widget(self):
        return self._plot_widget

    @property
    def ax(self):
        """Primary (left) axes — always the main axes of the plot widget."""
        return getattr(self._plot_widget, "_ax", None)

    @property
    def active_ax(self):
        """Currently active axes: right twin when y_side == 'right', else primary."""
        if self._y_side == "right":
            ax2 = getattr(self._plot_widget, "_ax2", None)
            if ax2 is not None:
                return ax2
        return getattr(self._plot_widget, "_ax", None)

    @property
    def y_side(self) -> str:
        """Which Y axis is currently active: 'left' or 'right'."""
        return self._y_side

    @property
    def canvas(self):
        return getattr(self._plot_widget, "_canvas", None)

    def set_plot_widget(self, widget) -> None:
        """Called by the viewer when the plot widget is swapped or rebuilt.

        The selected key survives — it identifies a curve in the tree, which
        is mode-independent.  Subscribers re-pull `selected_artist`, which
        resolves against the new widget (or None if it has no line artists).
        """
        if self._plot_widget is not None:
            sig = getattr(self._plot_widget, "artists_rebuilt", None)
            if sig is not None:
                try:
                    sig.disconnect(self._on_artists_rebuilt)
                except RuntimeError:
                    pass
        self._plot_widget = widget
        sig = getattr(widget, "artists_rebuilt", None)
        if sig is not None:
            sig.connect(self._on_artists_rebuilt)
        self.target_changed.emit()
        self.selection_changed.emit()   # artist refs are stale — re-pull

    def _on_artists_rebuilt(self) -> None:
        self.plot_rebuilt.emit()
        self.selection_changed.emit()

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

    def set_y_side(self, side: str) -> None:
        """Switch between 'left' and 'right' twin axis.

        Emits target_changed so the axes panel reloads from the new active_ax.
        """
        if side == self._y_side:
            return
        self._y_side = side
        self.target_changed.emit()

    def set_selected_key(self, key: tuple | None) -> None:
        if key == self._selected_key:
            return
        self._selected_key = key
        self.selection_changed.emit()

    def refresh_selection(self) -> None:
        """Re-emit selection_changed (e.g. after a rebuild replaced artists)."""
        self.selection_changed.emit()
