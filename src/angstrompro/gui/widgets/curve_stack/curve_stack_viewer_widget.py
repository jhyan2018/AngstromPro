# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

CurveStackViewerWidget — container widget for CurveStackViewer.

Layout
------
Left  : dataset/curve tree + Remove / All / None buttons
Right : mode selector toolbar + swappable plot widget

The left panel owns the display list (which datasets/curves are shown and
their visibility).  The right panel is swapped when the user changes mode.
Each plot widget (StackPlotWidget, ColormapPlotWidget, …) is a self-contained
QWidget that implements BasePlotWidget.
"""
from __future__ import annotations

import copy
import logging

import matplotlib as mpl
import numpy as np

from angstrompro.utils.qt_compat import QtCore, QtWidgets

from .base_plot_widget import BasePlotWidget
from .prepare import prepare_entry
from .stack_plot_widget import StackPlotWidget
from . import template_manager as tmgr

log = logging.getLogger(__name__)

_ITEM_ROLE = QtCore.Qt.ItemDataRole.UserRole

_MODES: list[tuple[str, str]] = [
    ("stack",    "Stack"),
    ("colormap", "Colormap"),
]


class CurveStackViewerWidget(QtWidgets.QWidget):
    """
    Top-level widget used as the central widget of CurveStackViewer.

    Public API (called by the module)
    ----------------------------------
    add_dataset(name, uds)   — add / replace a dataset
    remove_dataset(name)     — remove a dataset
    clear()                  — remove all datasets
    apply_config(cfg)        — push new preferences dict down to active plot widget
    save_scene(name)         — capture current state as ScenePlot
    restore_scene(scene)     — restore full state from ScenePlot

    Signals
    -------
    extract_requested(list)  — emits list of (suggested_name, UdsDataStru) when
                               the user clicks "Extract to workspace"
    """

    extract_requested = QtCore.pyqtSignal(list)   # list[(str, UdsDataStru)]
    cleared           = QtCore.pyqtSignal()        # emitted when Clear All is pressed

    def __init__(self, config: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self._config:   dict            = config or {}
        self._datasets: dict[str, dict] = {}          # name → prepare_entry result
        self._checked:  dict[str, list[bool]] = {}    # name → per-curve visibility
        self._plot_widget: BasePlotWidget | None = None
        self._setup_ui()
        self._set_mode("stack")

    # ── UI construction ───────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        outer.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())

        self._right_w = QtWidgets.QWidget()
        self._right_l = QtWidgets.QVBoxLayout(self._right_w)
        self._right_l.setContentsMargins(0, 0, 0, 0)
        self._right_l.setSpacing(0)
        self._right_l.addLayout(self._build_mode_bar())
        # plot widget is inserted here by _set_mode()

        splitter.addWidget(self._right_w)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 600])

    def _build_left_panel(self) -> QtWidgets.QWidget:
        w  = QtWidgets.QWidget()
        w.setMinimumWidth(0)
        ll = QtWidgets.QVBoxLayout(w)
        ll.setContentsMargins(4, 4, 4, 4)
        ll.setSpacing(4)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(1)
        self._tree.setHeaderLabel("Datasets / Curves")
        self._tree.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.itemChanged.connect(self._on_tree_item_changed)
        ll.addWidget(self._tree)

        btn_row    = QtWidgets.QHBoxLayout()
        btn_remove = QtWidgets.QPushButton("Remove")
        btn_all    = QtWidgets.QPushButton("All")
        btn_none   = QtWidgets.QPushButton("None")
        btn_remove.setToolTip("Remove selected dataset from plot")
        btn_all.setToolTip("Show all curves")
        btn_none.setToolTip("Hide all curves")
        btn_remove.clicked.connect(self._on_remove)
        btn_all.clicked.connect(lambda: self._check_all(True))
        btn_none.clicked.connect(lambda: self._check_all(False))
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        ll.addLayout(btn_row)

        btn_extract = QtWidgets.QPushButton("Extract to workspace")
        btn_extract.setToolTip(
            "Extract selected curves as individual WorkspaceItems.\n"
            "Select items in the tree above, then click here.")
        btn_extract.clicked.connect(self._on_extract)
        ll.addWidget(btn_extract)
        return w

    def _build_mode_bar(self) -> QtWidgets.QHBoxLayout:
        bar = QtWidgets.QHBoxLayout()
        bar.setContentsMargins(4, 4, 4, 2)
        bar.setSpacing(4)
        bar.addWidget(QtWidgets.QLabel("Mode:"))

        self._mode_combo = QtWidgets.QComboBox()
        for key, label in _MODES:
            self._mode_combo.addItem(label, key)
        self._mode_combo.currentIndexChanged.connect(
            lambda _: self._set_mode(self._mode_combo.currentData()))
        bar.addWidget(self._mode_combo)

        btn_clear = QtWidgets.QPushButton("Clear All")
        btn_clear.clicked.connect(self._on_clear_all)
        bar.addWidget(btn_clear)

        bar.addStretch()

        return bar

    # ── Template ──────────────────────────────────────────────────────────

    def _refresh_template_menu(self) -> None:
        self._tpl_load_menu.clear()
        names = tmgr.list_templates()
        if not names:
            act = self._tpl_load_menu.addAction("(no templates saved)")
            act.setEnabled(False)
            return
        for name in names:
            act = self._tpl_load_menu.addAction(name)
            act.triggered.connect(lambda _checked, n=name: self._load_template(n))

    def _load_template(self, name: str) -> None:
        try:
            rcparams, widget_style = tmgr.load_template(name)
        except Exception as exc:
            log.warning("Failed to load template %r: %s", name, exc)
            return
        tmgr.apply_rcparams(rcparams)
        # merge widget style into config and push to active plot widget
        self._config.update({k: v for k, v in widget_style.items()
                             if k in tmgr.WIDGET_DEFAULTS})
        self._plot_widget.apply_config(self._config)
        # sync colormap combo if present
        if hasattr(self._plot_widget, "_cmap_combo"):
            cmap = widget_style.get("colormap", "RdBu_r")
            self._plot_widget._cmap_combo.setCurrentText(cmap)
        self._plot_widget.refresh(self._datasets, self._checked)

    def apply_template_by_name(self, name: str) -> None:
        """Public entry point called by the module on startup."""
        if name:
            self._load_template(name)

    def _on_save_template(self) -> None:
        import matplotlib as mpl
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Template", "Template name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        widget_style = dict(self._config)
        if hasattr(self._plot_widget, "_cmap_combo"):
            widget_style["colormap"] = self._plot_widget._cmap_combo.currentText()

        try:
            tmgr.save_template(name, dict(mpl.rcParams), widget_style)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(exc))

    # ── Mode switching ────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        new_widget = self._create_plot_widget(mode)

        if self._plot_widget is not None:
            self._right_l.removeWidget(self._plot_widget)
            self._plot_widget.hide()
            self._plot_widget.deleteLater()

        self._plot_widget = new_widget
        self._right_l.addWidget(self._plot_widget)
        self._plot_widget.apply_config(self._config)
        self._plot_widget.refresh(self._datasets, self._checked)

    def _create_plot_widget(self, mode: str) -> BasePlotWidget:
        if mode == "stack":
            return StackPlotWidget(self._config, self)
        if mode == "colormap":
            from .colormap_plot_widget import ColormapPlotWidget
            return ColormapPlotWidget(self._config, self)
        raise ValueError(f"Unknown plot mode: {mode!r}")

    # ── Public API ────────────────────────────────────────────────────────

    def add_dataset(self, name: str, uds) -> None:
        try:
            entry = prepare_entry(name, uds)
        except Exception as exc:
            log.warning("CurveStackViewer: cannot display %r: %s", name, exc)
            return
        self._datasets[name] = entry
        n = entry["y"].shape[0]
        if len(self._checked.get(name, [])) != n:
            self._checked[name] = [True] * n
        self._rebuild_tree()
        self._plot_widget.refresh(self._datasets, self._checked)

    def remove_dataset(self, name: str) -> None:
        self._datasets.pop(name, None)
        self._checked.pop(name, None)
        self._rebuild_tree()
        self._plot_widget.refresh(self._datasets, self._checked)

    def clear(self) -> None:
        self._datasets.clear()
        self._checked.clear()
        self._tree.clear()
        self._plot_widget.clear()

    def _on_clear_all(self) -> None:
        self.clear()
        self.cleared.emit()

    def apply_config(self, config: dict) -> None:
        self._config = config
        self._plot_widget.apply_config(config)

    def save_scene(self, name: str):
        """Capture current display state as a ScenePlot (data copies + styles)."""
        from angstrompro.core.data.scene_plot import (
            CanvasConfig, ScenePlot, PlotStyle, SceneEntry)
        import copy

        mode = self._mode_combo.currentData()

        # per-curve styles from the active plot widget
        line_styles: dict[tuple[str, int], dict] = {}
        if hasattr(self._plot_widget, "get_line_styles"):
            line_styles = self._plot_widget.get_line_styles()

        offset = 0.0
        if hasattr(self._plot_widget, "get_offset"):
            offset = self._plot_widget.get_offset()

        colormap = self._config.get("colormap", "RdBu_r")
        if hasattr(self._plot_widget, "_cmap_combo"):
            colormap = self._plot_widget._cmap_combo.currentText()

        entries = []
        for ds_name, entry in self._datasets.items():
            y_arr   = entry["y"]
            checked = self._checked.get(ds_name, [True] * y_arr.shape[0])
            uds     = entry["uds"]
            n       = y_arr.shape[0]
            for i, visible in enumerate(checked):
                s = line_styles.get((ds_name, i), {})
                curve_label = f"{ds_name} / Line {i}" if n > 1 else ds_name
                style = PlotStyle(
                    color     = s.get("color", ""),
                    linewidth = s.get("linewidth", 1.5),
                    linestyle = s.get("linestyle", "solid"),
                    marker    = s.get("marker", ""),
                    alpha     = s.get("alpha", 1.0),
                    label     = s.get("label", curve_label),
                    visible   = visible,
                )
                entries.append(SceneEntry(data=copy.deepcopy(uds), style=style))

        canvas_config = CanvasConfig(
            plot_mode = mode,
            offset    = offset,
            colormap  = colormap,
            show_grid = self._config.get("show_grid", False),
        )
        return ScenePlot(name=name, entries=entries, canvas_config=canvas_config)

    def restore_scene(self, scene) -> None:
        """Restore full display state from a ScenePlot."""
        from .stack_plot_widget import StackPlotWidget

        self.clear()

        # switch mode
        cc   = scene.canvas_config
        mode = cc.plot_mode
        idx  = next((i for i in range(self._mode_combo.count())
                     if self._mode_combo.itemData(i) == mode), 0)
        self._mode_combo.blockSignals(True)
        self._mode_combo.setCurrentIndex(idx)
        self._mode_combo.blockSignals(False)
        self._set_mode(mode)

        # restore offset
        if isinstance(self._plot_widget, StackPlotWidget):
            self._plot_widget.set_offset(cc.offset)

        # restore colormap
        if hasattr(self._plot_widget, "_cmap_combo"):
            self._plot_widget._cmap_combo.setCurrentText(cc.colormap)

        # add each entry as its own dataset (1 curve each)
        for entry in scene.entries:
            ds_name = entry.style.label or entry.data.name
            self._datasets[ds_name] = prepare_entry(ds_name, entry.data)
            self._checked[ds_name]  = [entry.style.visible]

        self._rebuild_tree()
        self._plot_widget.refresh(self._datasets, self._checked)

    # ── Extract ───────────────────────────────────────────────────────────

    def _on_extract(self) -> None:
        """Collect selected tree items and emit extract_requested signal."""
        selected = self._tree.selectedItems()
        if not selected:
            # nothing selected — fall back to all visible curves
            selected = [self._tree.topLevelItem(i)
                        for i in range(self._tree.topLevelItemCount())]

        pairs: list[tuple[str, object]] = []
        seen: set[tuple[str, int]] = set()

        for item in selected:
            data = item.data(0, _ITEM_ROLE)
            if data is None:
                continue
            if data[0] == "dataset":
                # extract all curves of this dataset
                ds_name = data[1]
                entry   = self._datasets.get(ds_name)
                if entry is None:
                    continue
                n = entry["y"].shape[0]
                for i in range(n):
                    if (ds_name, i) in seen:
                        continue
                    seen.add((ds_name, i))
                    uds  = self._extract_curve(entry, i, ds_name)
                    label = f"{ds_name} / Line {i}" if n > 1 else ds_name
                    pairs.append((label, uds))
            elif data[0] == "curve":
                _, ds_name, i = data
                if (ds_name, i) in seen:
                    continue
                seen.add((ds_name, i))
                entry = self._datasets.get(ds_name)
                if entry is None:
                    continue
                uds   = self._extract_curve(entry, i, ds_name)
                n     = entry["y"].shape[0]
                label = f"{ds_name} / Line {i}" if n > 1 else ds_name
                pairs.append((label, uds))

        if pairs:
            self.extract_requested.emit(pairs)

    @staticmethod
    def _extract_curve(entry: dict, row: int, ds_name: str):
        """Return a 1D UdsDataStru for row *row* of *entry*, from original UDS."""
        from angstrompro.core.data.uds_data import Axis, UdsDataStru

        orig = entry["uds"]
        data = np.asarray(orig.data, dtype=float)

        if data.ndim == 1:
            y_values = data.copy()
        else:
            y_values = data[row].copy()

        axes      = copy.deepcopy(orig.axes)
        info      = copy.deepcopy(orig.info) if hasattr(orig, "info") else {}
        n         = data.shape[0] if data.ndim == 2 else 1
        row_name  = f"{ds_name} / Line {row}" if n > 1 else ds_name

        return UdsDataStru(
            name         = row_name,
            data         = y_values,
            axes         = axes,
            info         = info,
            proc_history = [],
            landmarks    = {},
        )

    # ── Tree ─────────────────────────────────────────────────────────────

    def _rebuild_tree(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        _Checked   = QtCore.Qt.CheckState.Checked
        _Unchecked = QtCore.Qt.CheckState.Unchecked
        _UserCheck = QtCore.Qt.ItemFlag.ItemIsUserCheckable
        _AutoTri   = QtCore.Qt.ItemFlag.ItemIsAutoTristate

        for name, entry in self._datasets.items():
            n_curves = entry["y"].shape[0]
            checked  = self._checked.get(name, [True] * n_curves)

            top = QtWidgets.QTreeWidgetItem([name])
            top.setData(0, _ITEM_ROLE, ("dataset", name))
            top.setFlags(top.flags() | _UserCheck | _AutoTri)

            for i in range(n_curves):
                child = QtWidgets.QTreeWidgetItem([f"Line {i}"])
                child.setData(0, _ITEM_ROLE, ("curve", name, i))
                child.setFlags(child.flags() | _UserCheck)
                child.setCheckState(0, _Checked if checked[i] else _Unchecked)
                top.addChild(child)

            top.setExpanded(True)
            self._tree.addTopLevelItem(top)
        self._tree.blockSignals(False)

    def _on_tree_item_changed(self, item, _col) -> None:
        data = item.data(0, _ITEM_ROLE)
        if data is None or data[0] != "curve":
            return
        _, name, idx = data
        if name in self._checked:
            self._checked[name][idx] = (
                item.checkState(0) == QtCore.Qt.CheckState.Checked)
            self._plot_widget.refresh(self._datasets, self._checked)

    def _on_remove(self) -> None:
        sel = self._tree.currentItem()
        if sel is None:
            return
        data = sel.data(0, _ITEM_ROLE)
        if data is None:
            return
        self.remove_dataset(data[1])

    def _check_all(self, checked: bool) -> None:
        for name in self._checked:
            self._checked[name] = [checked] * len(self._checked[name])
        self._rebuild_tree()
        self._plot_widget.refresh(self._datasets, self._checked)
