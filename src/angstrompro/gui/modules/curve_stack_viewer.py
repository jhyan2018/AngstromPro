# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

CurveStackViewer — AGuiModule for visualizing and processing 1D/2D UDS data
as a stack of curves.

Accepted data
-------------
- ndim=1  UdsDataStru : single curve  (n_pts,)
- ndim=2  UdsDataStru : curve stack   (n_curves, n_pts)

Item loading strategy
---------------------
- Double-click workspace item  → clear everything, set as primary, replot
- Right-click → "Add to plot"  → overlay on current figure (bypasses staged list)
- Right-click → "Set as reference" → fills reference slot (for two-input processes)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.widgets.curve_stack.runtime_scene import RuntimeScene
from angstrompro.gui.widgets.preferences import PrefSection, PrefItem
import angstrompro.gui.widgets.preferences.widgets  # registers custom widget types
from angstrompro.utils.qt_compat import QtCore, QtWidgets, Action

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

log = logging.getLogger(__name__)


@register_module
class CurveStackViewer(AGuiModule):
    # Retains its existing specialized geometry and dock-state implementation.
    persist_window_layout = False

    module_id    = "curve_stack_viewer"
    display_name = "Curve Stack Viewer"
    category     = "Basic"

    accepted_types = {"uds", "scene_plot"}
    accepted_ndim  = 2          # accepts 1D and 2D
    staged_labels  = ["P", "R"]

    preferences_schema = [
        PrefSection("Color map", "palette", [
            PrefItem("colormap.cmap_palette_list", "", "colormap_picker", full_width=True),
        ]),
        PrefSection("Templates", "palette", [
            PrefItem("default_template", "Default template", "template_picker",
                     "Scene template applied when this module opens "
                     "(select '(none)' for matplotlib defaults)"),
        ]),
    ]

    def build_ui(self) -> None:
        from angstrompro.gui.widgets.curve_stack import CurveStackViewerWidget

        # ── runtime scene — single source of truth ────────────────────────
        self._scene = RuntimeScene()

        # ── staged slots (hidden from widget) ─────────────────────────────
        self._primary_item:   WorkspaceItem | None = None
        self._reference_item: WorkspaceItem | None = None
        self._displayed_names: set[str] = set()   # tracks all items shown in plot

        # ── viewer widget ─────────────────────────────────────────────────
        self._viewer = CurveStackViewerWidget(config=self._config)
        self._viewer.set_runtime_scene(self._scene)
        self._viewer.extract_requested.connect(self._on_extract_requested)
        self._viewer.cleared.connect(self._on_viewer_cleared)

        # any scene mutation → dirty flag
        bus = self._viewer.scene_bus
        bus.axes_config_changed.connect(self._on_scene_mutated)
        bus.line_style_changed.connect(lambda _key: self._on_scene_mutated())
        bus.artists_changed.connect(self._on_scene_mutated)

        # NOTE: the default template is NOT applied at startup — it is the
        # pre-load template consumed on every fresh UDS load (on_item_loaded)

        self._build_scene_menu()
        self.setCentralWidget(self._viewer)
        self._build_inspector_docks()

        # apply saved config (e.g. colormap palette) immediately on startup
        self._apply_config_to_panels(self._config)

    def _build_inspector_docks(self) -> None:
        """Right-side docks bound to the viewer's ViewerContext (pull model)."""
        from angstrompro.gui.widgets.curve_stack.artist_style_panel import ArtistStylePanel
        from angstrompro.gui.widgets.curve_stack.axes_config_panel import AxesConfigPanel

        ctx = self._viewer.view_context
        _Right = QtCore.Qt.DockWidgetArea.RightDockWidgetArea

        # Curve Style dock
        self._style_panel = ArtistStylePanel()
        self._style_panel.bind_context(ctx)
        self._style_panel.color_pinned.connect(self._viewer.pin_selected_color)
        self._style_panel.color_reset.connect(self._viewer.reset_selected_color)
        self._style_panel.style_changed.connect(self._viewer.pin_selected_style)
        self._style_dock = QtWidgets.QDockWidget("Curve Style", self)
        self._style_dock.setObjectName("curve_style_dock")
        self._style_dock.setWidget(self._style_panel)
        self.addDockWidget(_Right, self._style_dock)

        # Axes dock — edits go to the RuntimeScene via the viewer
        self._axes_panel = AxesConfigPanel()
        self._axes_panel.bind_context(ctx)
        self._axes_panel.set_scene_config_provider(self._viewer._current_mode_cfg)
        self._axes_panel.config_changed.connect(self._viewer.update_axes_config)
        self._axes_dock = QtWidgets.QDockWidget("Axes", self)
        self._axes_dock.setObjectName("axes_config_dock")
        self._axes_dock.setWidget(self._axes_panel)
        self.addDockWidget(_Right, self._axes_dock)

        # stack them as tabs; hidden by default — View menu can re-show
        self.tabifyDockWidget(self._style_dock, self._axes_dock)
        self._style_dock.hide()
        self._axes_dock.hide()

        # View-menu toggles
        vm = getattr(self, "_view_menu", None) or self._find_view_menu()
        if vm is not None:
            vm.addSeparator()
            vm.addAction(self._style_dock.toggleViewAction())
            vm.addAction(self._axes_dock.toggleViewAction())

    def _on_scene_mutated(self) -> None:
        """Any scene mutation (via SceneBus) marks the scene dirty."""
        self._scene.mark_dirty()
        self._update_title()

    def _find_view_menu(self):
        for act in self.menuBar().actions():
            if act.text().replace("&", "") == "View":
                return act.menu()
        return None

    # ── Window / dock layout persistence ─────────────────────────────────

    def _layout_qs_prefix(self) -> str:
        return f"module/{self.module_id}"

    def _restore_layout(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        geom  = qs.value(f"{self._layout_qs_prefix()}/geometry")
        state = qs.value(f"{self._layout_qs_prefix()}/layout")
        if geom:
            self.restoreGeometry(geom)
        if state:
            self.restoreState(state)

    def _save_layout(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings
        qs = get_qsettings()
        qs.setValue(f"{self._layout_qs_prefix()}/geometry", self.saveGeometry())
        qs.setValue(f"{self._layout_qs_prefix()}/layout",   self.saveState())
        qs.sync()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not getattr(self, "_layout_restored", False):
            self._layout_restored = True
            QtCore.QTimer.singleShot(0, self._restore_layout)

    def closeEvent(self, event) -> None:
        self._save_layout()
        super().closeEvent(event)   # AGuiModule hides instead of destroying

    def save_state_for_exit(self) -> None:
        self._save_layout()
        super().save_state_for_exit()

    # ── Slot hooks ────────────────────────────────────────────────────────

    def _clear_slot(self, idx: int) -> None:
        if idx == 1:
            self._clear_reference()

    # ── Display color hook ────────────────────────────────────────────────

    def _get_display_color(self, item_name: str) -> str | None:
        if item_name in self._displayed_names:
            return "#2196F3"   # blue — shown in plot
        return None

    # ── Item loading ──────────────────────────────────────────────────────

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        """Double-click: if uds, clear and reload as primary; if scene, restore display."""
        if item.type_id == "scene_plot":
            self._restore_scene(item)
            return
        if not self._validate_uds(item):
            return
        self._primary_item = item
        self._displayed_names.clear()
        self._displayed_names.add(item.name)
        self._sync_process_inputs()
        self._scene.clear()
        self._viewer.clear()
        # fresh UDS load: style comes from the pre-load template (if any)
        self._viewer.apply_preload_template(
            self._config.get("default_template", ""))
        self._viewer.add_dataset(item.name, item.payload)
        self._scene.mark_dirty()
        self._update_title()
        self._refresh_workspace_panel()
        self._refresh_slots_panel()

    def _restore_scene(self, item: WorkspaceItem) -> None:
        if self._scene.dirty:
            ans = QtWidgets.QMessageBox.question(
                self, "Unsaved changes",
                "The current scene has unsaved changes.\n"
                "Load new scene and discard changes?",
                QtWidgets.QMessageBox.StandardButton.Discard |
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            if ans != QtWidgets.QMessageBox.StandardButton.Discard:
                return
        self._primary_item = None
        self._clear_reference()
        self._displayed_names.clear()
        self._displayed_names.add(item.name)
        # deep-copy: the runtime scene is mutated by every edit — it must
        # never alias the workspace payload, or edits corrupt the saved item
        import copy
        self._scene.replace(copy.deepcopy(item.payload))
        self._viewer.restore_scene(self._scene.scene)
        self._update_title()
        self._refresh_workspace_panel()

    def _on_extract_requested(self, pairs: list) -> None:
        from angstrompro.gui.dialogs.extract_curves_dialog import ExtractCurvesDialog
        dlg = ExtractCurvesDialog(pairs, parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        for name, uds in dlg.result_pairs():
            uds.name = name
            self.workspace.add_item(payload=uds)

    def _on_save_scene(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save as Scene", "Scene name:",
            text=self._primary_item.name if self._primary_item else "scene")
        if not ok or not name.strip():
            return
        name = name.strip()
        # save_scene syncs the RuntimeScene in place and returns an
        # independent snapshot — the runtime scene must NOT be re-pointed
        # at the payload, or later edits would mutate the saved item
        scene = self._viewer.save_scene(name)
        self._scene.mark_clean()
        self._update_title()
        self.workspace.add_item(payload=scene)

    def _add_to_plot(self, item: WorkspaceItem) -> None:
        """Overlay item on current figure without touching staged list."""
        if not self._validate_uds(item):
            return
        self._displayed_names.add(item.name)
        self._viewer.add_dataset(item.name, item.payload)
        self._scene.mark_dirty()
        self._update_title()
        self._refresh_workspace_panel()

    def _set_reference(self, item: WorkspaceItem) -> None:
        self._reference_item = item
        self._sync_process_inputs()
        self._refresh_workspace_panel()
        self._refresh_slots_panel()

    def _clear_reference(self) -> None:
        self._reference_item = None
        self._sync_process_inputs()
        self._refresh_workspace_panel()
        self._refresh_slots_panel()

    def _sync_process_inputs(self) -> None:
        inputs = []
        if self._primary_item is not None:
            inputs.append(self._primary_item)
        if self._reference_item is not None:
            inputs.append(self._reference_item)
        self.process_inputs = inputs

    # ── Context menu hook ─────────────────────────────────────────────────

    def _populate_ws_item_context_menu(
            self, menu: QtWidgets.QMenu, item: WorkspaceItem) -> None:
        if item.type_id == "uds":
            act_add = menu.addAction("Add to plot")
            act_ref = menu.addAction("Set as Reference")
            act_add.triggered.connect(lambda: self._add_to_plot(item))
            act_ref.triggered.connect(lambda: self._set_reference(item))
            if self._reference_item is not None and self._reference_item.name == item.name:
                act_clr = menu.addAction("Clear Reference")
                act_clr.triggered.connect(self._clear_reference)

    # ── Scene menu ────────────────────────────────────────────────────────

    def _build_scene_menu(self) -> None:
        menu = self.menuBar().addMenu("Scene")

        act_save = Action("Save as Scene…", self)
        act_save.setShortcut("Ctrl+Shift+S")
        act_save.setToolTip("Capture current figure as a WorkspaceItem (data + style)")
        act_save.triggered.connect(self._on_save_scene)
        menu.addAction(act_save)

        menu.addSeparator()

        self._tpl_load_menu = menu.addMenu("Load Template")
        self._tpl_load_menu.aboutToShow.connect(self._refresh_template_menu)

        act_save_tpl = Action("Save Template…", self)
        act_save_tpl.setToolTip("Save current plot style as a reusable template")
        act_save_tpl.triggered.connect(self._on_save_template)
        menu.addAction(act_save_tpl)

        menu.addSeparator()

        act_style = Action("Plot Style…", self)
        act_style.setToolTip("Edit matplotlib rcParams (font, ticks, line defaults, …)")
        act_style.triggered.connect(self._on_plot_style)
        menu.addAction(act_style)

    def _refresh_template_menu(self) -> None:
        from angstrompro.gui.widgets.curve_stack import template_manager as tmgr
        self._tpl_load_menu.clear()
        names = tmgr.list_templates()
        if not names:
            act = self._tpl_load_menu.addAction("(no templates saved)")
            act.setEnabled(False)
            return
        for name in names:
            act = self._tpl_load_menu.addAction(name)
            act.triggered.connect(
                lambda _checked, n=name: self._viewer.apply_template_by_name(n))

    def _on_save_template(self) -> None:
        self._viewer._on_save_template()

    def _on_plot_style(self) -> None:
        from angstrompro.gui.widgets.curve_stack.rcparams_style_panel import RcParamsStylePanel
        if not hasattr(self, "_style_dlg") or self._style_dlg is None:
            self._style_dlg = RcParamsStylePanel(
                delta_provider=lambda: self._scene.scene.rcparams_delta,
                parent=self)
            self._style_dlg.delta_changed.connect(self._on_style_delta_changed)
            self._style_dlg.finished.connect(lambda _: setattr(self, "_style_dlg", None))
        self._style_dlg.show()
        self._style_dlg.raise_()
        self._style_dlg.activateWindow()

    def _on_style_delta_changed(self, delta: dict) -> None:
        """Dialog produced a new delta — write to scene and rebuild."""
        self._viewer.set_rcparams_delta(delta)
        self._scene.mark_dirty()
        self._update_title()

    # ── File menu ─────────────────────────────────────────────────────────

    def _build_file_menu(self) -> None:
        super()._build_file_menu()
        file_menu = None
        for action in self.menuBar().actions():
            if action.text() == "File":
                file_menu = action.menu()
                break
        if file_menu is None:
            return
        prefs_action = next(
            (a for a in file_menu.actions() if a.text() == "Preferences…"), None)

        export_act = Action("Export Figure…", self)
        export_act.setShortcut("Ctrl+E")
        export_act.triggered.connect(self._on_export_figure)

        if prefs_action is not None:
            sep = file_menu.insertSeparator(prefs_action)
            file_menu.insertAction(sep, export_act)
        else:
            file_menu.addSeparator()
            file_menu.addAction(export_act)

    def _on_export_figure(self) -> None:
        from angstrompro.gui.dialogs.export_figure_dialog import ExportFigureDialog

        plot_widget = self._viewer._plot_widget
        if plot_widget is None or not hasattr(plot_widget, "_fig"):
            QtWidgets.QMessageBox.information(
                self, "Nothing to export", "No figure is currently displayed.")
            return

        dlg = ExportFigureDialog.run(self)
        if dlg is None:
            return

        fig = plot_widget._fig

        if dlg.to_clipboard:
            self._export_figure_to_clipboard(fig)
            return

        _EXT = {"PNG": "png", "PDF": "pdf", "SVG": "svg", "TIFF": "tif"}
        ext  = _EXT.get(dlg.file_format, "png")
        filters = (
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;TIFF (*.tiff *.tif)"
        )
        from pathlib import Path
        default_name = (self._primary_item.name if self._primary_item else "figure") + f".{ext}"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Figure",
            str(Path.home() / default_name),
            filters,
        )
        if not path:
            return

        kwargs: dict = {"bbox_inches": "tight" if dlg.tight else None}
        if dlg.file_format not in ("PDF", "SVG"):
            kwargs["dpi"] = dlg.dpi
        if dlg.transparent:
            kwargs["transparent"] = True

        try:
            fig.savefig(path, **kwargs)
            self.statusBar().showMessage(f"Figure saved to {path}", 4000)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(exc))

    def _export_figure_to_clipboard(self, fig) -> None:
        import io
        from angstrompro.utils.qt_compat import QtGui
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(buf.read(), "PNG")
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
        self.statusBar().showMessage("Figure copied to clipboard.", 3000)

    # ── Config ────────────────────────────────────────────────────────────

    def _on_viewer_cleared(self) -> None:
        self._primary_item = None
        self._reference_item = None
        self._displayed_names.clear()
        self._scene.clear()
        self._update_title()
        self._sync_process_inputs()
        self._refresh_workspace_panel()
        self._refresh_slots_panel()

    def _apply_config_to_panels(self, cfg: dict) -> None:
        self._viewer.apply_config(cfg)
        cmap_list = cfg.get("colormap", {}).get("cmap_palette_list", [])
        if cmap_list:
            self._viewer.set_cmap_palette(cmap_list)

    # ── Title / dirty indicator ───────────────────────────────────────────

    def _update_title(self) -> None:
        scene_name = self._scene.scene.name or ""
        if self._scene.dirty:
            marker = "● "    # filled dot = unsaved changes
            tip    = "Unsaved changes — use Scene → Save as Scene… to save"
        else:
            marker = ""
            tip    = ""
        label = f"{marker}{scene_name}" if scene_name else (marker.strip() or "")
        self.statusBar().showMessage(label, 0)   # 0 = permanent until next update
        self.statusBar().setToolTip(tip)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _validate_uds(self, item: WorkspaceItem) -> bool:
        ndim = getattr(getattr(item.payload, "data", None), "ndim", None)
        if ndim not in (1, 2):
            log.warning(
                "CurveStackViewer: %r has %sD data — only 1D and 2D supported",
                item.name, ndim,
            )
            return False
        return True
