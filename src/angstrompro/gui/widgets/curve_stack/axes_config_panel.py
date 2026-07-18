# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

AxesConfigPanel — dockable widget editing the scene's AxesSpec.config.

Model-driven: every control change emits ``config_changed(patch_dict)``.
The viewer writes the patch into the RuntimeScene (single source of truth)
and applies it to the live axes; rebuilds re-apply from the scene, so the
settings survive mode switches and save/reload.

Bound to a ViewerContext (pull model): the panel re-reads effective values
from the active axes whenever the target changes.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets, Signal


class AxesConfigPanel(QtWidgets.QWidget):
    """Edit title, labels, limits, scale, grid, legend — applied live."""

    config_changed = Signal(dict)   # partial AxesConfig patch

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._context = None
        self._loading = False
        self._loaded: dict = {}     # snapshot of last-loaded field values
        self._scene_config_provider = None  # () -> dict  (raw per-mode config)
        self._build()

    # ── ViewerContext binding (pull model) ────────────────────────────────

    def bind_context(self, context) -> None:
        self._context = context
        context.target_changed.connect(self._on_target_changed)
        context.plot_rebuilt.connect(self._on_target_changed)
        self._on_target_changed()

    def set_scene_config_provider(self, fn) -> None:
        """Provide a callable () -> dict returning the raw per-mode scene config.

        Grid, legend, and aspect are user-controlled settings stored in the
        scene, not auto-computed by matplotlib.  Reading them from the live
        axes is unreliable (e.g. ax.get_xgridlines() only returns major
        gridlines, so minor-only grids appear as 'off').  The provider is
        called after _load_from_axes to overlay these values from the scene.
        """
        self._scene_config_provider = fn

    def _on_target_changed(self) -> None:
        if self._ax is not None:
            self._load_from_axes()
            self._overlay_from_scene()
        self.setEnabled(self._ax is not None)
        self._update_field_enabled()

    def _update_field_enabled(self) -> None:
        """Disable fields irrelevant to the right twin-Y axis."""
        is_right = (self._context is not None
                    and self._context.y_side == "right")
        left_only = [
            self._title, self._xlabel,
            self._xmin, self._xmax,
            self._xscale,
            self._grid, self._grid_which,
            self._aspect,
        ]
        for w in left_only:
            w.setEnabled(not is_right)

    @property
    def _ax(self):
        return self._context.active_ax if self._context is not None else None

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
        self._title.editingFinished.connect(
            lambda: self._emit_text("title", self._title))
        self._xlabel.editingFinished.connect(
            lambda: self._emit_text("xlabel", self._xlabel))
        self._ylabel.editingFinished.connect(
            lambda: self._emit_text("ylabel", self._ylabel))

        # limits — each bound (min/max) on its own row
        self._xmin = QtWidgets.QLineEdit(); self._xmin.setPlaceholderText("auto")
        self._xmax = QtWidgets.QLineEdit(); self._xmax.setPlaceholderText("auto")
        self._ymin = QtWidgets.QLineEdit(); self._ymin.setPlaceholderText("auto")
        self._ymax = QtWidgets.QLineEdit(); self._ymax.setPlaceholderText("auto")
        form.addRow("X min:", self._xmin)
        form.addRow("X max:", self._xmax)
        form.addRow("Y min:", self._ymin)
        form.addRow("Y max:", self._ymax)
        for w in (self._xmin, self._xmax):
            w.editingFinished.connect(
                lambda: self._emit_lim("xlim", self._xmin, self._xmax))
        for w in (self._ymin, self._ymax):
            w.editingFinished.connect(
                lambda: self._emit_lim("ylim", self._ymin, self._ymax))

        # scale — X and Y each on their own row
        _scales = ["linear", "log", "symlog", "logit"]
        self._xscale = QtWidgets.QComboBox(); self._xscale.addItems(_scales)
        self._yscale = QtWidgets.QComboBox(); self._yscale.addItems(_scales)
        form.addRow("X scale:", self._xscale)
        form.addRow("Y scale:", self._yscale)
        self._xscale.currentTextChanged.connect(
            lambda s: self._emit({"xscale": s}))
        self._yscale.currentTextChanged.connect(
            lambda s: self._emit({"yscale": s}))

        # grid — Show checkbox on its own row, Which combo on the next
        self._grid = QtWidgets.QCheckBox("Show")
        self._grid_which = QtWidgets.QComboBox()
        self._grid_which.addItems(["major", "minor", "both"])
        form.addRow("Grid:", self._grid)
        form.addRow("Grid which:", self._grid_which)
        self._grid.toggled.connect(lambda _: self._emit_grid())
        self._grid_which.currentTextChanged.connect(lambda _: self._emit_grid())

        # legend — Show checkbox on its own row, Loc combo on the next
        self._legend = QtWidgets.QCheckBox("Show")
        self._legend_loc = QtWidgets.QComboBox()
        self._legend_loc.addItems(["best", "upper right", "upper left",
                                   "lower right", "lower left",
                                   "center", "center left", "center right"])
        form.addRow("Legend:", self._legend)
        form.addRow("Legend loc:", self._legend_loc)
        self._legend.toggled.connect(lambda _: self._emit_legend())
        self._legend_loc.currentTextChanged.connect(lambda _: self._emit_legend())

        # aspect
        self._aspect = QtWidgets.QComboBox()
        self._aspect.addItems(["auto", "equal"])
        form.addRow("Aspect:", self._aspect)
        self._aspect.currentTextChanged.connect(
            lambda s: self._emit({"aspect": s}))

        layout.addLayout(form)
        layout.addStretch()   # dock: keep form at the top
        self.setMinimumWidth(320)

    # ── Emit helpers ──────────────────────────────────────────────────────

    def _emit(self, patch: dict) -> None:
        if self._loading:
            return
        self.config_changed.emit(patch)

    def _emit_text(self, field: str, widget: QtWidgets.QLineEdit) -> None:
        if self._loading:
            return
        val = widget.text()
        if val == self._loaded.get(field):
            return   # editingFinished fires on focus-out even without changes
        self._loaded[field] = val
        self.config_changed.emit({field: val})

    def _emit_lim(self, field: str, lo: QtWidgets.QLineEdit,
                  hi: QtWidgets.QLineEdit) -> None:
        if self._loading:
            return
        if not lo.text().strip() and not hi.text().strip():
            val = None          # both cleared → autoscale
        else:
            try:
                val = (float(lo.text()), float(hi.text()))
            except ValueError:
                return          # incomplete / invalid — wait for more input
        if val == self._loaded.get(field):
            return
        self._loaded[field] = val
        self.config_changed.emit(
            {field: list(val) if val is not None else None})

    def _emit_grid(self) -> None:
        self._emit({"grid":       self._grid.isChecked(),
                    "grid_which": self._grid_which.currentText()})

    def _emit_legend(self) -> None:
        self._emit({"legend":     self._legend.isChecked(),
                    "legend_loc": self._legend_loc.currentText()})

    # ── Load effective values from live axes ──────────────────────────────

    def _load_from_axes(self) -> None:
        ax = self._ax
        self._loading = True
        try:
            self._title.setText(ax.get_title())
            self._xlabel.setText(ax.get_xlabel())
            self._ylabel.setText(ax.get_ylabel())
            self._loaded["title"]  = ax.get_title()
            self._loaded["xlabel"] = ax.get_xlabel()
            self._loaded["ylabel"] = ax.get_ylabel()

            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            self._xmin.setText(f"{xmin:.6g}")
            self._xmax.setText(f"{xmax:.6g}")
            self._ymin.setText(f"{ymin:.6g}")
            self._ymax.setText(f"{ymax:.6g}")
            self._loaded["xlim"] = (float(f"{xmin:.6g}"), float(f"{xmax:.6g}"))
            self._loaded["ylim"] = (float(f"{ymin:.6g}"), float(f"{ymax:.6g}"))

            self._xscale.setCurrentText(ax.get_xscale())
            self._yscale.setCurrentText(ax.get_yscale())

            # grid/legend/aspect — read from live axes as fallback only;
            # _overlay_from_scene() will correct these from the scene config
            # (ax.get_xgridlines() only returns major lines and is unreliable
            # for detecting minor-only or 'both' grids)
            try:
                grid_on = any(l.get_visible() for l in ax.get_xgridlines())
            except Exception:
                grid_on = False
            self._grid.setChecked(grid_on)
            self._legend.setChecked(ax.get_legend() is not None)
            self._aspect.setCurrentText(
                ax.get_aspect() if ax.get_aspect() in ("auto", "equal")
                else "auto")
        finally:
            self._loading = False

    def _overlay_from_scene(self) -> None:
        """Overlay grid/legend/aspect from scene config (authoritative source).

        These are user-controlled settings that must not be re-derived from
        the live axes — matplotlib's API for reading them back is unreliable
        (e.g. get_xgridlines() only returns major lines).
        """
        if self._scene_config_provider is None:
            return
        d = self._scene_config_provider()
        if not d:
            return
        self._loading = True
        try:
            if "grid" in d:
                self._grid.setChecked(bool(d["grid"]))
            if "grid_which" in d:
                self._grid_which.setCurrentText(d["grid_which"])
            if "legend" in d:
                self._legend.setChecked(bool(d["legend"]))
            if "legend_loc" in d:
                self._legend_loc.setCurrentText(d["legend_loc"])
            if "aspect" in d and d["aspect"] in ("auto", "equal"):
                self._aspect.setCurrentText(d["aspect"])
        finally:
            self._loading = False
