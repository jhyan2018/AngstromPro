# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 2026

@author: jiahaoYan

ImageStackViewer — module for visualizing and processing ndim=3 UDS data
as a stack of 2D images (Main + Auxiliary panels).

Each panel is an Image2Uds3Widget which provides:
  - matplotlib canvas with pan / zoom / pick-points interactions
  - ScaleWidget (range slider + sigma auto-scale)
  - Layer spinbox + axis value readout
  - Data-type selector (Abs / Angle / Real / Imag)
  - Colormap selector + real-time ColorMapEditorWidget

Sync options (View menu):
  - Sync Layer      : Auxiliary follows Main layer
  - Sync Colormap   : not wired here — use individual panel controls

on_item_loaded strategy:
  - Double-click workspace item → loads into Main, stages [item]
  - "Load selected → Aux" button → loads into Auxiliary, stages [main, aux]
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.utils.qt_compat import QtCore, QtWidgets

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

log = logging.getLogger(__name__)


@register_module
class ImageStackViewer(AGuiModule):
    module_id     = "image_stack_viewer"
    display_name  = "Image Stack Viewer"
    category      = "Imaging"
    accepted_ndim = 3

    _sync_layer: bool = False

    def __init__(self, context: "AppContext", parent=None) -> None:
        super().__init__(context, parent)
        self._main_item: WorkspaceItem | None = None
        self._aux_item:  WorkspaceItem | None = None
        self.resize(1200, 650)
        self.setWindowTitle(f"Image Stack Viewer — {self.instance_id}")

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        from angstrompro.gui.widgets.image_stack_viewer_widget import ImageStackViewerWidget
        from angstrompro.gui.resources.colormaps import register_all
        register_all()

        cmap_list = (
            self._context.config.get_group("modules")
            .get("image2u3", {})
            .get("colormap", {})
            .get("cmap_palette_list", ["gray"])
        )

        self._panel_main = ImageStackViewerWidget()
        self._panel_main.ui_lb_widget_name.setText("<b>— MAIN —</b>")
        self._panel_main.sendMsgSignal.connect(self._on_msg_from_main)
        self._panel_main.setup_palette(cmap_list)

        self._panel_aux = ImageStackViewerWidget()
        self._panel_aux.ui_lb_widget_name.setText("<b>— AUXILIARY —</b>")
        self._panel_aux.sendMsgSignal.connect(self._on_msg_from_aux)
        self._panel_aux.setParamlistEnabled(False)
        self._panel_aux.setup_palette(cmap_list)

        splitter = QtWidgets.QSplitter(
            QtCore.Qt.Orientation.Horizontal
            if hasattr(QtCore.Qt.Orientation, "Horizontal")
            else QtCore.Qt.Horizontal
        )
        splitter.addWidget(self._panel_main)
        splitter.addWidget(self._panel_aux)
        splitter.setSizes([600, 600])

        # toolbar above panels
        aux_bar = QtWidgets.QHBoxLayout()
        self._btn_load_aux = QtWidgets.QPushButton("Load selected → Aux")
        self._btn_load_aux.setToolTip(
            "Load the currently selected workspace item into the Auxiliary panel.")
        self._btn_load_aux.clicked.connect(self._on_load_aux)
        aux_bar.addWidget(self._btn_load_aux)
        aux_bar.addStretch()

        central = QtWidgets.QWidget()
        vlay = QtWidgets.QVBoxLayout(central)
        vlay.setContentsMargins(4, 4, 4, 4)
        vlay.addLayout(aux_bar)
        vlay.addWidget(splitter, stretch=1)
        self.setCentralWidget(central)

        self._add_sync_actions()

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        if not self._check_ndim3(item):
            return
        self._main_item  = item
        self._aux_item   = None
        self.process_inputs = [item]
        self._panel_main.setUdsData(item.payload)
        self._panel_main.setEnabled(True)
        self.statusBar().showMessage(
            f"Main: {item.name}  shape={item.payload.data.shape}", 4000)

    def on_add_item(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Aux loading
    # ------------------------------------------------------------------

    def _on_load_aux(self) -> None:
        name = self._selected_item_name()
        if name is None:
            QtWidgets.QMessageBox.information(
                self, "No selection", "Select a workspace item first.")
            return
        item = self.workspace.get_item(name)
        if not self._check_ndim3(item):
            return
        self._aux_item = item
        self.process_inputs = [self._main_item, item] if self._main_item else [item]
        self._panel_aux.setUdsData(item.payload)
        self._panel_aux.setEnabled(True)
        if self._sync_layer:
            self._panel_aux.setImageLayer(self._panel_main.img_current_layer)
        self.statusBar().showMessage(
            f"Aux: {item.name}  shape={item.payload.data.shape}", 4000)

    # ------------------------------------------------------------------
    # Message routing between panels
    # ------------------------------------------------------------------

    def _on_msg_from_main(self, msg_idx: int) -> None:
        msg = self._panel_main.msg_type[msg_idx]
        if msg == "SYNC_LAYER" and self._sync_layer:
            self._panel_aux.setImageLayer(self._panel_main.img_current_layer)

    def _on_msg_from_aux(self, msg_idx: int) -> None:
        pass

    # ------------------------------------------------------------------
    # Sync actions in View menu
    # ------------------------------------------------------------------

    def _add_sync_actions(self) -> None:
        view_menu = None
        for action in self.menuBar().actions():
            if action.text() == "View":
                view_menu = action.menu()
                break
        if view_menu is None:
            return
        view_menu.addSeparator()
        act = view_menu.addAction("Sync Layer (Main → Aux)")
        act.setCheckable(True)
        act.toggled.connect(lambda v: setattr(self, "_sync_layer", v))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_ndim3(self, item: WorkspaceItem) -> bool:
        data = getattr(item.payload, "data", None)
        if data is None or data.ndim != 3:
            QtWidgets.QMessageBox.warning(
                self, "Wrong ndim",
                f"'{item.name}' is not ndim=3 — cannot display in Image Stack Viewer.")
            return False
        return True
