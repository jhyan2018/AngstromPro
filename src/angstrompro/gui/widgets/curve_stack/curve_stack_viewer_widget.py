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
        from .viewer_context import ViewerContext
        self._config:   dict            = config or {}
        self._datasets: dict[str, dict] = {}          # name → prepare_entry result
        self._checked:  dict[str, list[bool]] = {}    # name → per-curve visibility
        self._plot_widget: BasePlotWidget | None = None
        self._plot_widgets: dict[str, BasePlotWidget] = {}   # mode → cached widget
        self._cmap_palette: list[str] = []            # user palette from preferences
        self._widget_extras: dict[str, dict] = {}     # mode → restored scene extras
        self._restored_manual_colors: dict[tuple, str] = {}  # pending per-line pins
        self._bulk_update: bool = False               # suppress per-child refreshes
        self.view_context = ViewerContext(self)            # identity of active view objects
        self._setup_ui()
        self._set_mode("stack")

    # ── UI construction ───────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        # override the layout-derived minimum so right-side docks can grow;
        # inner toolbars clip gracefully when squeezed
        self.setMinimumWidth(400)

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
        # cached plot widgets live in a stack — switching modes preserves
        # each widget's toolbar state (color mode, offset, colormap, …)
        self._plot_stack = QtWidgets.QStackedWidget()
        self._right_l.addWidget(self._plot_stack)

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
        ll.addWidget(self._tree, stretch=1)   # tree takes all spare vertical space

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

        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)

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
            rcparams_delta, widget_extras = tmgr.load_template(name)
        except Exception as exc:
            log.warning("Failed to load template %r: %s", name, exc)
            return

        tmgr.apply_rcparams(rcparams_delta)

        mode  = self._mode_combo.currentData() or "stack"
        extra = tmgr.get_widget_extra(widget_extras, mode)

        # apply widget-type extras to the active plot widget
        if hasattr(self._plot_widget, "set_color_mode"):
            self._plot_widget.set_color_mode(extra.get("color_mode", "auto"))
        if hasattr(self._plot_widget, "set_offset"):
            self._plot_widget.set_offset(extra.get("offset", 0.0))
        from .colormap_plot_widget import ColormapPlotWidget
        if isinstance(self._plot_widget, ColormapPlotWidget):
            cmb = self._plot_widget._cmap_combo
            cmb.blockSignals(True)
            cmb.setCurrentText(extra.get("colormap", "RdBu_r"))
            cmb.blockSignals(False)

        self._plot_widget.refresh(self._datasets, self._checked)

    def apply_template_by_name(self, name: str) -> None:
        """Public entry point called by the module on startup."""
        if name:
            self._load_template(name)

    def _on_save_template(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Template", "Template name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        mode  = self._mode_combo.currentData() or "stack"
        extra: dict = {}
        if hasattr(self._plot_widget, "color_mode"):
            extra["color_mode"] = self._plot_widget.color_mode
        if hasattr(self._plot_widget, "get_offset"):
            extra["offset"] = self._plot_widget.get_offset()
        if hasattr(self._plot_widget, "_cmap_combo"):
            extra["colormap"] = self._plot_widget._cmap_combo.currentText()

        # warn if this widget type already exists in the template
        existing = tmgr.list_templates()
        if name in existing:
            from angstrompro.gui.widgets.curve_stack import template_manager as _t
            path = _t.templates_dir() / f"{name}.scet"
            try:
                import json as _j
                raw = _j.loads(path.read_text(encoding="utf-8"))
                if mode in raw.get("widget_extras", {}):
                    ans = QtWidgets.QMessageBox.question(
                        self, "Override template?",
                        f"Template '{name}' already has settings for "
                        f"widget type '{mode}'.\n\nOverride?",
                        QtWidgets.QMessageBox.StandardButton.Yes |
                        QtWidgets.QMessageBox.StandardButton.No,
                    )
                    if ans != QtWidgets.QMessageBox.StandardButton.Yes:
                        return
            except Exception:
                pass

        try:
            tmgr.save_template(name, mode, extra)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(exc))

    # ── Mode switching ────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        widget = self._plot_widgets.get(mode)
        if widget is None:
            widget = self._create_plot_widget(mode)
            widget.apply_config(self._config)
            if self._cmap_palette and hasattr(widget, "set_cmap_palette"):
                widget.set_cmap_palette(self._cmap_palette)
            if hasattr(widget, "artists_rebuilt"):
                # artists replaced (e.g. color mode Line2D↔LC) — panels re-pull
                widget.artists_rebuilt.connect(self.view_context.refresh_selection)
            self._plot_widgets[mode] = widget
            self._plot_stack.addWidget(widget)
            # apply extras restored from a scene before this widget existed
            self._apply_widget_extra(widget, mode)
            if mode == "stack":
                self._apply_manual_colors(widget)

        self._plot_widget = widget
        self._plot_stack.setCurrentWidget(widget)
        # data may have changed while this widget was hidden — resync
        self._plot_widget.refresh(self._datasets, self._checked)
        self.view_context.set_plot_widget(self._plot_widget)

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
        is_replace = name in self._datasets
        self._datasets[name] = entry
        n = entry["y"].shape[0]
        if len(self._checked.get(name, [])) != n:
            self._checked[name] = [True] * n
        self._rebuild_tree()
        if is_replace:
            self._plot_widget.remove_lines(name)
        self._plot_widget.add_lines(name, entry, self._checked[name])

    def remove_dataset(self, name: str) -> None:
        self._datasets.pop(name, None)
        self._checked.pop(name, None)
        self._rebuild_tree()
        self._plot_widget.remove_lines(name)

    def clear(self) -> None:
        self._datasets.clear()
        self._checked.clear()
        self._tree.clear()
        for w in self._plot_widgets.values():
            w.clear()
        self.view_context.set_selected_key(None)

    def _on_clear_all(self) -> None:
        self.clear()
        self.cleared.emit()

    def apply_config(self, config: dict) -> None:
        self._config = config
        for w in self._plot_widgets.values():
            w.apply_config(config)

    def set_cmap_palette(self, names: list[str]) -> None:
        """Repopulate the colormap combos with user's chosen palette."""
        # custom colormaps (non-mpl names) must be registered before use
        try:
            from angstrompro.gui.resources.colormaps import register_all
            register_all()
        except Exception:
            log.warning("Could not register custom colormaps", exc_info=True)
        self._cmap_palette = list(names)
        for w in self._plot_widgets.values():
            if hasattr(w, "set_cmap_palette"):
                w.set_cmap_palette(names)

    def save_scene(self, name: str):
        """Capture current display state as a ScenePlot."""
        import copy
        import matplotlib as mpl
        from angstrompro.core.data.scene_plot import (
            ScenePlot, FigureConfig, AxesSpec, AxesConfig, ArtistSpec, LineStyle)

        mode = self._mode_combo.currentData()

        # gather from ALL cached plot widgets so hidden-mode state is kept too
        stack_w = self._plot_widgets.get("stack")
        cmap_w  = self._plot_widgets.get("colormap")

        line_styles: dict[tuple[str, int], dict] = {}
        offset        = 0.0
        color_mode    = "auto"
        manual_colors = {}
        if stack_w is not None:
            line_styles   = stack_w.get_line_styles()
            offset        = stack_w.get_offset()
            color_mode    = stack_w.color_mode
            manual_colors = dict(stack_w._manual_colors)

        colormap  = self._config.get("default_cmap", "RdBu_r")
        symmetric = True
        if cmap_w is not None:
            colormap  = cmap_w._cmap_combo.currentText()
            symmetric = cmap_w._sym_check.isChecked()

        widget_extras = {
            "stack":    {"color_mode": color_mode, "offset": offset},
            "colormap": {"colormap": colormap, "symmetric": symmetric},
        }
        artists = []
        for ds_name, entry in self._datasets.items():
            y_arr   = entry["y"]
            n       = y_arr.shape[0]
            checked = self._checked.get(ds_name, [True] * n)
            uds     = entry["uds"]
            # representative style from first row
            s = line_styles.get((ds_name, 0), {})
            # per-row style overrides: only save rows that differ (non-empty color)
            row_styles = {}
            for i in range(n):
                ri = line_styles.get((ds_name, i), {})
                if ri.get("color", ""):
                    row_styles[i] = ri
            artist = ArtistSpec(
                kind    = "line",
                style   = LineStyle(
                    color     = s.get("color", ""),
                    linewidth = s.get("linewidth"),
                    linestyle = s.get("linestyle", ""),
                    marker    = s.get("marker", ""),
                ),
                data    = copy.deepcopy(uds),
                label   = ds_name,
                visible = any(checked),
                row     = None,
                extra   = {
                    "row_visibility": list(checked),
                    "row_styles":     row_styles,
                },
            )
            artists.append(artist)

        ax_spec = AxesSpec(
            config  = AxesConfig(grid=self._config.get("show_grid", False)),
            artists = artists,
            extra   = {
                "plot_mode":         mode,
                "widget_extras":     widget_extras,
                "has_manual_colors": bool(manual_colors),
            },
        )

        rcparams_delta = {
            k: mpl.rcParams[k]
            for k in mpl.rcParams
            if k in mpl.rcParamsDefault and mpl.rcParams[k] != mpl.rcParamsDefault[k]
        }

        return ScenePlot(
            name           = name,
            figure         = FigureConfig(axes_list=[ax_spec]),
            rcparams_delta = rcparams_delta,
        )

    def restore_scene(self, scene) -> None:
        """Restore full display state from a ScenePlot."""
        import matplotlib as mpl

        self.clear()

        if not scene.figure.axes_list:
            return

        ax_spec = scene.figure.axes_list[0]
        extra   = ax_spec.extra

        # switch mode
        mode = extra.get("plot_mode", "stack")
        idx  = next((i for i in range(self._mode_combo.count())
                     if self._mode_combo.itemData(i) == mode), 0)
        self._mode_combo.blockSignals(True)
        self._mode_combo.setCurrentIndex(idx)
        self._mode_combo.blockSignals(False)
        self._set_mode(mode)

        # restore rcparams before drawing
        if scene.rcparams_delta:
            mpl.rcdefaults()
            try:
                mpl.rcParams.update(scene.rcparams_delta)
            except Exception as exc:
                log.warning("restore_scene: rcparams_delta partially failed: %s", exc)

        # restore per-widget-type extras (applied lazily to widgets not yet created)
        self._widget_extras = extra.get("widget_extras", {})
        for m, w in self._plot_widgets.items():
            self._apply_widget_extra(w, m)

        # rebuild datasets from ArtistSpec list (line artists only)
        for artist in ax_spec.artists:
            if artist.kind != "line" or artist.data is None:
                continue
            ds_name = artist.label or artist.data.name
            self._datasets[ds_name] = prepare_entry(ds_name, artist.data)
            n       = self._datasets[ds_name]["y"].shape[0]
            checked = artist.extra.get("row_visibility", [artist.visible] * n)
            if len(checked) != n:
                checked = [artist.visible] * n
            self._checked[ds_name] = list(checked)

        self._rebuild_tree()
        self._plot_widget.refresh(self._datasets, self._checked)

        # collect per-line manual color pins — applied to the stack widget
        # (now if it exists, or lazily when it is first created)
        self._restored_manual_colors = {}
        for artist in ax_spec.artists:
            if artist.kind != "line" or artist.data is None:
                continue
            ds_name    = artist.label or artist.data.name
            row_styles = artist.extra.get("row_styles", {})
            for row_idx_str, rs in row_styles.items():
                color = rs.get("color", "")
                if color:
                    self._restored_manual_colors[(ds_name, int(row_idx_str))] = color

        stack_w = self._plot_widgets.get("stack")
        if stack_w is not None:
            self._apply_manual_colors(stack_w)

        # artists were rebuilt — panels must drop stale refs and re-pull
        self.view_context.set_plot_widget(self._plot_widget)

    def _apply_widget_extra(self, widget, mode: str) -> None:
        """Apply restored scene extras for one widget type."""
        from .colormap_plot_widget import ColormapPlotWidget
        extra = self._widget_extras.get(mode, {})
        if not extra:
            return
        if hasattr(widget, "set_color_mode"):
            widget.set_color_mode(extra.get("color_mode", "auto"))
        if hasattr(widget, "set_offset"):
            widget.set_offset(extra.get("offset", 0.0))
        if isinstance(widget, ColormapPlotWidget):
            cmb = widget._cmap_combo
            cmb.blockSignals(True)
            cmb.setCurrentText(extra.get("colormap", "RdBu_r"))
            cmb.blockSignals(False)
            widget._sym_check.blockSignals(True)
            widget._sym_check.setChecked(extra.get("symmetric", True))
            widget._sym_check.blockSignals(False)

    def _apply_manual_colors(self, stack_widget) -> None:
        """Push restored per-line color pins into a stack widget."""
        if not self._restored_manual_colors:
            return
        stack_widget._manual_colors = dict(self._restored_manual_colors)
        for key, color in stack_widget._manual_colors.items():
            line = stack_widget._lines.get(key)
            if line is not None:
                line.set_color(color)
        stack_widget._capture_background()

    # ── Selection → ViewerContext ─────────────────────────────────────────

    def _on_tree_selection_changed(self) -> None:
        """Publish tree selection into the ViewerContext (identity only)."""
        selected = self._tree.selectedItems()
        if len(selected) != 1:
            self.view_context.set_selected_key(None)
            return
        data = selected[0].data(0, _ITEM_ROLE)
        if not isinstance(data, tuple) or data[0] != "curve":
            self.view_context.set_selected_key(None)
            return
        _, ds_name, curve_idx = data
        self.view_context.set_selected_key((ds_name, curve_idx))

    def pin_selected_color(self, hex_color: str) -> None:
        """Pin a manual color on the selected curve (called by the module)."""
        key = self.view_context.selected_key
        if key is not None and hasattr(self._plot_widget, "pin_color"):
            self._plot_widget.pin_color(key, hex_color)

    def reset_selected_color(self) -> None:
        """Remove the manual color pin on the selected curve."""
        key = self.view_context.selected_key
        if key is not None and hasattr(self._plot_widget, "reset_color"):
            self._plot_widget.reset_color(key)
            self.view_context.refresh_selection()   # panel re-pulls the new color

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

        for name, entry in self._datasets.items():
            n_curves = entry["y"].shape[0]
            checked  = self._checked.get(name, [True] * n_curves)

            top = QtWidgets.QTreeWidgetItem([name])
            top.setData(0, _ITEM_ROLE, ("dataset", name))
            # No AutoTristate — we update parent check state manually so that
            # a child change does NOT re-emit itemChanged for the parent.
            top.setFlags(top.flags() | _UserCheck)

            for i in range(n_curves):
                child = QtWidgets.QTreeWidgetItem([f"Line {i}"])
                child.setData(0, _ITEM_ROLE, ("curve", name, i))
                child.setFlags(child.flags() | _UserCheck)
                child.setCheckState(0, _Checked if checked[i] else _Unchecked)
                top.addChild(child)

            top.setCheckState(0, self._parent_check_state(checked))
            top.setExpanded(True)
            self._tree.addTopLevelItem(top)
        self._tree.blockSignals(False)

    @staticmethod
    def _parent_check_state(checked: list[bool]):
        _C = QtCore.Qt.CheckState
        if all(checked):
            return _C.Checked
        if any(checked):
            return _C.PartiallyChecked
        return _C.Unchecked

    def _on_tree_item_changed(self, item, _col) -> None:
        if self._bulk_update:
            return
        data = item.data(0, _ITEM_ROLE)
        if data is None:
            return

        _C = QtCore.Qt.CheckState

        if data[0] == "curve":
            # Single curve toggled — O(1) visibility change, no redraw of others.
            _, name, idx = data
            if name not in self._checked:
                return
            visible = (item.checkState(0) == _C.Checked)
            self._checked[name][idx] = visible
            # Update parent visual state without re-firing itemChanged.
            self._bulk_update = True
            try:
                parent = item.parent()
                if parent is not None:
                    self._tree.blockSignals(True)
                    parent.setCheckState(0, self._parent_check_state(self._checked[name]))
                    self._tree.blockSignals(False)
            finally:
                self._bulk_update = False
            self._plot_widget.set_line_visible(name, idx, visible)

        elif data[0] == "dataset":
            # Parent checkbox — propagate to all children, O(n) visibility change.
            _, name = data
            if name not in self._checked:
                return
            visible = (item.checkState(0) != _C.Unchecked)
            self._bulk_update = True
            try:
                self._tree.blockSignals(True)
                for ci in range(item.childCount()):
                    child = item.child(ci)
                    child.setCheckState(0, _C.Checked if visible else _C.Unchecked)
                item.setCheckState(0, _C.Checked if visible else _C.Unchecked)
                self._tree.blockSignals(False)
            finally:
                self._bulk_update = False
            self._plot_widget.set_all_visible(name, visible)

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
