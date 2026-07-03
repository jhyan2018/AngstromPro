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
from angstrompro.utils.qt_compat import QtCore, QtGui, QtWidgets, Action
from angstrompro.gui.widgets.preferences import PrefSection, PrefItem
import angstrompro.gui.widgets.preferences.widgets  # registers custom widget types

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext

log = logging.getLogger(__name__)


class _VideoExportProgressDialog(QtWidgets.QDialog):
    """
    Progress dialog for video export that stays open after completion,
    showing a summary before the user dismisses it.
    """

    def __init__(self, n_frames: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Video")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.cancelled = False
        self._n = n_frames
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self._label = QtWidgets.QLabel("Preparing…")
        layout.addWidget(self._label)

        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, self._n)
        self._bar.setValue(0)
        layout.addWidget(self._bar)

        # Summary (hidden until done)
        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setVisible(False)
        self._summary.setFixedHeight(130)
        layout.addWidget(self._summary)

        # Buttons
        self._btn_box = QtWidgets.QDialogButtonBox()
        self._cancel_btn = self._btn_box.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._ok_btn = self._btn_box.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setVisible(False)
        self._ok_btn.clicked.connect(self.accept)
        layout.addWidget(self._btn_box)

    def set_progress(self, value: int, label: str) -> None:
        self._bar.setValue(value)
        self._label.setText(label)

    def finish(self, *, success: bool, summary: str, path: str) -> None:
        self._bar.setValue(self._n)
        if success:
            self._label.setText(f"Done — saved to:\n{path}")
            self._summary.setPlainText(summary)
            self._summary.setVisible(True)
        else:
            self._label.setText("Export failed.")
            self._summary.setPlainText(
                f"Error:\n{summary}\n\n"
                "For MP4/AVI: pip install imageio[ffmpeg]\n"
                "For GIF:     pip install pillow")
            self._summary.setVisible(True)
        self._cancel_btn.setVisible(False)
        self._ok_btn.setVisible(True)
        self.adjustSize()

    def _on_cancel(self) -> None:
        self.cancelled = True
        self._cancel_btn.setEnabled(False)
        self._label.setText("Cancelling…")


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

        menu.addAction("Set Interest Region from Main").triggered.connect(
            self._set_interest_region_main)
        menu.addAction("Set Mask Center from Main").triggered.connect(
            self._set_mask_center_main)
        menu.addAction("Set Bragg Peaks from Aux").triggered.connect(
            self._set_bragg_peaks_aux)
        menu.addAction("Set Filter Points from Aux").triggered.connect(
            self._set_filter_points_from_aux)
        menu.addAction("Set Lock-in Peak from Aux").triggered.connect(
            self._set_lockin_peak_aux)
        cut_menu = menu.addMenu("Cut")
        cut_menu.addAction("Set Line Cut from Main").triggered.connect(
            self._set_line_cut_main)
        cut_menu.addAction("Set Circle Cut from Main").triggered.connect(
            self._set_circle_cut_points_main)
        register_menu = menu.addMenu("Register")
        register_menu.addAction("Set Src Points from Main").triggered.connect(
            self._set_register_points_main)
        register_menu.addAction("Set Ref Points from Aux").triggered.connect(
            self._set_register_ref_points_aux)

        menu.addSeparator()

        clear_menu = menu.addMenu("Clear")
        clear_menu.addAction("Clear Interest Region").triggered.connect(
            lambda: self._clear_annotation("interest_region"))
        clear_menu.addAction("Clear Mask Center").triggered.connect(
            lambda: self._clear_annotation("mask_center"))
        clear_menu.addAction("Clear Bragg Peaks").triggered.connect(
            lambda: self._clear_annotation("bragg_peaks"))
        clear_menu.addAction("Clear Filter Points").triggered.connect(
            lambda: self._clear_annotation("filter_points"))
        clear_menu.addAction("Clear Lock-in Peak").triggered.connect(
            lambda: self._clear_annotation("lockin_peak"))
        clear_menu.addAction("Clear Line Cut").triggered.connect(
            lambda: self._clear_annotation("line_cut"))
        clear_menu.addAction("Clear Circle Cut").triggered.connect(
            lambda: self._clear_annotation("circle_cut_points"))
        clear_menu.addAction("Clear Register Src Points").triggered.connect(
            lambda: self._clear_annotation("register_points"))
        clear_menu.addAction("Clear Register Ref Points").triggered.connect(
            lambda: self._clear_annotation("register_reference_points"))

    # ------------------------------------------------------------------
    # File menu override — adds Export Image… before Close
    # ------------------------------------------------------------------

    def _build_file_menu(self) -> None:
        super()._build_file_menu()
        # Find the File menu that the base class just added
        file_menu = None
        for action in self.menuBar().actions():
            if action.text() == "File":
                file_menu = action.menu()
                break
        if file_menu is None:
            return

        # Insert Export Image… before the Close action
        close_action = None
        for act in file_menu.actions():
            if act.text() == "Close Window":
                close_action = act
                break

        export_img_action = Action("Export Image…", self)
        export_img_action.setShortcut("Ctrl+E")
        export_img_action.triggered.connect(self._on_export_image)

        export_vid_action = Action("Export Video…", self)
        export_vid_action.setShortcut("Ctrl+Shift+E")
        export_vid_action.triggered.connect(self._on_export_video)

        if close_action is not None:
            file_menu.insertAction(close_action, export_img_action)
            file_menu.insertAction(close_action, export_vid_action)
            file_menu.insertSeparator(close_action)
        else:
            file_menu.addSeparator()
            file_menu.addAction(export_img_action)
            file_menu.addAction(export_vid_action)

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _last_export_dir() -> str:
        """Return last-used export directory, falling back to Documents."""
        from pathlib import Path
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            s = get_qsettings()
            saved = s.value("Export/last_dir", "")
            if saved and Path(saved).exists():
                return saved
        except Exception:
            pass
        docs = Path.home() / "Documents"
        return str(docs) if docs.exists() else str(Path.home())

    @staticmethod
    def _save_export_dir(file_path: str) -> None:
        """Persist the directory of the last saved export file."""
        from pathlib import Path
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            s = get_qsettings()
            s.setValue("Export/last_dir", str(Path(file_path).parent))
            s.sync()
        except Exception:
            pass

    def _on_export_image(self) -> None:
        from angstrompro.gui.dialogs.export_image_dialog import ExportImageDialog
        has_aux = self._aux_item is not None
        dlg = ExportImageDialog.run(self, has_aux=has_aux)
        if dlg is None:
            return

        panel = self._panel_main if dlg.panel == "Main" else self._panel_aux
        pixmap = panel._pixmap_item.pixmap()
        if pixmap.isNull():
            QtWidgets.QMessageBox.information(
                self, "Nothing to export", "No image is loaded in this panel.")
            return

        if dlg.with_overlay:
            export_pixmap = panel._view.viewport().grab()
        else:
            export_pixmap = pixmap

        if dlg.to_clipboard:
            QtWidgets.QApplication.clipboard().setPixmap(export_pixmap)
            self.statusBar().showMessage("Image copied to clipboard.", 3000)
        else:
            fmt = dlg.file_format
            filters = {"PNG": "PNG (*.png)", "TIFF": "TIFF (*.tif *.tiff)",
                       "JPEG": "JPEG (*.jpg *.jpeg)"}
            chosen_filter = filters.get(fmt, "PNG (*.png)")
            all_filters = ";;".join(filters.values())
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Image", self._last_export_dir(), all_filters, chosen_filter)
            if path:
                export_pixmap.save(path)
                self._save_export_dir(path)
                self.statusBar().showMessage(f"Saved to {path}", 4000)

    def _on_export_video(self) -> None:
        from angstrompro.gui.dialogs.export_video_dialog import ExportVideoDialog

        # Determine available layers from main item
        n_layers = (self._main_item.payload.data.shape[0]
                    if self._main_item is not None else 1)
        has_aux  = self._aux_item is not None

        dlg = ExportVideoDialog.run(self, has_aux=has_aux, n_layers=n_layers)
        if dlg is None:
            return

        panel = self._panel_main if dlg.panel == "Main" else self._panel_aux
        if panel._pixmap_item.pixmap().isNull():
            QtWidgets.QMessageBox.information(
                self, "Nothing to export", "No image is loaded in this panel.")
            return

        fmt_ext = {"MP4": ".mp4", "GIF": ".gif", "AVI": ".avi"}
        ext = fmt_ext[dlg.file_format]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Video", self._last_export_dir(),
            f"{dlg.file_format} (*{ext})")
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext
        self._save_export_dir(path)
        self._run_video_export(panel, dlg, path)

    def _run_video_export(self, panel, dlg, path: str) -> None:
        first = dlg.first_layer
        last  = dlg.last_layer
        layers = range(first, last + 1)
        n = len(layers)

        import numpy as np

        # Custom progress dialog that stays open after completion
        prog = _VideoExportProgressDialog(n, self)
        prog.show()
        QtWidgets.QApplication.processEvents()

        frames: list[np.ndarray] = []

        _fmt_rgba = (QtGui.QImage.Format.Format_RGBA8888
                     if hasattr(QtGui.QImage.Format, "Format_RGBA8888")
                     else QtGui.QImage.Format_RGBA8888)

        original_layer = panel.ui_sb_image_layers.value()
        for i, layer in enumerate(layers):
            if prog.cancelled:
                break
            prog.set_progress(i, f"Capturing layer {layer} / {last}…")
            QtWidgets.QApplication.processEvents()
            panel.ui_sb_image_layers.setValue(layer)
            QtWidgets.QApplication.processEvents()

            if dlg.with_overlay:
                px  = panel._view.viewport().grab()
                img = px.toImage()
            else:
                img = panel._pixmap_item.pixmap().toImage()

            img = img.convertToFormat(_fmt_rgba)
            ptr = img.bits()
            if hasattr(ptr, "setsize"):
                ptr.setsize(img.sizeInBytes()
                            if hasattr(img, "sizeInBytes") else img.byteCount())
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape(
                img.height(), img.width(), 4).copy()
            frames.append(arr[..., :3])

        panel.ui_sb_image_layers.setValue(original_layer)
        QtWidgets.QApplication.processEvents()

        if prog.cancelled or not frames:
            prog.close()
            self.statusBar().showMessage("Export cancelled.", 3000)
            return

        prog.set_progress(n, "Writing file…")
        QtWidgets.QApplication.processEvents()

        try:
            summary = self._write_video(frames, path, dlg)
            prog.finish(success=True, summary=summary, path=path)
            self.statusBar().showMessage(f"Video saved to {path}", 5000)
        except Exception as exc:
            prog.finish(success=False, summary=str(exc), path=path)
            self.statusBar().showMessage("Export failed.", 4000)

    @staticmethod
    def _write_video(frames: list, path: str, dlg) -> str:
        """Write frames to file. Returns a human-readable summary string."""
        fmt = dlg.file_format
        fps = dlg.fps
        n   = len(frames)
        h, w = frames[0].shape[:2]

        if fmt == "GIF":
            from PIL import Image as PilImage
            import PIL
            duration_ms = int(1000 / fps)
            pil_frames  = [PilImage.fromarray(f) for f in frames]
            pil_frames[0].save(
                path, save_all=True, append_images=pil_frames[1:],
                loop=0, duration=duration_ms, optimize=False)
            return (f"Format:  GIF\n"
                    f"Backend: Pillow {PIL.__version__}\n"
                    f"Frames:  {n}  ({w} × {h} px)\n"
                    f"FPS:     {fps}\n"
                    f"Duration: {n / fps:.1f} s")
        else:
            import imageio
            quality = dlg.quality
            # Map 0-100 → bitrate string: 100→"50M", 50→"8M", 0→"500k"
            # Bitrate gives true full-range quality control across all codecs
            # without relying on codec-specific CRF/qscale parameters
            mbps = 0.5 + (quality / 100) ** 2 * 49.5   # quadratic: more headroom at top
            bitrate = f"{mbps:.1f}M"
            if fmt == "MP4":
                codec      = "libx264"
                codec_desc = f"libx264 via ffmpeg  ({bitrate})"
            else:  # AVI
                codec      = "mjpeg"
                codec_desc = f"mjpeg via ffmpeg  ({bitrate})"

            imageio.mimwrite(path, frames, fps=fps, codec=codec,
                             bitrate=bitrate, macro_block_size=1)

            return (f"Format:  {fmt}\n"
                    f"Backend: imageio {imageio.__version__} + ffmpeg\n"
                    f"Codec:   {codec_desc}\n"
                    f"Frames:  {n}  ({w} × {h} px)\n"
                    f"FPS:     {fps}    Quality: {quality}/100  ({bitrate})\n"
                    f"Duration: {n / fps:.1f} s")

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

    def _set_register_points_main(self) -> None:
        """Pick points from main panel, store as register_points on main item."""
        from angstrompro.core.data.annotation_data import PointSetData
        if self._main_item is None:
            QtWidgets.QMessageBox.information(
                self, "No main item", "Load an item into the Main panel first.")
            return
        coords = self._get_picked_coords(self._panel_main)
        if coords is None or len(coords) == 0:
            QtWidgets.QMessageBox.information(
                self, "No points",
                "No points picked in main panel. Right-click on canvas to pick points first.")
            return
        self._main_item.annotations["register_points"] = PointSetData(coords=coords)
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Register src points set: {len(coords)} points on '{self._main_item.name}'", 3000)

    def _set_register_ref_points_aux(self) -> None:
        """Pick points from aux panel, store as register_reference_points on main item."""
        from angstrompro.core.data.annotation_data import PointSetData
        if self._main_item is None:
            QtWidgets.QMessageBox.information(
                self, "No main item", "Load an item into the Main panel first.")
            return
        coords = self._get_picked_coords(self._panel_aux)
        if coords is None or len(coords) == 0:
            QtWidgets.QMessageBox.information(
                self, "No points",
                "No points picked in aux panel. Right-click on canvas to pick points first.")
            return
        self._main_item.annotations["register_reference_points"] = PointSetData(coords=coords)
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Register ref points set: {len(coords)} points on '{self._main_item.name}'", 3000)

    def _set_circle_cut_points_main(self) -> None:
        """Pick 2 points from main panel, store as circle_cut_points on main item."""
        from angstrompro.core.data.annotation_data import PointSetData
        if self._main_item is None:
            QtWidgets.QMessageBox.information(
                self, "No main item", "Load an item into the Main panel first.")
            return
        coords = self._get_picked_coords(self._panel_main)
        if coords is None or len(coords) < 2:
            QtWidgets.QMessageBox.information(
                self, "Need 2 points",
                "Pick exactly 2 points on the main canvas first: [0] centre, [1] edge.")
            return
        self._main_item.annotations["circle_cut_points"] = PointSetData(coords=coords[:2])
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Circle cut points set on '{self._main_item.name}'", 3000)

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

    def _set_line_cut_main(self) -> None:
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
        self._main_item.annotations["line_cut"] = LineData(p1=p1, p2=p2)
        self.workspace.notify_changed(self._main_item.name)
        self.statusBar().showMessage(
            f"Line profile set on {self._main_item.name}", 3000)

    def _set_line_cut_aux(self) -> None:
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
        self._aux_item.annotations["line_cut"] = LineData(p1=p1, p2=p2)
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
