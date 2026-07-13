# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

AxesConfigPanel — dockable widget to edit axes fields and apply them
to the live matplotlib Axes immediately (ax.set_*() + draw_idle()).

Bound to a ViewerContext (pull model): call ``bind_context(ctx)`` once;
the panel re-pulls from the active axes whenever the target changes.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets


class AxesConfigPanel(QtWidgets.QWidget):
    """Edit title, labels, limits, scale, grid, legend — apply live."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._context = None
        self._build()

    # ── ViewerContext binding (pull model) ────────────────────────────────

    def bind_context(self, context) -> None:
        self._context = context
        context.target_changed.connect(self._on_target_changed)
        self._on_target_changed()

    def _on_target_changed(self) -> None:
        if self._ax is not None:
            self._load_from_axes()
        self.setEnabled(self._ax is not None)

    @property
    def _ax(self):
        return self._context.ax if self._context is not None else None

    @property
    def _canvas(self):
        return self._context.canvas if self._context is not None else None

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(6)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._title  = QtWidgets.QLineEdit()
        self._xlabel = QtWidgets.QLineEdit()
        self._ylabel = QtWidgets.QLineEdit()
        form.addRow("Title:",   self._title)
        form.addRow("X label:", self._xlabel)
        form.addRow("Y label:", self._ylabel)

        # limits
        lim_widget = QtWidgets.QWidget()
        lim_lay    = QtWidgets.QGridLayout(lim_widget)
        lim_lay.setContentsMargins(0, 0, 0, 0)
        lim_lay.setSpacing(4)

        self._xmin = QtWidgets.QLineEdit(); self._xmin.setPlaceholderText("auto")
        self._xmax = QtWidgets.QLineEdit(); self._xmax.setPlaceholderText("auto")
        self._ymin = QtWidgets.QLineEdit(); self._ymin.setPlaceholderText("auto")
        self._ymax = QtWidgets.QLineEdit(); self._ymax.setPlaceholderText("auto")
        lim_lay.addWidget(QtWidgets.QLabel("X:"),   0, 0)
        lim_lay.addWidget(self._xmin, 0, 1)
        lim_lay.addWidget(QtWidgets.QLabel("–"),    0, 2)
        lim_lay.addWidget(self._xmax, 0, 3)
        lim_lay.addWidget(QtWidgets.QLabel("Y:"),   1, 0)
        lim_lay.addWidget(self._ymin, 1, 1)
        lim_lay.addWidget(QtWidgets.QLabel("–"),    1, 2)
        lim_lay.addWidget(self._ymax, 1, 3)
        form.addRow("Limits:", lim_widget)

        # scale
        scale_widget = QtWidgets.QWidget()
        scale_lay    = QtWidgets.QHBoxLayout(scale_widget)
        scale_lay.setContentsMargins(0, 0, 0, 0)
        scale_lay.setSpacing(8)
        _scales = ["linear", "log", "symlog", "logit"]
        self._xscale = QtWidgets.QComboBox(); self._xscale.addItems(_scales)
        self._yscale = QtWidgets.QComboBox(); self._yscale.addItems(_scales)
        scale_lay.addWidget(QtWidgets.QLabel("X:")); scale_lay.addWidget(self._xscale)
        scale_lay.addWidget(QtWidgets.QLabel("Y:")); scale_lay.addWidget(self._yscale)
        scale_lay.addStretch()
        form.addRow("Scale:", scale_widget)

        # grid
        grid_widget = QtWidgets.QWidget()
        grid_lay    = QtWidgets.QHBoxLayout(grid_widget)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        self._grid      = QtWidgets.QCheckBox("Show")
        self._grid_which = QtWidgets.QComboBox()
        self._grid_which.addItems(["major", "minor", "both"])
        grid_lay.addWidget(self._grid)
        grid_lay.addWidget(QtWidgets.QLabel("Which:"))
        grid_lay.addWidget(self._grid_which)
        grid_lay.addStretch()
        form.addRow("Grid:", grid_widget)

        # legend
        leg_widget = QtWidgets.QWidget()
        leg_lay    = QtWidgets.QHBoxLayout(leg_widget)
        leg_lay.setContentsMargins(0, 0, 0, 0)
        self._legend     = QtWidgets.QCheckBox("Show")
        self._legend_loc = QtWidgets.QComboBox()
        self._legend_loc.addItems(["best", "upper right", "upper left",
                                   "lower right", "lower left",
                                   "center", "center left", "center right"])
        leg_lay.addWidget(self._legend)
        leg_lay.addWidget(QtWidgets.QLabel("Loc:"))
        leg_lay.addWidget(self._legend_loc)
        leg_lay.addStretch()
        form.addRow("Legend:", leg_widget)

        # aspect
        self._aspect = QtWidgets.QComboBox()
        self._aspect.addItems(["auto", "equal"])
        form.addRow("Aspect:", self._aspect)

        layout.addLayout(form)

        # buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_apply = QtWidgets.QPushButton("Apply")
        btn_apply.setDefault(True)
        btn_apply.clicked.connect(self._apply)
        btn_reload = QtWidgets.QPushButton("Reload")
        btn_reload.setToolTip("Re-read current values from the plot")
        btn_reload.clicked.connect(self._on_target_changed)
        btn_reset = QtWidgets.QPushButton("Reset to Defaults")
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_reset)
        btn_row.addWidget(btn_reload)
        btn_row.addStretch()
        btn_row.addWidget(btn_apply)
        layout.addLayout(btn_row)

        layout.addStretch()   # dock: keep form at the top
        self.setMinimumWidth(320)

    # ── Load from live axes ───────────────────────────────────────────────

    def _load_from_axes(self) -> None:
        ax = self._ax
        self._title.setText(ax.get_title())
        self._xlabel.setText(ax.get_xlabel())
        self._ylabel.setText(ax.get_ylabel())

        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        self._xmin.setText(f"{xmin:.6g}")
        self._xmax.setText(f"{xmax:.6g}")
        self._ymin.setText(f"{ymin:.6g}")
        self._ymax.setText(f"{ymax:.6g}")

        self._xscale.setCurrentText(ax.get_xscale())
        self._yscale.setCurrentText(ax.get_yscale())

        try:
            grid_on = any(l.get_visible() for l in ax.get_xgridlines())
        except Exception:
            grid_on = False
        self._grid.setChecked(grid_on)
        self._legend.setChecked(ax.get_legend() is not None)
        if ax.get_legend() is not None:
            pass  # legend_loc is hard to read back reliably

        self._aspect.setCurrentText(
            ax.get_aspect() if ax.get_aspect() in ("auto", "equal") else "auto")

    # ── Apply to live axes ────────────────────────────────────────────────

    def _apply(self) -> None:
        ax = self._ax
        if ax is None:
            return

        ax.set_title(self._title.text())
        ax.set_xlabel(self._xlabel.text())
        ax.set_ylabel(self._ylabel.text())

        xlim = self._parse_lim(self._xmin, self._xmax)
        ylim = self._parse_lim(self._ymin, self._ymax)
        if xlim:
            ax.set_xlim(xlim)
        else:
            ax.autoscale(axis="x")
        if ylim:
            ax.set_ylim(ylim)
        else:
            ax.autoscale(axis="y")

        ax.set_xscale(self._xscale.currentText())
        ax.set_yscale(self._yscale.currentText())

        if self._grid.isChecked():
            ax.grid(True, which=self._grid_which.currentText(),
                    linestyle="--", alpha=0.4)
        else:
            ax.grid(False)

        if self._legend.isChecked():
            ax.legend(loc=self._legend_loc.currentText())
        else:
            leg = ax.get_legend()
            if leg is not None:
                leg.remove()

        ax.set_aspect(self._aspect.currentText())

        self._canvas.draw_idle()

    def _reset(self) -> None:
        ax = self._ax
        if ax is None:
            return
        ax.set_title("")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.autoscale(axis="both")
        ax.set_xscale("linear")
        ax.set_yscale("linear")
        ax.grid(False)
        leg = ax.get_legend()
        if leg is not None:
            leg.remove()
        ax.set_aspect("auto")
        self._canvas.draw_idle()
        self._load_from_axes()

    @staticmethod
    def _parse_lim(lo: QtWidgets.QLineEdit,
                   hi: QtWidgets.QLineEdit) -> tuple | None:
        try:
            return (float(lo.text()), float(hi.text()))
        except ValueError:
            return None
