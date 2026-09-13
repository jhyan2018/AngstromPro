"""Shared image-export support for modules using ImageStackViewerWidget."""

from __future__ import annotations

from pathlib import Path

from angstrompro.utils.qt_compat import Action, QtWidgets


def install_export_image_action(module, callback) -> Action | None:
    """Insert an ``Export Image`` action before Preferences in File."""
    file_menu = next(
        (
            action.menu()
            for action in module.menuBar().actions()
            if action.text() == "File"
        ),
        None,
    )
    if file_menu is None:
        return None

    action = Action("Export Image…", module)
    action.setShortcut("Ctrl+E")
    action.triggered.connect(callback)

    preferences = next(
        (item for item in file_menu.actions() if item.text() == "Preferences…"),
        None,
    )
    if preferences is None:
        file_menu.addSeparator()
        file_menu.addAction(action)
    else:
        separator = file_menu.insertSeparator(preferences)
        file_menu.insertAction(separator, action)
    return action


def _last_export_dir() -> str:
    try:
        from angstrompro.app.user_data_folder import get_qsettings

        settings = get_qsettings()
        saved = settings.value("Export/last_dir", "")
        if saved and Path(saved).exists():
            return str(saved)
    except Exception:
        pass
    documents = Path.home() / "Documents"
    return str(documents) if documents.exists() else str(Path.home())


def _save_export_dir(file_path: str) -> None:
    try:
        from angstrompro.app.user_data_folder import get_qsettings

        settings = get_qsettings()
        settings.setValue("Export/last_dir", str(Path(file_path).parent))
        settings.sync()
    except Exception:
        pass


def export_image(
    parent,
    primary_panel,
    reference_panel=None,
) -> None:
    """Run the standard image-export workflow for one or two image panels."""
    from angstrompro.gui.dialogs.export_image_dialog import ExportImageDialog

    dialog = ExportImageDialog.run(
        parent,
        has_aux=reference_panel is not None,
    )
    if dialog is None:
        return

    panel = (
        primary_panel
        if dialog.panel == "Primary" or reference_panel is None
        else reference_panel
    )
    pixmap = panel._pixmap_item.pixmap()
    if pixmap.isNull():
        QtWidgets.QMessageBox.information(
            parent,
            "Nothing to export",
            "No image is loaded in this panel.",
        )
        return

    export_pixmap = (
        panel._view.viewport().grab()
        if dialog.with_overlay
        else pixmap
    )

    if dialog.to_clipboard:
        if dialog.clipboard_format == "SVG":
            from angstrompro.gui.utils.clipboard_image import (
                raster_svg_bytes,
                set_svg_with_bitmap_fallback,
            )

            set_svg_with_bitmap_fallback(
                raster_svg_bytes(export_pixmap),
                export_pixmap,
            )
        else:
            QtWidgets.QApplication.clipboard().setPixmap(export_pixmap)
        parent.statusBar().showMessage("Image copied to clipboard.", 3000)
        return

    file_format = dialog.file_format
    filters = {
        "PNG": "PNG (*.png)",
        "TIFF": "TIFF (*.tif *.tiff)",
        "JPEG": "JPEG (*.jpg *.jpeg)",
    }
    chosen_filter = filters.get(file_format, filters["PNG"])
    path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
        parent,
        "Save Image",
        _last_export_dir(),
        ";;".join(filters.values()),
        chosen_filter,
    )
    if not path:
        return
    export_pixmap.save(path)
    _save_export_dir(path)
    parent.statusBar().showMessage(f"Saved to {path}", 4000)


__all__ = ["export_image", "install_export_image_action"]
