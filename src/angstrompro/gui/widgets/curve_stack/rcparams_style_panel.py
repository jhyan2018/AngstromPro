# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

RcParamsStylePanel — dialog for editing common matplotlib rcParams.

Covers: line defaults, axes appearance, tick style, font, grid, legend.
Changes are applied immediately to mpl.rcParams (live preview).
"Reset" restores mpl defaults for tracked keys only.
The calling widget is responsible for calling refresh() on the plot widget
after the dialog closes (or on Apply).
"""
from __future__ import annotations

import matplotlib as mpl

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QtGui


class RcParamsStylePanel(QtWidgets.QDialog):
    """Edit common rcParams and apply them live."""

    # Emitted whenever rcParams change so the caller can refresh the plot
    applied = QtCore.pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent,
                         QtCore.Qt.WindowType.Tool |
                         QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Plot Style (rcParams)")
        self.setModal(False)
        self._loading = False
        self._build()
        self._load()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_lines_tab(),  "Lines")
        tabs.addTab(self._build_axes_tab(),   "Axes")
        tabs.addTab(self._build_ticks_tab(),  "Ticks")
        tabs.addTab(self._build_font_tab(),   "Font")
        tabs.addTab(self._build_legend_tab(), "Legend")
        tabs.addTab(self._build_cycle_tab(),  "Color cycle")
        layout.addWidget(tabs)

        btn_row = QtWidgets.QHBoxLayout()
        btn_reset = QtWidgets.QPushButton("Reset to Defaults")
        btn_reset.clicked.connect(self._reset)
        btn_apply = QtWidgets.QPushButton("Apply")
        btn_apply.setDefault(True)
        btn_apply.clicked.connect(self._apply)
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.setMinimumWidth(380)

    def _form(self) -> tuple[QtWidgets.QWidget, QtWidgets.QFormLayout]:
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        f.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        f.setSpacing(6)
        f.setContentsMargins(8, 8, 8, 8)
        return w, f

    def _spin(self, lo, hi, step=0.1, dec=1) -> QtWidgets.QDoubleSpinBox:
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi); s.setSingleStep(step); s.setDecimals(dec)
        s.setFixedWidth(80)
        return s

    def _color_btn(self) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton()
        btn.setFixedSize(56, 22)
        return btn

    # ── Tabs ──────────────────────────────────────────────────────────────

    def _build_lines_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._lw   = self._spin(0.1, 20.0, 0.5)
        self._ls   = QtWidgets.QComboBox()
        self._ls.addItems(["solid", "dashed", "dotted", "dashdot"])
        self._mk   = QtWidgets.QComboBox()
        self._mk.addItems(["None", "o", "s", "^", "D", "+", "x"])
        self._mks  = self._spin(0.5, 30.0, 1.0)
        f.addRow("Line width:",   self._lw)
        f.addRow("Line style:",   self._ls)
        f.addRow("Marker:",       self._mk)
        f.addRow("Marker size:",  self._mks)
        return w

    def _build_axes_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._axes_fc  = self._color_btn()
        self._axes_fc.clicked.connect(lambda: self._pick("axes.facecolor", self._axes_fc))
        self._axes_ec  = self._color_btn()
        self._axes_ec.clicked.connect(lambda: self._pick("axes.edgecolor", self._axes_ec))
        self._axes_lw  = self._spin(0.1, 5.0, 0.5)
        self._title_sz = self._spin(4, 40, 1, 0)
        self._label_sz = self._spin(4, 40, 1, 0)
        self._grid_cb  = QtWidgets.QCheckBox()
        self._grid_ls  = QtWidgets.QComboBox()
        self._grid_ls.addItems(["--", "-", ":", "-."])
        self._grid_lw  = self._spin(0.1, 5.0, 0.1)
        self._grid_alpha = self._spin(0.0, 1.0, 0.05, 2)
        f.addRow("Face color:",   self._axes_fc)
        f.addRow("Edge color:",   self._axes_ec)
        f.addRow("Edge width:",   self._axes_lw)
        f.addRow("Title size:",   self._title_sz)
        f.addRow("Label size:",   self._label_sz)
        f.addRow("Grid on:",      self._grid_cb)
        f.addRow("Grid style:",   self._grid_ls)
        f.addRow("Grid width:",   self._grid_lw)
        f.addRow("Grid alpha:",   self._grid_alpha)
        return w

    def _build_ticks_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._tick_dir   = QtWidgets.QComboBox()
        self._tick_dir.addItems(["in", "out", "inout"])
        self._major_sz   = self._spin(0, 20, 1, 1)
        self._minor_sz   = self._spin(0, 20, 1, 1)
        self._tick_lw    = self._spin(0.1, 5, 0.1)
        self._tick_lsz   = self._spin(4, 40, 1, 0)
        f.addRow("Direction:",    self._tick_dir)
        f.addRow("Major size:",   self._major_sz)
        f.addRow("Minor size:",   self._minor_sz)
        f.addRow("Line width:",   self._tick_lw)
        f.addRow("Label size:",   self._tick_lsz)
        return w

    def _build_font_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._font_sz  = self._spin(4, 40, 1, 0)
        self._font_fam = QtWidgets.QComboBox()
        self._font_fam.addItems(["sans-serif", "serif", "monospace", "cursive"])
        self._font_wt  = QtWidgets.QComboBox()
        self._font_wt.addItems(["normal", "bold", "light"])
        f.addRow("Size:",    self._font_sz)
        f.addRow("Family:", self._font_fam)
        f.addRow("Weight:", self._font_wt)
        return w

    def _build_legend_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._leg_sz     = self._spin(4, 40, 1, 0)
        self._leg_frame  = QtWidgets.QCheckBox()
        self._leg_alpha  = self._spin(0.0, 1.0, 0.05, 2)
        f.addRow("Font size:",     self._leg_sz)
        f.addRow("Frame:",         self._leg_frame)
        f.addRow("Frame alpha:",   self._leg_alpha)
        return w

    def _build_cycle_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        ll = QtWidgets.QVBoxLayout(w)
        ll.setContentsMargins(8, 8, 8, 8)
        ll.addWidget(QtWidgets.QLabel(
            "Color cycle (one hex color per line, e.g. #1f77b4):"))
        self._cycle_edit = QtWidgets.QPlainTextEdit()
        self._cycle_edit.setFixedHeight(160)
        self._cycle_edit.setFont(QtGui.QFont("Courier New", 9))
        ll.addWidget(self._cycle_edit)
        ll.addWidget(QtWidgets.QLabel(
            "Leave blank to use the current matplotlib default cycle."))
        ll.addStretch()
        return w

    # ── Load from mpl ─────────────────────────────────────────────────────

    def _load(self) -> None:
        self._loading = True
        rc = mpl.rcParams
        try:
            self._lw.setValue(rc["lines.linewidth"])
            self._ls.setCurrentText(rc.get("lines.linestyle", "solid"))
            mk = str(rc.get("lines.marker", "None"))
            self._mk.setCurrentText(mk if mk in [self._mk.itemText(i)
                                                  for i in range(self._mk.count())] else "None")
            self._mks.setValue(rc["lines.markersize"])

            self._set_color_btn(self._axes_fc, rc["axes.facecolor"])
            self._set_color_btn(self._axes_ec, rc["axes.edgecolor"])
            self._axes_lw.setValue(rc["axes.linewidth"])
            self._title_sz.setValue(rc["axes.titlesize"]
                                    if isinstance(rc["axes.titlesize"], (int, float)) else 12)
            self._label_sz.setValue(rc["axes.labelsize"]
                                    if isinstance(rc["axes.labelsize"], (int, float)) else 10)
            self._grid_cb.setChecked(rc["axes.grid"])
            self._grid_ls.setCurrentText(rc.get("grid.linestyle", "--"))
            self._grid_lw.setValue(rc["grid.linewidth"])
            self._grid_alpha.setValue(rc["grid.alpha"] or 0.4)

            self._tick_dir.setCurrentText(rc["xtick.direction"])
            self._major_sz.setValue(rc["xtick.major.size"])
            self._minor_sz.setValue(rc["xtick.minor.size"])
            self._tick_lw.setValue(rc["xtick.major.width"])
            self._tick_lsz.setValue(rc["xtick.labelsize"]
                                    if isinstance(rc["xtick.labelsize"], (int, float)) else 9)

            self._font_sz.setValue(rc["font.size"]
                                   if isinstance(rc["font.size"], (int, float)) else 10)
            fam = rc.get("font.family", ["sans-serif"])
            self._font_fam.setCurrentText(fam[0] if isinstance(fam, list) else fam)
            self._font_wt.setCurrentText(str(rc.get("font.weight", "normal")))

            self._leg_sz.setValue(rc["legend.fontsize"]
                                  if isinstance(rc["legend.fontsize"], (int, float)) else 9)
            self._leg_frame.setChecked(rc["legend.frameon"])
            self._leg_alpha.setValue(rc["legend.framealpha"] or 0.8)

            # color cycle
            try:
                colors = [c["color"] for c in rc["axes.prop_cycle"]]
                self._cycle_edit.setPlainText("\n".join(colors))
            except Exception:
                self._cycle_edit.setPlainText("")

        except Exception:
            pass
        finally:
            self._loading = False

    # ── Apply to mpl ──────────────────────────────────────────────────────

    def _apply(self) -> None:
        rc = mpl.rcParams
        try:
            rc["lines.linewidth"]  = self._lw.value()
            rc["lines.linestyle"]  = self._ls.currentText()
            rc["lines.marker"]     = self._mk.currentText()
            rc["lines.markersize"] = self._mks.value()

            # axes
            rc["axes.linewidth"]  = self._axes_lw.value()
            rc["axes.titlesize"]  = int(self._title_sz.value())
            rc["axes.labelsize"]  = int(self._label_sz.value())
            rc["axes.grid"]       = self._grid_cb.isChecked()
            rc["grid.linestyle"]  = self._grid_ls.currentText()
            rc["grid.linewidth"]  = self._grid_lw.value()
            rc["grid.alpha"]      = self._grid_alpha.value()

            # ticks
            for prefix in ("xtick", "ytick"):
                rc[f"{prefix}.direction"]     = self._tick_dir.currentText()
                rc[f"{prefix}.major.size"]    = self._major_sz.value()
                rc[f"{prefix}.minor.size"]    = self._minor_sz.value()
                rc[f"{prefix}.major.width"]   = self._tick_lw.value()
                rc[f"{prefix}.labelsize"]     = int(self._tick_lsz.value())

            # font
            rc["font.size"]   = int(self._font_sz.value())
            rc["font.family"] = [self._font_fam.currentText()]
            rc["font.weight"] = self._font_wt.currentText()

            # legend
            rc["legend.fontsize"]   = int(self._leg_sz.value())
            rc["legend.frameon"]    = self._leg_frame.isChecked()
            rc["legend.framealpha"] = self._leg_alpha.value()

            # color cycle
            raw = self._cycle_edit.toPlainText().strip()
            if raw:
                from cycler import cycler
                colors = [ln.strip() for ln in raw.splitlines() if ln.strip()]
                rc["axes.prop_cycle"] = cycler(color=colors)

        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Apply failed", str(exc))
            return

        self.applied.emit()

    def _reset(self) -> None:
        from .template_manager import _tracked_keys
        tracked = _tracked_keys()
        for k in tracked:
            if k in mpl.rcParamsDefault:
                try:
                    mpl.rcParams[k] = mpl.rcParamsDefault[k]
                except Exception:
                    pass
        self._load()
        self.applied.emit()

    # ── Color button helpers ──────────────────────────────────────────────

    def _pick(self, rc_key: str, btn: QtWidgets.QPushButton) -> None:
        import matplotlib.colors as mcolors
        current = mpl.rcParams.get(rc_key, "white")
        try:
            r, g, b, a = mcolors.to_rgba(current)
            initial = QtGui.QColor.fromRgbF(r, g, b, a)
        except Exception:
            initial = QtGui.QColor("white")
        color = QtWidgets.QColorDialog.getColor(initial, self, f"Pick color: {rc_key}")
        if not color.isValid():
            return
        mpl.rcParams[rc_key] = color.name()
        self._set_color_btn(btn, color.name())
        self.applied.emit()

    @staticmethod
    def _set_color_btn(btn: QtWidgets.QPushButton, color_str: str) -> None:
        import matplotlib.colors as mcolors
        try:
            r, g, b, _ = mcolors.to_rgba(color_str)
            qc = QtGui.QColor.fromRgbF(r, g, b)
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            fg = "#000000" if luma > 0.5 else "#ffffff"
            btn.setStyleSheet(
                f"background-color: {qc.name()}; color: {fg}; border: 1px solid #888;")
            btn.setText(qc.name())
        except Exception:
            btn.setStyleSheet("")
            btn.setText("?")
