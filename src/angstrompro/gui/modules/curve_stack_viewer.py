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
from angstrompro.gui.widgets.preferences import PrefSection, PrefItem
import angstrompro.gui.widgets.preferences.widgets  # registers custom widget types
from angstrompro.utils.qt_compat import QtWidgets, Action

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

log = logging.getLogger(__name__)


@register_module
class CurveStackViewer(AGuiModule):
    module_id    = "curve_stack_viewer"
    display_name = "Curve Stack Viewer"
    category     = "Basic"

    accepted_types = {"uds", "scene"}
    accepted_ndim  = 2          # accepts 1D and 2D
    staged_labels  = ["P", "R"]

    preferences_schema = [
        PrefSection("Display", "chart-line", [
            PrefItem("line_width", "Line width", "number",
                     "Matplotlib line width for all curves",
                     kwargs={"min": 0.1, "max": 10.0}),
            PrefItem("show_grid", "Show grid", "checkbox",
                     "Draw a dashed grid on the plot"),
        ]),
        PrefSection("Templates", "palette", [
            PrefItem("default_template", "Default template", "text",
                     "Name of the scene template to apply when this module opens "
                     "(leave blank for matplotlib defaults)"),
        ]),
    ]

    def build_ui(self) -> None:
        from angstrompro.gui.widgets.curve_stack import CurveStackViewerWidget

        # ── staged slots (hidden from widget) ─────────────────────────────
        self._primary_item:   WorkspaceItem | None = None
        self._reference_item: WorkspaceItem | None = None
        self._displayed_names: set[str] = set()   # tracks all items shown in plot

        # ── viewer widget ─────────────────────────────────────────────────
        self._viewer = CurveStackViewerWidget(config=self._config)
        self._viewer.extract_requested.connect(self._on_extract_requested)
        self._viewer.cleared.connect(self._on_viewer_cleared)

        default_tpl = self._config.get("default_template", "")
        if default_tpl:
            self._viewer.apply_template_by_name(default_tpl)

        self._build_scene_menu()
        self.setCentralWidget(self._viewer)

        # suppress mpl toolbar save buttons (export handled via File menu)
        self._remove_mpl_save_actions()

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
        """Double-click: if uds, clear and reload as Input; if scene, restore display."""
        if item.type_id == "scene":
            self._restore_scene(item)
            return
        if not self._validate_uds(item):
            return
        self._primary_item = item
        self._displayed_names.clear()
        self._displayed_names.add(item.name)
        self._sync_process_inputs()
        self._viewer.clear()
        self._viewer.add_dataset(item.name, item.payload)
        self._refresh_workspace_panel()
        self._refresh_slots_panel()

    def _restore_scene(self, item: WorkspaceItem) -> None:
        self._primary_item = None
        self._clear_reference()
        self._displayed_names.clear()
        self._displayed_names.add(item.name)
        self._viewer.restore_scene(item.payload)
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
        scene = self._viewer.save_scene(name)
        self.workspace.add_item(payload=scene)

    def _add_to_plot(self, item: WorkspaceItem) -> None:
        """Overlay item on current figure without touching staged list."""
        if not self._validate_uds(item):
            return
        self._displayed_names.add(item.name)
        self._viewer.add_dataset(item.name, item.payload)
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

    def _remove_mpl_save_actions(self) -> None:
        """Remove the save button from every mpl NavigationToolbar in the viewer."""
        from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
        for navbar in self._viewer.findChildren(NavigationToolbar2QT):
            for action in navbar.actions():
                if "save" in action.text().lower() or "save" in action.toolTip().lower():
                    navbar.removeAction(action)

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
        self._sync_process_inputs()
        self._refresh_workspace_panel()
        self._refresh_slots_panel()

    def _apply_config_to_panels(self, cfg: dict) -> None:
        self._viewer.apply_config(cfg)

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
