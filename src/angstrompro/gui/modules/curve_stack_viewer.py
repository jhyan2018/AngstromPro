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
from angstrompro.utils.qt_compat import QtWidgets

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

log = logging.getLogger(__name__)


@register_module
class CurveStackViewer(AGuiModule):
    module_id    = "curve_stack_viewer"
    display_name = "Curve Stack Viewer"
    category     = "Basic"

    accepted_types = {"uds", "scene"}
    accepted_ndim  = None          # accepts 1D and 2D
    staged_labels  = ["Primary", "Reference"]

    preferences_schema = [
        PrefSection("Display", "chart-line", [
            PrefItem("line_width", "Line width", "number",
                     "Matplotlib line width for all curves",
                     kwargs={"min": 0.1, "max": 10.0, "step": 0.5}),
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

        # ── reference panel ───────────────────────────────────────────────
        ref_bar = self._build_reference_bar()

        # ── viewer widget ─────────────────────────────────────────────────
        self._viewer = CurveStackViewerWidget(config=self._config)
        self._viewer.extract_requested.connect(self._on_extract_requested)

        default_tpl = self._config.get("default_template", "")
        if default_tpl:
            self._viewer.apply_template_by_name(default_tpl)

        container = QtWidgets.QWidget()
        vl = QtWidgets.QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)
        vl.addWidget(ref_bar)
        vl.addWidget(self._viewer)
        self.setCentralWidget(container)

        # ── toolbar action ────────────────────────────────────────────────
        tb = self.addToolBar("Scene")
        act_save_scene = tb.addAction("Save as Scene…")
        act_save_scene.setToolTip("Save current figure as a scene WorkspaceItem")
        act_save_scene.triggered.connect(self._on_save_scene)

    def _build_reference_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(30)
        hl  = QtWidgets.QHBoxLayout(bar)
        hl.setContentsMargins(6, 2, 6, 2)
        hl.setSpacing(6)

        hl.addWidget(QtWidgets.QLabel("Reference:"))

        self._ref_label = QtWidgets.QLabel("—")
        self._ref_label.setStyleSheet("color: gray; font-style: italic;")
        hl.addWidget(self._ref_label)

        self._ref_clear_btn = QtWidgets.QPushButton("✕")
        self._ref_clear_btn.setFixedWidth(24)
        self._ref_clear_btn.setToolTip("Clear reference item")
        self._ref_clear_btn.setEnabled(False)
        self._ref_clear_btn.clicked.connect(self._clear_reference)
        hl.addWidget(self._ref_clear_btn)

        hl.addStretch()
        return bar

    # ── Item loading ──────────────────────────────────────────────────────

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        """Double-click: clear everything, set as primary, replot."""
        if item.type_id == "scene":
            self._restore_scene(item)
            return
        if not self._validate_uds(item):
            return
        self._primary_item = item
        self._sync_process_inputs()
        self._viewer.clear()
        self._viewer.add_dataset(item.name, item.payload)

    def _restore_scene(self, item: WorkspaceItem) -> None:
        self._primary_item = None
        self._clear_reference()
        self._viewer.restore_scene(item.payload)

    def _on_extract_requested(self, pairs: list) -> None:
        """Receive (suggested_name, UdsDataStru) pairs from widget and add to workspace."""
        from angstrompro.gui.dialogs.extract_curves_dialog import ExtractCurvesDialog
        dlg = ExtractCurvesDialog(pairs, parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        for name, uds in dlg.result_pairs():
            ws_name = self.workspace.suggest_name(name)
            self.workspace.add_item(name=ws_name, payload=uds)

    def _on_save_scene(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save as Scene", "Scene name:",
            text=self._primary_item.name if self._primary_item else "scene")
        if not ok or not name.strip():
            return
        name = name.strip()
        scene = self._viewer.save_scene(name)
        ws_name = self.workspace.suggest_name(name)
        self.workspace.add_item(name=ws_name, payload=scene)

    def _add_to_plot(self, item: WorkspaceItem) -> None:
        """Overlay item on current figure without touching staged list."""
        if not self._validate_uds(item):
            return
        self._viewer.add_dataset(item.name, item.payload)

    def _set_reference(self, item: WorkspaceItem) -> None:
        self._reference_item = item
        self._ref_label.setText(item.name)
        self._ref_label.setStyleSheet("")
        self._ref_clear_btn.setEnabled(True)
        self._sync_process_inputs()

    def _clear_reference(self) -> None:
        self._reference_item = None
        self._ref_label.setText("—")
        self._ref_label.setStyleSheet("color: gray; font-style: italic;")
        self._ref_clear_btn.setEnabled(False)
        self._sync_process_inputs()

    def _sync_process_inputs(self) -> None:
        """Keep process_inputs aligned with primary + reference slots."""
        inputs = []
        if self._primary_item is not None:
            inputs.append(self._primary_item)
        if self._reference_item is not None:
            inputs.append(self._reference_item)
        self.process_inputs = inputs

    # ── Context menu hook ─────────────────────────────────────────────────

    def _populate_ws_item_context_menu(
            self, menu: QtWidgets.QMenu, item: WorkspaceItem) -> None:
        if item.type_id not in self.accepted_types:
            return
        act_add = menu.addAction("Add to plot")
        act_ref = menu.addAction("Set as reference")
        act_add.triggered.connect(lambda: self._add_to_plot(item))
        act_ref.triggered.connect(lambda: self._set_reference(item))

    # ── Config ────────────────────────────────────────────────────────────

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
