# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 2026

@author: jiahaoYan

ImageStackViewer — module for visualizing and processing ndim=3 UDS data
as a stack of 2D images (Main + Auxiliary panels).

Each panel is an ImageStackViewerWidget which provides:
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
from angstrompro.gui.widgets.preferences import PrefSection, PrefItem
import angstrompro.gui.widgets.preferences.widgets  # registers custom widget types

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

log = logging.getLogger(__name__)


@register_module
class ImageStackViewer(AGuiModule):
    module_id     = "image_stack_viewer"
    display_name  = "Image Stack Viewer"
    category      = "Basic"
    accepted_types = ['uds']
    accepted_ndim = 3

    _sync_layer: bool = False
    staged_labels = ["M", "A"]

    preferences_schema = [
        PrefSection("Color map", "palette", [
            PrefItem("colormap.cmap_palette_list", "", "colormap_picker", full_width=True),
        ]),
        PrefSection("Sync", "arrows-exchange", [
            PrefItem("sync.layer",            "Sync layer",       "checkbox", "Auxiliary follows main layer"),
            PrefItem("sync.picked_points",    "Sync pick points", "checkbox", "Mirror pick-point coordinates"),
            PrefItem("sync.real_time_cursor", "Sync cursor",      "checkbox", "Show cursor position on both panels"),
            PrefItem("sync.canvas_view_zoom", "Sync FOV zoom",    "checkbox", "Pan and zoom together"),
        ]),
        PrefSection("Scale", "adjustments-horizontal", [
            PrefItem("factor.sigma",                    "Sigma",              "number", "σ window for histogram auto-scale"),
            PrefItem("factor.fft_auto_scale_factor",    "FFT auto scale",     "number", "Upper fraction of FFT max kept"),
            PrefItem("factor.slider_scale_zoom_factor", "Slider zoom factor", "number", "Step size for zoom in/out buttons"),
        ]),
        PrefSection("Canvas", "layout-kanban", [
            PrefItem("canvas.canvas_size_factor", "Size factor", "number", "Relative canvas size within the panel"),
            PrefItem("canvas.bias_text",          "Show bias value", "checkbox", "Overlay bias setpoint text on image"),
        ]),
    ]

    def __init__(self, context: "AppContext", parent=None) -> None:
        super().__init__(context, parent)
        self._main_item: WorkspaceItem | None = None
        self._aux_item:  WorkspaceItem | None = None
        self.resize(1200, 650)
        self.setWindowTitle(f"Image Stack Viewer — {self.instance_id}")

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def _apply_config_to_panels(self, cfg: dict) -> None:
        cmap_list = cfg.get("colormap", {}).get("cmap_palette_list", ["gray"])
        if hasattr(self, "_panel_main"):
            self._panel_main.setup_palette(cmap_list)
        if hasattr(self, "_panel_aux"):
            self._panel_aux.setup_palette(cmap_list)

    def build_ui(self) -> None:
        from angstrompro.gui.widgets.image_stack_viewer_widget import ImageStackViewerWidget
        from angstrompro.gui.resources.colormaps import register_all
        register_all()

        cmap_list = (
            self._config
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
        self._panel_aux.setup_palette(cmap_list)

        self._splitter = QtWidgets.QSplitter(
            QtCore.Qt.Orientation.Horizontal
            if hasattr(QtCore.Qt.Orientation, "Horizontal")
            else QtCore.Qt.Horizontal
        )
        self._splitter.addWidget(self._panel_main)
        self._splitter.addWidget(self._panel_aux)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setSizes([600, 600])

        central = QtWidgets.QWidget()
        vlay = QtWidgets.QVBoxLayout(central)
        vlay.setContentsMargins(4, 4, 4, 4)
        vlay.addWidget(self._splitter, stretch=1)
        self.setCentralWidget(central)

        self._add_sync_actions()
        self._build_annotate_menu()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_splitter"):
            half = self._splitter.width() // 2
            self._splitter.setSizes([half, half])

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

        if not item.name.endswith("_fft"):
            self._auto_fft(item)

    def _auto_fft(self, src_item: WorkspaceItem) -> None:
        """Load or compute the FFT of src_item into the aux panel."""
        expected_fft_name = src_item.name + "_fft"
        existing = self.workspace.find_item(expected_fft_name)
        if existing is not None:
            self._load_fft_aux(existing)
            return

        if self._context.processes.get("spectral.fft2d") is None:
            return
        fft_name = self.workspace.suggest_name(expected_fft_name)

        def _on_result(_tid, result):
            fft_item = self.workspace.add_item(name=fft_name, payload=result)
            self._load_fft_aux(fft_item)

        self.submit_process(
            "spectral.fft2d",
            input_items = [src_item],
            params      = None,
            on_result   = _on_result,
        )

    def _load_fft_aux(self, fft_item: WorkspaceItem) -> None:
        self._aux_item = fft_item
        self.process_inputs = ([self._main_item, fft_item]
                               if self._main_item else [fft_item])
        self._panel_aux.setUdsData(fft_item.payload)
        self._panel_aux.setEnabled(True)
        if self._sync_layer:
            self._panel_aux.setImageLayer(self._panel_main.img_current_layer)
        self.statusBar().showMessage(
            f"Aux (auto FFT): {fft_item.name}", 4000)

    # ------------------------------------------------------------------
    # Message routing between panels
    # ------------------------------------------------------------------

    def _on_msg_from_main(self, msg_idx: int) -> None:
        msg = self._panel_main.msg_type[msg_idx]
        if msg == "SELECT_USD_VARIABLE":
            name = self._selected_item_name()
            if name is not None:
                self.load_item(self.workspace.get_item(name))
        elif msg == "SYNC_LAYER" and self._sync_layer:
            self._panel_aux.setImageLayer(self._panel_main.img_current_layer)

    def _on_msg_from_aux(self, msg_idx: int) -> None:
        msg = self._panel_aux.msg_type[msg_idx]
        if msg == "SELECT_USD_VARIABLE":
            self._load_aux_from_workspace()

    def _load_aux_from_workspace(self) -> None:
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

    # ------------------------------------------------------------------
    # Annotate menu
    # ------------------------------------------------------------------

    def _build_annotate_menu(self) -> None:
        menu = self.menuBar().addMenu("Points")

        menu.addAction("Set Bragg Peaks from Aux").triggered.connect(
            self._set_bragg_peaks_aux)
        menu.addAction("Set Filter Points from Aux").triggered.connect(
            self._set_filter_points_from_aux)
        menu.addAction("Set Interest Region from Main").triggered.connect(
            self._set_interest_region_main)
        menu.addAction("Set Mask Center from Main").triggered.connect(
            self._set_mask_center_main)
        menu.addAction("Set Lock-in Peak from Aux").triggered.connect(
            self._set_lockin_peak_aux)
        menu.addAction("Set Line Profile from Main").triggered.connect(
            self._set_line_profile_main)
        menu.addSeparator()

        clear_menu = menu.addMenu("Clear")
        clear_menu.addAction("Clear Bragg Peaks").triggered.connect(
            lambda: self._clear_annotation("bragg_peaks"))
        clear_menu.addAction("Clear Filter Points").triggered.connect(
            lambda: self._clear_annotation("filter_points"))
        clear_menu.addAction("Clear Interest Region").triggered.connect(
            lambda: self._clear_annotation("interest_region"))
        clear_menu.addAction("Clear Mask Center").triggered.connect(
            lambda: self._clear_annotation("mask_center"))
        clear_menu.addAction("Clear Lock-in Peak").triggered.connect(
            lambda: self._clear_annotation("lockin_peak"))
        clear_menu.addAction("Clear Line Profile").triggered.connect(
            lambda: self._clear_annotation("line_profile"))

    def _get_picked_coords(self, panel) -> "np.ndarray | None":
        """Parse img_picked_points_list from a panel into an (N,2) [row, col] array."""
        import numpy as np
        pts = getattr(panel, 'img_picked_points_list', [])
        if not pts:
            return None
        coords = []
        for s in pts:
            parts = s.split(',')
            if len(parts) >= 2:
                col = int(parts[0])
                row = int(parts[1])
                coords.append((row, col))
        return np.array(coords) if coords else None

    def _set_bragg_peaks_main(self) -> None:
        import numpy as np
        from angstrompro.core.data.annotation_data import PointSetData
        if self._main_item is None:
            return
        coords = self._get_picked_coords(self._panel_main)
        if coords is None or len(coords) == 0:
            QtWidgets.QMessageBox.information(
                self, "No points",
                "No points picked in main panel. Right-click on canvas to pick points first.")
            return
        self._main_item.annotations["bragg_peaks"] = PointSetData(coords=coords)
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Bragg peaks set: {len(coords)} points on {self._main_item.name}", 3000)

    def _set_bragg_peaks_aux(self) -> None:
        """Pick points from aux panel, store on the corresponding real-space item."""
        from angstrompro.core.data.annotation_data import PointSetData
        if self._aux_item is None:
            QtWidgets.QMessageBox.information(self, "No aux item",
                                              "Load an item into the Auxiliary panel first.")
            return
        coords = self._get_picked_coords(self._panel_aux)
        if coords is None or len(coords) == 0:
            QtWidgets.QMessageBox.information(
                self, "No points",
                "No points picked in aux panel. Right-click on canvas to pick points first.")
            return

        # Resolve target: strip _fft suffix to find the real-space item
        aux_name = self._aux_item.name
        if aux_name.endswith("_fft"):
            real_name = aux_name[:-4]
            target = self.workspace.find_item(real_name) or self._aux_item
        else:
            target = self._aux_item

        target.annotations["bragg_peaks"] = PointSetData(coords=coords)
        self.workspace.notify_changed(target.name)
        self.statusBar().showMessage(
            f"Bragg peaks set: {len(coords)} points on {target.name}", 3000)

    def _set_filter_points_from_aux(self) -> None:
        """Pick points from aux panel, store as filter_points on the real-space item."""
        from angstrompro.core.data.annotation_data import PointSetData
        if self._main_item is None:
            QtWidgets.QMessageBox.information(
                self, "No main item", "Load an item into the Main panel first.")
            return
        coords = self._get_picked_coords(self._panel_aux)
        if coords is None or len(coords) == 0:
            QtWidgets.QMessageBox.information(
                self, "No points",
                "No points picked in aux panel. Right-click on the FFT canvas to pick filter points first.")
            return
        # Always store on the real-space item (strip _fft if main item is FFT)
        name = self._main_item.name
        target = (self.workspace.find_item(name[:-4])
                  if name.endswith("_fft") else self._main_item)
        if target is None:
            target = self._main_item
        target.annotations["filter_points"] = PointSetData(coords=coords)
        self.workspace.notify_changed(target.name)
        self.statusBar().showMessage(
            f"Filter points set: {len(coords)} points on '{target.name}'", 3000)

    def _on_ws_context_menu(self, pos) -> None:
        from angstrompro.utils.qt_compat import IS_QT6
        _UserRole = QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
        tree_item = self._ws_list.itemAt(pos)
        if tree_item is None:
            return
        data = tree_item.data(0, _UserRole)
        if not isinstance(data, tuple):
            # Top-level item — delegate to base
            super()._on_ws_context_menu(pos)
            return

        item_name, role = data
        menu = QtWidgets.QMenu(self)
        act_clear = menu.addAction(f"Clear '{role}'")

        act_restore = None
        if role == "bragg_peaks":
            act_restore = menu.addAction("Restore to Aux picked points")

        act = menu.exec(self._ws_list.viewport().mapToGlobal(pos))
        if act == act_clear:
            ws_item = self.workspace.get_item(item_name)
            ws_item.annotations.pop(role, None)
            self.workspace.notify_changed(item_name)
        elif act_restore is not None and act == act_restore:
            ws_item = self.workspace.get_item(item_name)
            self._restore_bragg_peaks_to_aux(ws_item)

    def _restore_bragg_peaks_to_aux(self, ws_item: WorkspaceItem) -> None:
        ann = ws_item.annotations.get("bragg_peaks")
        if ann is None or not hasattr(ann, "coords") or len(ann.coords) == 0:
            return
        entries = [f"{int(c[1])},{int(c[0])}" for c in ann.coords]  # col,row
        self._panel_aux.img_picked_points_list = entries
        self._panel_aux.ui_lw_img_picked_points.clear()
        self._panel_aux.ui_lw_img_picked_points.addItems(entries)
        self._panel_aux.ui_lw_img_picked_points.setCurrentRow(len(entries) - 1)
        self._panel_aux.updateImage()
        self.statusBar().showMessage(
            f"Restored {len(entries)} Bragg peaks → Aux picked points", 3000)

    def _set_interest_region_main(self) -> None:
        from angstrompro.core.data.annotation_data import RegionData
        if self._main_item is None:
            return
        coords = self._get_picked_coords(self._panel_main)
        if coords is None or len(coords) < 2:
            QtWidgets.QMessageBox.information(
                self, "Need 2 points",
                "Pick exactly 2 points in main panel to define the crop region corners.")
            return
        rows = [c[0] for c in coords]
        cols = [c[1] for c in coords]
        self._main_item.annotations["interest_region"] = RegionData(
            row_min=min(rows), col_min=min(cols),
            row_max=max(rows), col_max=max(cols),
        )
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Crop region set on {self._main_item.name}", 3000)

    def _set_mask_center_main(self) -> None:
        from angstrompro.core.data.annotation_data import PointSetData
        import numpy as np
        if self._main_item is None:
            return
        coords = self._get_picked_coords(self._panel_main)
        if coords is None or len(coords) < 1:
            QtWidgets.QMessageBox.information(
                self, "Need 1 point",
                "Pick exactly 1 point in the main panel to define the mask centre.")
            return
        self._main_item.annotations["mask_center"] = PointSetData(
            coords=np.array([[coords[0][0], coords[0][1]]], dtype=float)
        )
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Mask center set on {self._main_item.name}", 3000)

    def _set_lockin_peak_aux(self) -> None:
        """Pick one point from the aux (FFT) panel, store as lockin_peak on the real-space item."""
        from angstrompro.core.data.annotation_data import PointSetData
        import numpy as np
        if self._main_item is None:
            QtWidgets.QMessageBox.information(self, "No main item",
                                              "Load an item into the Main panel first.")
            return
        coords = self._get_picked_coords(self._panel_aux)
        if coords is None or len(coords) < 1:
            QtWidgets.QMessageBox.information(
                self, "Need 1 point",
                "Pick exactly 1 point in the Aux (FFT) panel to define the lock-in Q-vector.")
            return
        # Store on the real-space item (main panel), not on the FFT item
        self._main_item.annotations["lockin_peak"] = PointSetData(
            coords=np.array([[coords[0][0], coords[0][1]]], dtype=float))
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Lock-in peak set on {self._main_item.name} "
            f"(col={int(coords[0][1])}, row={int(coords[0][0])})", 3000)

    def _set_interest_region_aux(self) -> None:
        from angstrompro.core.data.annotation_data import RegionData
        if self._aux_item is None:
            QtWidgets.QMessageBox.information(self, "No aux item",
                                              "Load an item into the Auxiliary panel first.")
            return
        coords = self._get_picked_coords(self._panel_aux)
        if coords is None or len(coords) < 2:
            QtWidgets.QMessageBox.information(
                self, "Need 2 points",
                "Pick exactly 2 points in aux panel to define the crop region corners.")
            return
        rows = [c[0] for c in coords]
        cols = [c[1] for c in coords]
        self._aux_item.annotations["interest_region"] = RegionData(
            row_min=min(rows), col_min=min(cols),
            row_max=max(rows), col_max=max(cols),
        )
        self.workspace.notify_changed(self._aux_item.name)
        self.statusBar().showMessage(
            f"Crop region set on {self._aux_item.name}", 3000)

    def _set_line_profile_main(self) -> None:
        from angstrompro.core.data.annotation_data import LineData
        if self._main_item is None:
            return
        coords = self._get_picked_coords(self._panel_main)
        if coords is None or len(coords) < 2:
            QtWidgets.QMessageBox.information(
                self, "Need 2 points",
                "Pick exactly 2 points in main panel to define the line profile endpoints.")
            return
        p1 = (float(coords[0][0]), float(coords[0][1]))
        p2 = (float(coords[1][0]), float(coords[1][1]))
        self._main_item.annotations["line_profile"] = LineData(p1=p1, p2=p2)
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Line profile set on {self._main_item.name}", 3000)

    def _set_line_profile_aux(self) -> None:
        from angstrompro.core.data.annotation_data import LineData
        if self._aux_item is None:
            QtWidgets.QMessageBox.information(self, "No aux item",
                                              "Load an item into the Auxiliary panel first.")
            return
        coords = self._get_picked_coords(self._panel_aux)
        if coords is None or len(coords) < 2:
            QtWidgets.QMessageBox.information(
                self, "Need 2 points",
                "Pick exactly 2 points in aux panel to define the line profile endpoints.")
            return
        p1 = (float(coords[0][0]), float(coords[0][1]))
        p2 = (float(coords[1][0]), float(coords[1][1]))
        self._aux_item.annotations["line_profile"] = LineData(p1=p1, p2=p2)
        self.workspace.notify_changed(self._aux_item.name)
        self.statusBar().showMessage(
            f"Line profile set on {self._aux_item.name}", 3000)

    def _clear_annotation(self, role: str) -> None:
        if self._main_item and role in self._main_item.annotations:
            del self._main_item.annotations[role]
            self.workspace.notify_changed(self._main_item.name)
            self.statusBar().showMessage(
                f"Cleared '{role}' on {self._main_item.name}", 3000)

    # ------------------------------------------------------------------

    def _check_ndim3(self, item: WorkspaceItem) -> bool:
        data = getattr(item.payload, "data", None)
        if data is None or data.ndim != 3:
            QtWidgets.QMessageBox.warning(
                self, "Wrong ndim",
                f"'{item.name}' is not ndim=3 — cannot display in Image Stack Viewer.")
            return False
        return True
