# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

ArtistStylePanel — embedded panel in the left sidebar of CurveStackViewerWidget.

Shows style controls for the currently selected curve in the dataset tree.
Writes changes directly to the live Line2D artist via set_*() + draw_idle().
Hidden when no single curve is selected.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QtGui

_LINESTYLES = [
    ("Solid",    "solid"),
    ("Dashed",   "dashed"),
    ("Dotted",   "dotted"),
    ("Dash-dot", "dashdot"),
    ("None",     "none"),
]

_MARKERS = [
    ("None",     ""),
    ("Circle",   "o"),
    ("Square",   "s"),
    ("Triangle", "^"),
    ("Diamond",  "D"),
    ("Plus",     "+"),
    ("Cross",    "x"),
    ("Star",     "*"),
    ("Pentagon", "p"),
]


class ArtistStylePanel(QtWidgets.QGroupBox):
    """
    Inline style editor for a single Line2D artist.

    Call ``load(line, canvas)`` to populate with the artist's current style.
    Call ``clear()`` to reset to placeholder state (no artist loaded).

    Signals
    -------
    color_pinned(str)  — user picked a manual color; value is hex string
    color_reset()      — user clicked "Auto", removing the manual pin
    """

    color_pinned = QtCore.pyqtSignal(str)   # hex color string
    color_reset  = QtCore.pyqtSignal()

    def __init__(self, parent=None) -> None:
        # no group-box title: the dock's title bar already says "Curve Style"
        super().__init__("", parent)
        self._line    = None
        self._canvas  = None
        self._context = None
        self._loading = False
        self._build()
        self.clear()
        self.setMinimumWidth(220)   # keep controls readable when docked

    # ── ViewerContext binding (pull model) ────────────────────────────────

    def bind_context(self, context) -> None:
        """Subscribe to a ViewerContext; panel pulls values on selection."""
        self._context = context
        context.selection_changed.connect(self._on_context_selection)
        context.target_changed.connect(self._on_context_target)
        self._on_context_selection()

    def _on_context_target(self) -> None:
        # plot widget swapped — old artist/canvas references are dead
        self._line   = None
        self._canvas = None

    def _on_context_selection(self) -> None:
        ctx = self._context
        if ctx is None:
            return
        artist = ctx.selected_artist
        if artist is None:
            if ctx.selected_key is not None and ctx.plot_widget is not None \
                    and not hasattr(ctx.plot_widget, "_lines"):
                self.clear("Not available in Colormap mode")
            else:
                self.clear()
            return
        self.load(artist, ctx.canvas)

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._placeholder = QtWidgets.QLabel("Select a single curve to edit style")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self._placeholder)

        self._form_w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(self._form_w)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setSpacing(4)

        # Color
        self._color_btn = QtWidgets.QPushButton()
        self._color_btn.setFixedHeight(24)
        self._color_btn.setMinimumWidth(
            self._color_btn.fontMetrics().horizontalAdvance("#88888888") + 16)
        self._color_btn.setToolTip("Click to pick line color")
        self._color_btn.clicked.connect(self._on_pick_color)
        color_row = QtWidgets.QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        color_row.addWidget(self._color_btn)
        self._reset_color_btn = QtWidgets.QPushButton("Auto")
        self._reset_color_btn.setToolTip("Remove manual color (use auto/cmap)")
        self._reset_color_btn.clicked.connect(self._on_reset_color)
        color_row.addWidget(self._reset_color_btn)
        color_row.addStretch()
        form.addRow("Color:", color_row)

        # Linewidth
        self._lw_spin = QtWidgets.QDoubleSpinBox()
        self._lw_spin.setRange(0.1, 20.0)
        self._lw_spin.setSingleStep(0.5)
        self._lw_spin.setDecimals(1)
        self._lw_spin.setFixedWidth(70)
        self._lw_spin.valueChanged.connect(self._on_lw_changed)
        form.addRow("Width:", self._lw_spin)

        # Linestyle
        self._ls_combo = QtWidgets.QComboBox()
        for label, value in _LINESTYLES:
            self._ls_combo.addItem(label, value)
        self._ls_combo.currentIndexChanged.connect(self._on_ls_changed)
        form.addRow("Style:", self._ls_combo)

        # Marker
        self._marker_combo = QtWidgets.QComboBox()
        for label, value in _MARKERS:
            self._marker_combo.addItem(label, value)
        self._marker_combo.currentIndexChanged.connect(self._on_marker_changed)
        form.addRow("Marker:", self._marker_combo)

        # Markersize
        self._ms_spin = QtWidgets.QDoubleSpinBox()
        self._ms_spin.setRange(0.5, 30.0)
        self._ms_spin.setSingleStep(1.0)
        self._ms_spin.setDecimals(1)
        self._ms_spin.setFixedWidth(70)
        self._ms_spin.valueChanged.connect(self._on_ms_changed)
        form.addRow("Marker size:", self._ms_spin)

        # Alpha
        self._alpha_spin = QtWidgets.QDoubleSpinBox()
        self._alpha_spin.setRange(0.0, 1.0)
        self._alpha_spin.setSingleStep(0.05)
        self._alpha_spin.setDecimals(2)
        self._alpha_spin.setFixedWidth(70)
        self._alpha_spin.valueChanged.connect(self._on_alpha_changed)
        form.addRow("Alpha:", self._alpha_spin)

        layout.addWidget(self._form_w)

    # ── Public API ────────────────────────────────────────────────────────

    def load(self, line, canvas) -> None:
        """Populate controls from a Line2D or LineCollection artist.

        For LineCollection (cmap_value modes) only width / style / alpha are
        editable — color comes from the colormap and markers don't exist.
        """
        from matplotlib.lines import Line2D
        is_line2d = isinstance(line, Line2D)

        self._line   = line
        self._canvas = canvas
        self._loading = True
        try:
            # color — Line2D only
            self._color_btn.setEnabled(is_line2d)
            self._reset_color_btn.setEnabled(is_line2d)
            if is_line2d:
                self._set_color_btn(line.get_color())
            else:
                self._color_btn.setStyleSheet("")
                self._color_btn.setText("cmap")

            # linewidth — both (LC returns a sequence)
            lw = line.get_linewidth()
            if not isinstance(lw, (int, float)):
                lw = lw[0] if len(lw) else 1.0
            self._lw_spin.setValue(float(lw))

            # linestyle — Line2D only: per-point LC segments are shorter than
            # a dash stroke, so dash patterns are invisible on LineCollection
            self._ls_combo.setEnabled(is_line2d)
            ls = line.get_linestyle()
            if isinstance(ls, list):   # LC returns list of dash tuples
                ls = ls[0] if ls else "solid"
            if not isinstance(ls, str):
                ls = "solid"
            ls_map = {"-": "solid", "--": "dashed", ":": "dotted",
                      "-.": "dashdot", "none": "none", "None": "none", "": "none"}
            ls = ls_map.get(ls, ls)
            idx = self._ls_combo.findData(ls)
            self._ls_combo.setCurrentIndex(idx if idx >= 0 else 0)

            # marker — Line2D only
            self._marker_combo.setEnabled(is_line2d)
            self._ms_spin.setEnabled(is_line2d)
            if is_line2d:
                marker = line.get_marker()
                if marker in ("None", "none", None):
                    marker = ""
                idx = self._marker_combo.findData(marker)
                self._marker_combo.setCurrentIndex(idx if idx >= 0 else 0)
                self._ms_spin.setValue(line.get_markersize())

            # alpha — both
            alpha = line.get_alpha()
            self._alpha_spin.setValue(alpha if isinstance(alpha, (int, float)) else 1.0)
        finally:
            self._loading = False

        self._placeholder.hide()
        self._form_w.show()
        self.setMaximumHeight(16777215)   # unlimited — form needs full height
        self.updateGeometry()

    def clear(self, reason: str = "") -> None:
        """Reset to placeholder state — compact height."""
        self._line   = None
        self._canvas = None
        self._form_w.hide()
        self._placeholder.setText(
            reason or "Select a single curve to edit style")
        self._placeholder.show()
        self.setMaximumHeight(60)   # just title + placeholder line
        self.updateGeometry()

    # ── Handlers ──────────────────────────────────────────────────────────

    def _on_pick_color(self) -> None:
        if self._line is None:
            return
        import matplotlib.colors as mcolors
        current = self._line.get_color()
        try:
            r, g, b, a = mcolors.to_rgba(current)
            initial = QtGui.QColor.fromRgbF(r, g, b, a)
        except Exception:
            initial = QtGui.QColor("white")

        color = QtWidgets.QColorDialog.getColor(
            initial, self, "Pick Line Color",
            QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if not color.isValid():
            return
        hex_color = color.name()
        self._line.set_color(hex_color)
        self._set_color_btn(hex_color)
        self._redraw()
        self.color_pinned.emit(hex_color)

    def _on_reset_color(self) -> None:
        """Remove manual color pin — caller will reapply color mode via color_reset signal."""
        if self._line is None:
            return
        self.color_reset.emit()

    def _on_lw_changed(self, val: float) -> None:
        if self._loading or self._line is None:
            return
        self._line.set_linewidth(val)
        self._redraw()

    def _on_ls_changed(self, _idx: int) -> None:
        if self._loading or self._line is None:
            return
        ls = self._ls_combo.currentData() or "none"
        from matplotlib.lines import Line2D
        if ls == "none" and not isinstance(self._line, Line2D):
            # LineCollection has no "none" linestyle — hide instead
            self._line.set_visible(False)
        else:
            if not isinstance(self._line, Line2D) and not self._line.get_visible():
                self._line.set_visible(True)   # undo a previous "None" choice
            self._line.set_linestyle(ls)
        self._redraw()

    def _on_marker_changed(self, _idx: int) -> None:
        if self._loading or self._line is None:
            return
        m = self._marker_combo.currentData()
        self._line.set_marker(m if m else "None")
        self._redraw()

    def _on_ms_changed(self, val: float) -> None:
        if self._loading or self._line is None:
            return
        self._line.set_markersize(val)
        self._redraw()

    def _on_alpha_changed(self, val: float) -> None:
        if self._loading or self._line is None:
            return
        self._line.set_alpha(val)
        self._redraw()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _set_color_btn(self, color_str: str) -> None:
        import matplotlib.colors as mcolors
        try:
            r, g, b, _ = mcolors.to_rgba(color_str)
            qc = QtGui.QColor.fromRgbF(r, g, b)
            # pick contrasting label color
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            fg = "#000000" if luma > 0.5 else "#ffffff"
            self._color_btn.setStyleSheet(
                f"background-color: {qc.name()}; color: {fg}; "
                f"border: 1px solid #888;")
            self._color_btn.setText(qc.name())
        except Exception:
            self._color_btn.setStyleSheet("")
            self._color_btn.setText("?")

    def _redraw(self) -> None:
        if self._canvas is not None:
            self._canvas.draw_idle()
