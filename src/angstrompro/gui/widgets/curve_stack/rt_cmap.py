# -*- coding: utf-8 -*-
"""
Created on 2026-07-14

@author: jiahaoYan

RT (anchor-based) colormap support for CurveStackViewer plot widgets.

RtCmapControl bundles the toolbar UI (label + checkbox + "Edit…" button)
and the lazily-created ColorMapEditorWidget dialog.  Each plot widget owns
its own instance, so stack and colormap modes keep independent anchor sets,
harvested/restored per mode in the scene's widget_extras.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets, Signal


def cmap_from_anchors(anchors: list[dict]):
    """Build a LinearSegmentedColormap from RT anchor dicts.

    Anchor format (same as ColorMapEditorWidget.get_anchors()):
    {"position": 0..1, "red": 0..1, "green": 0..1, "blue": 0..1}
    """
    from matplotlib.colors import LinearSegmentedColormap
    pts = sorted(anchors, key=lambda a: a["position"])
    cdict = {"red": [], "green": [], "blue": []}
    for a in pts:
        x = max(0.0, min(1.0, float(a["position"])))
        for ch in ("red", "green", "blue"):
            v = max(0.0, min(1.0, float(a[ch])))
            cdict[ch].append([x, v, v])
    return LinearSegmentedColormap("rt_cmap", segmentdata=cdict, N=256)


class RtCmapControl(QtCore.QObject):
    """Toolbar control + editor dialog for one widget's RT colormap.

    Usage::

        self._rt = RtCmapControl(self)
        self._rt.add_to(ctrl_layout)
        self._rt.changed.connect(self._rebuild_plot)
        ...
        cmap = self._rt.resolve(fallback_name)
    """

    changed = Signal()   # emitted when the effective colormap changed

    def __init__(self, parent_widget: QtWidgets.QWidget) -> None:
        super().__init__(parent_widget)
        self._parent = parent_widget
        self._dlg    = None   # lazy QDialog wrapping ColorMapEditorWidget
        self._editor = None   # the ColorMapEditorWidget inside it
        # anchors restored from a scene before the editor exists
        self._pending: list[dict] | None = None

        self.check = QtWidgets.QCheckBox()
        self.check.setToolTip(
            "Use the anchor-based real-time colormap instead of the palette")
        self.check.toggled.connect(self._on_toggled)

        self.edit_btn = QtWidgets.QPushButton("Edit…")
        self.edit_btn.setToolTip("Open the RT colormap anchor editor")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.open_editor)

    def add_to(self, layout: QtWidgets.QHBoxLayout) -> None:
        """Append 'RT-ColorMap: [x] [Edit…]' to a toolbar layout."""
        layout.addWidget(QtWidgets.QLabel("RT-ColorMap:"))
        layout.addWidget(self.check)
        layout.addWidget(self.edit_btn)

    # ── State ─────────────────────────────────────────────────────────────

    def use_rt_cmap(self) -> bool:
        return self.check.isChecked()

    def rt_anchors(self) -> list[dict]:
        """Current anchor list [{position, red, green, blue}, …] (JSON-safe)."""
        if self._editor is not None:
            return self._editor.get_anchors()
        return list(self._pending or [])

    def set_rt(self, use: bool, anchors: list[dict] | None) -> None:
        """Restore RT state (from scene or template) — no rebuild emitted."""
        if anchors:
            if self._editor is not None:
                self._editor.set_anchors(anchors)
            else:
                self._pending = [dict(a) for a in anchors]
        self.check.blockSignals(True)
        self.check.setChecked(bool(use))
        self.check.blockSignals(False)
        self.edit_btn.setEnabled(bool(use))

    def resolve(self, fallback):
        """Effective colormap: anchor-built map when RT is on, else *fallback*."""
        if self.check.isChecked():
            anchors = self.rt_anchors()
            if anchors:
                return cmap_from_anchors(anchors)
        return fallback

    # ── Editor dialog ─────────────────────────────────────────────────────

    def open_editor(self) -> None:
        if self._dlg is None:
            from angstrompro.gui.widgets.ColorMapEditorWidget import ColorMapEditorWidget
            self._dlg = QtWidgets.QDialog(
                self._parent, QtCore.Qt.WindowType.Tool |
                QtCore.Qt.WindowType.WindowStaysOnTopHint)
            self._dlg.setWindowTitle("RT Colormap Editor")
            lay = QtWidgets.QVBoxLayout(self._dlg)
            self._editor = ColorMapEditorWidget()
            lay.addWidget(self._editor)
            # "Update" button in the editor → repaint with the new anchors
            self._editor.updateCdict.connect(lambda _d: self.changed.emit())
            if self._pending:
                self._editor.set_anchors(self._pending)
                self._pending = None
        self._dlg.show()
        self._dlg.raise_()
        self._dlg.activateWindow()

    def _on_toggled(self, checked: bool) -> None:
        self.edit_btn.setEnabled(checked)
        if checked and self._editor is None and not self._pending:
            self.open_editor()   # first use: let the user define anchors
        self.changed.emit()
