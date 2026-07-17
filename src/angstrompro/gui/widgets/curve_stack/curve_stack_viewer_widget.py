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
        self._runtime_scene = None                    # set via set_runtime_scene()
        self._current_mode: str = "stack"             # active plot mode
        self._bulk_update: bool = False               # suppress per-child refreshes
        self.view_context = ViewerContext(self)       # identity of active view objects
        from .scene_bus import SceneBus
        self.scene_bus = SceneBus(self)               # scene-mutation notifications
        self._setup_ui()
        self._set_mode("stack")

    # ── RuntimeScene (single source of truth) ─────────────────────────────

    def set_runtime_scene(self, runtime_scene) -> None:
        """Attach the module-owned RuntimeScene. Must be called once at build."""
        self._runtime_scene = runtime_scene

    def _active_axes(self):
        """Active AxesSpec of the scene — created on demand."""
        from angstrompro.core.data.scene_plot import AxesSpec
        if self._runtime_scene is None:
            return None
        axes = self._runtime_scene.active_axes
        if axes is None:
            axes = AxesSpec()
            self._runtime_scene.scene.figure.axes_list.append(axes)
        return axes

    def _artist_spec(self, ds_name: str, uds=None):
        """Find-or-create the ArtistSpec for a dataset (keyed by label)."""
        from angstrompro.core.data.scene_plot import ArtistSpec, LineStyle
        axes = self._active_axes()
        if axes is None:
            return None
        for spec in axes.artists:
            if spec.label == ds_name:
                return spec
        spec = ArtistSpec(kind="line", style=LineStyle(),
                          data=uds, label=ds_name)
        axes.artists.append(spec)
        return spec

    # ── Y-axis assignment (twin axes) ─────────────────────────────────────

    def _ds_yaxis(self, ds_name: str) -> str:
        """Return 'left' or 'right' Y-axis assignment for a dataset."""
        axes = self._active_axes()
        if axes is None:
            return "left"
        for spec in axes.artists:
            if spec.label == ds_name:
                return spec.extra.get("y_axis", "left")
        return "left"

    def _get_y_axis_assignments(self) -> dict[str, str]:
        """Provider: {ds_name: 'left'|'right'} for all current artists."""
        axes = self._active_axes()
        if axes is None:
            return {}
        return {spec.label: spec.extra.get("y_axis", "left")
                for spec in axes.artists}

    def set_dataset_yaxis(self, ds_name: str, side: str) -> None:
        """Assign dataset to left or right Y axis and trigger a rebuild."""
        spec = self._artist_spec(ds_name)
        if spec is None:
            return
        spec.extra["y_axis"] = side
        self._rebuild_tree()
        if self._plot_widget is not None:
            self._plot_widget.refresh(self._datasets, self._checked)
        self.scene_bus.artists_changed.emit()

    def _axes_config_key(self) -> str:
        """Config-dict slot for the currently active axis.

        'stack_right' when viewing the right twin axis; otherwise the
        widget mode name ('stack', 'colormap', …).
        """
        if (self._current_mode == "stack"
                and self.view_context.y_side == "right"):
            return "stack_right"
        return self._current_mode

    # ── Tree context menu ─────────────────────────────────────────────────

    def _on_tree_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return
        data = item.data(0, _ITEM_ROLE)
        if data is None or data[0] != "dataset":
            return
        _, ds_name = data
        current_side = self._ds_yaxis(ds_name)

        menu = QtWidgets.QMenu(self)
        if current_side != "right":
            act = menu.addAction("Move to Right Y axis")
            act.triggered.connect(lambda: self.set_dataset_yaxis(ds_name, "right"))
        if current_side != "left":
            act = menu.addAction("Move to Left Y axis")
            act.triggered.connect(lambda: self.set_dataset_yaxis(ds_name, "left"))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # scene providers pulled by the plot widgets (see BasePlotWidget)

    def _get_axes_config(self, mode: str):
        """Return an AxesConfig for the given mode, built from the per-mode dict."""
        from angstrompro.core.data.scene_plot import AxesConfig
        axes = self._runtime_scene.active_axes if self._runtime_scene else None
        if axes is None:
            return AxesConfig()
        d = axes.extra.get("axes_config_by_mode", {}).get(mode, {})
        if not d:
            return AxesConfig()   # all defaults → autoscale / dataset labels apply
        def _lim(v): return tuple(v) if v else None
        return AxesConfig(
            title      = d.get("title", ""),
            xlabel     = d.get("xlabel", ""),
            ylabel     = d.get("ylabel", ""),
            xlim       = _lim(d.get("xlim")),
            ylim       = _lim(d.get("ylim")),
            xscale     = d.get("xscale", "linear"),
            yscale     = d.get("yscale", "linear"),
            grid       = d.get("grid"),        # None = untouched → delta rules
            grid_which = d.get("grid_which", "major"),
            legend     = d.get("legend", False),
            legend_loc = d.get("legend_loc", "best"),
            aspect     = d.get("aspect", "auto"),
        )

    def _get_rcparams_delta(self) -> dict:
        """Provider: the scene's live rcparams_delta (single source of truth)."""
        if self._runtime_scene is None:
            return {}
        return self._runtime_scene.scene.rcparams_delta

    def set_rcparams_delta(self, delta: dict) -> None:
        """Replace the scene's delta wholesale and rebuild the active plot."""
        if self._runtime_scene is None:
            return
        self._runtime_scene.scene.rcparams_delta = tmgr.sanitize_delta(delta)
        if self._plot_widget is not None:
            self._plot_widget.refresh(self._datasets, self._checked)

    def _get_row_styles(self) -> dict:
        """{(ds_name, row): props} across all artists of the active axes."""
        axes = self._runtime_scene.active_axes if self._runtime_scene else None
        if axes is None:
            return {}
        out: dict[tuple, dict] = {}
        for spec in axes.artists:
            ds = spec.label or (spec.data.name if spec.data is not None else "")
            for k, props in (spec.extra.get("row_styles") or {}).items():
                out[(ds, int(k))] = props
        return out

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
        self._tree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_tree_context_menu)
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

    def _load_template(self, name: str) -> bool:
        """Load a template: REPLACE the scene delta and ALL modes' extras.

        The active plot mode is never changed.  Returns True on success.
        """
        try:
            rcparams_delta, widget_extras = tmgr.load_template(name)
        except Exception as exc:
            log.warning("Failed to load template %r: %s", name, exc)
            return False

        if self._runtime_scene is not None:
            self._runtime_scene.scene.rcparams_delta = dict(rcparams_delta)

        # replace extras for every mode; cached widgets pick theirs up now,
        # not-yet-created widgets pick theirs up lazily in _set_mode
        self._widget_extras = {m: dict(e) for m, e in widget_extras.items()}
        for m, w in self._plot_widgets.items():
            self._apply_widget_extra(w, m)

        if self._plot_widget is not None:
            self._plot_widget.refresh(self._datasets, self._checked)
        return True

    def apply_template_by_name(self, name: str) -> None:
        """Manual template load (Scene menu)."""
        if name:
            self._load_template(name)

    def apply_preload_template(self, name: str) -> None:
        """Pre-load template for fresh UDS loads.

        Called by the module right after the scene reset on a UDS
        double-click.  Missing/broken templates are logged, not fatal —
        the scene simply keeps matplotlib defaults.
        """
        if not name:
            return
        if not self._load_template(name):
            log.warning(
                "Pre-load template %r is configured but could not be "
                "loaded — using matplotlib defaults", name)

    def _harvest_widget_extras(self) -> dict[str, dict]:
        """Toolbar state of ALL cached widgets (hidden modes included)."""
        extras: dict[str, dict] = {}
        stack_w = self._plot_widgets.get("stack")
        cmap_w  = self._plot_widgets.get("colormap")
        if stack_w is not None:
            extras["stack"] = {
                "color_mode":  stack_w.color_mode,
                "offset":      stack_w.get_offset(),
                "use_rt_cmap": stack_w.use_rt_cmap(),
                "rt_anchors":  stack_w.rt_anchors(),
            }
        if cmap_w is not None:
            extras["colormap"] = {
                "colormap":    cmap_w._cmap_combo.currentText(),
                "symmetric":   cmap_w._sym_check.isChecked(),
                "use_rt_cmap": cmap_w.use_rt_cmap(),
                "rt_anchors":  cmap_w.rt_anchors(),
            }
        # modes never activated: keep extras restored from a scene/template
        for m, e in self._widget_extras.items():
            extras.setdefault(m, dict(e))
        return extras

    def _on_save_template(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Template", "Template name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        if name in tmgr.list_templates():
            ans = QtWidgets.QMessageBox.question(
                self, "Override template?",
                f"Template '{name}' already exists.\n\nOverride?",
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if ans != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        try:
            tmgr.save_template(name,
                               self._get_rcparams_delta(),
                               self._harvest_widget_extras())
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(exc))

    # ── Mode switching ────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        self._current_mode = mode
        widget = self._plot_widgets.get(mode)
        if widget is None:
            widget = self._create_plot_widget(mode)
            widget.apply_config(self._config)
            # scene providers — the widget pulls axes config and per-line
            # pins from the RuntimeScene during every rebuild.
            # axes_config_provider captures mode so each widget reads its
            # own per-mode config dict from the scene.
            widget.axes_config_provider = lambda m=mode: self._get_axes_config(m)
            widget.row_styles_provider  = self._get_row_styles
            widget.rcparams_provider    = self._get_rcparams_delta
            if mode == "stack":
                widget.y_axis_provider           = self._get_y_axis_assignments
                widget.axes_config_provider_right = (
                    lambda: self._get_axes_config("stack_right"))
            if self._cmap_palette and hasattr(widget, "set_cmap_palette"):
                widget.set_cmap_palette(self._cmap_palette)
            # artists_rebuilt is routed through ViewerContext (plot_rebuilt +
            # selection_changed) — no direct connection needed here
            self._plot_widgets[mode] = widget
            self._plot_stack.addWidget(widget)
            # apply extras restored from a scene before this widget existed
            self._apply_widget_extra(widget, mode)

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
        # keep the scene's artist list in sync (single source of truth)
        spec = self._artist_spec(name, uds)
        if spec is not None:
            spec.data = uds
        self._rebuild_tree()
        if is_replace:
            self._plot_widget.remove_lines(name)
        self._plot_widget.add_lines(name, entry, self._checked[name])
        self.scene_bus.artists_changed.emit()

    def remove_dataset(self, name: str) -> None:
        self._datasets.pop(name, None)
        self._checked.pop(name, None)
        axes = self._active_axes()
        if axes is not None:
            axes.artists = [s for s in axes.artists if s.label != name]
        self._rebuild_tree()
        self._plot_widget.remove_lines(name)
        self.scene_bus.artists_changed.emit()

    def clear(self) -> None:
        self._datasets.clear()
        self._checked.clear()
        self._tree.clear()
        self._widget_extras = {}
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
        """Sync UI-held state into the RuntimeScene and return a snapshot.

        Per-line pins, axes config and the rcparams delta already live in the
        scene (written on every edit).  Only widget toolbar state and
        visibility are harvested here.
        """
        rs = self._runtime_scene
        ax_spec = self._active_axes()
        if rs is None or ax_spec is None:
            raise RuntimeError("save_scene: no RuntimeScene attached")

        rs.scene.name = name

        widget_extras = self._harvest_widget_extras()

        row_styles_all = self._get_row_styles()
        ax_spec.extra["plot_mode"]     = self._mode_combo.currentData()
        ax_spec.extra["widget_extras"] = widget_extras
        ax_spec.extra["has_manual_colors"] = any(
            props.get("color") for props in row_styles_all.values())

        # per-artist visibility
        for spec in ax_spec.artists:
            checked = self._checked.get(spec.label, [])
            spec.extra["row_visibility"] = list(checked)
            spec.visible = any(checked) if checked else True

        # rcparams_delta is live state — already exact in the scene

        return rs.snapshot()

    def restore_scene(self, scene) -> None:
        """Restore full display state from a ScenePlot.

        The scene's rcparams_delta needs no handling here: the module has
        already replaced the RuntimeScene, and every rebuild pulls the delta
        via rcparams_provider — global mpl.rcParams is never touched.
        """
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
        # refresh pulls per-line pins and axes config straight from the scene
        self._plot_widget.refresh(self._datasets, self._checked)

        # artists were rebuilt — panels must drop stale refs and re-pull
        self.view_context.set_plot_widget(self._plot_widget)
        self.scene_bus.scene_replaced.emit()

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
        # per-mode RT colormap copy — stack and colormap each restore their own
        if mode == "stack" and hasattr(widget, "set_rt_cmap"):
            widget.set_rt_cmap(extra.get("use_rt_cmap", False),
                               extra.get("rt_anchors"))
        if isinstance(widget, ColormapPlotWidget):
            cmb = widget._cmap_combo
            cmb.blockSignals(True)
            cmb.setCurrentText(extra.get("colormap", "RdBu_r"))
            cmb.blockSignals(False)
            widget._sym_check.blockSignals(True)
            widget._sym_check.setChecked(extra.get("symmetric", True))
            widget._sym_check.blockSignals(False)
            widget.set_rt_cmap(extra.get("use_rt_cmap", False),
                               extra.get("rt_anchors"))

    # ── Selection → ViewerContext ─────────────────────────────────────────

    def _on_tree_selection_changed(self) -> None:
        """Publish tree selection into the ViewerContext (identity only)."""
        selected = self._tree.selectedItems()
        if len(selected) != 1:
            self.view_context.set_selected_key(None)
            self.view_context.set_y_side("left")
            return
        data = selected[0].data(0, _ITEM_ROLE)
        if not isinstance(data, tuple):
            self.view_context.set_selected_key(None)
            self.view_context.set_y_side("left")
            return
        if data[0] == "dataset":
            _, ds_name = data
            self.view_context.set_selected_key(None)
            self.view_context.set_y_side(self._ds_yaxis(ds_name))
        elif data[0] == "curve":
            _, ds_name, curve_idx = data
            self.view_context.set_selected_key((ds_name, curve_idx))
            self.view_context.set_y_side(self._ds_yaxis(ds_name))
        else:
            self.view_context.set_selected_key(None)
            self.view_context.set_y_side("left")

    def pin_selected_color(self, hex_color: str) -> None:
        """Pin a manual color on the selected curve — written to the scene."""
        self._pin_selected("color", hex_color)

    def pin_selected_style(self, prop: str, value) -> None:
        """Pin a manual style prop on the selected curve — written to the scene."""
        self._pin_selected(prop, value)

    def _pin_selected(self, prop: str, value) -> None:
        key = self.view_context.selected_key
        if key is None:
            return
        ds_name, row = key
        spec = self._artist_spec(ds_name)
        if spec is None:
            return
        row_styles = spec.extra.setdefault("row_styles", {})
        # JSON round-trips turn int keys into strings — reuse either form
        entry = row_styles.get(row)
        if entry is None:
            entry = row_styles.pop(str(row), None)
            if entry is None:
                entry = {}
            row_styles[row] = entry
        entry[prop] = value
        # live application already happened in the panel; the scene entry
        # makes it survive rebuilds, mode switches and save/reload
        self.scene_bus.line_style_changed.emit(key)

    def reset_selected_color(self) -> None:
        """Remove the manual color pin on the selected curve."""
        key = self.view_context.selected_key
        if key is None:
            return
        ds_name, row = key
        spec = self._artist_spec(ds_name)
        if spec is not None:
            row_styles = spec.extra.get("row_styles", {})
            for rk in (row, str(row)):   # int at runtime, str after JSON load
                if rk in row_styles:
                    row_styles[rk].pop("color", None)
                    if not row_styles[rk]:
                        row_styles.pop(rk)
        if hasattr(self._plot_widget, "refresh_line_styles"):
            self._plot_widget.refresh_line_styles()
        self.scene_bus.line_style_changed.emit(key)
        self.view_context.refresh_selection()   # panel re-pulls the new color

    # ── Axes config (scene-backed) ────────────────────────────────────────

    def update_axes_config(self, patch: dict) -> None:
        """Write a partial axes config patch into the current axis's scene dict."""
        axes = self._active_axes()
        if axes is None:
            return
        by_mode = axes.extra.setdefault("axes_config_by_mode", {})
        cfg = by_mode.setdefault(self._axes_config_key(), {})
        for k, v in patch.items():
            # store lists (JSON-safe); tuples round-trip as lists through JSON
            if k in ("xlim", "ylim") and v is not None:
                v = list(v)
            cfg[k] = v
        self._apply_axes_patch_live(patch)
        self.scene_bus.axes_config_changed.emit()

    def _current_mode_cfg(self) -> dict:
        """Raw config dict for the current active axis (read-only convenience)."""
        axes = self._active_axes()
        if axes is None:
            return {}
        return axes.extra.get("axes_config_by_mode", {}).get(self._axes_config_key(), {})

    def _apply_axes_patch_live(self, patch: dict) -> None:
        """Apply a patch directly to the live ax (handles clears too)."""
        w = self._plot_widget
        # Right twin axis gets its own config slot; only Y settings apply there
        if self._axes_config_key() == "stack_right":
            ax = getattr(w, "_ax2", None)
        else:
            ax = getattr(w, "_ax", None)
        canvas = getattr(w, "_canvas", None)
        if ax is None:
            return
        cfg = self._current_mode_cfg()
        for k, v in patch.items():
            if k == "title":
                ax.set_title(v)
            elif k == "xlabel":
                ax.set_xlabel(v)
            elif k == "ylabel":
                ax.set_ylabel(v)
            elif k == "xlim":
                ax.set_xlim(tuple(v)) if v else ax.autoscale(axis="x")
            elif k == "ylim":
                ax.set_ylim(tuple(v)) if v else ax.autoscale(axis="y")
            elif k == "xscale":
                ax.set_xscale(v)
            elif k == "yscale":
                ax.set_yscale(v)
            elif k in ("grid", "grid_which"):
                ax.grid(False, which="both")   # clear all first
                if cfg.get("grid"):
                    ax.grid(True, which=cfg.get("grid_which") or "major",
                            linestyle="--", alpha=0.4)
            elif k in ("legend", "legend_loc"):
                if cfg.get("legend"):
                    try:
                        ax.legend(loc=cfg.get("legend_loc") or "best")
                    except Exception:
                        pass
                else:
                    leg = ax.get_legend()
                    if leg is not None:
                        leg.remove()
            elif k == "aspect":
                ax.set_aspect(v or "auto")
        # margins were computed before this text existed — a new/changed
        # title or label needs a re-layout or it clips at the figure edge
        if patch.keys() & {"title", "xlabel", "ylabel"}:
            fig = getattr(w, "_fig", None)
            if fig is not None:
                try:
                    fig.tight_layout()
                except Exception:
                    pass
                ax2 = getattr(w, "_ax2", None)
                main_ax = getattr(w, "_ax", None)
                if ax2 is not None and main_ax is not None:
                    ax2.set_position(main_ax.get_position())
        if canvas is not None:
            canvas.draw_idle()

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
            label    = f"{name} [R]" if self._ds_yaxis(name) == "right" else name

            top = QtWidgets.QTreeWidgetItem([label])
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
