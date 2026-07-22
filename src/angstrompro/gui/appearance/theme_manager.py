"""Application-owned light/dark appearance for AngstromPro.

The theme deliberately uses Qt's Fusion style and an AngstromPro stylesheet
instead of inheriting Spyder's QApplication style or depending on a third-party
theme package.  This keeps control metrics compact and predictable when the
application is launched from different Python environments.
"""

from __future__ import annotations

import logging
import sys

from angstrompro.utils.qt_compat import QtCore, QtGui, QtWidgets

log = logging.getLogger(__name__)

_VALID_THEMES = ("dark", "light", "auto")
_FONT_CANDIDATES = ("Segoe UI", "Noto Sans", "DejaVu Sans", "Arial")
_MONOSPACE_CANDIDATES = (
    "Cascadia Mono", "Consolas", "DejaVu Sans Mono",
    "Liberation Mono", "Courier New",
)


def _role(name: str):
    roles = getattr(QtGui.QPalette, "ColorRole", QtGui.QPalette)
    return getattr(roles, name)


def _has_font_family(family: str) -> bool:
    """Query one family without enumerating problematic legacy Windows fonts."""
    info = QtGui.QFontInfo(QtGui.QFont(family))
    return (info.exactMatch()
            or info.family().casefold() == family.casefold())


class _NativeTitleBarFilter(QtCore.QObject):
    """Refresh native frames for top-level windows created after startup."""

    def eventFilter(self, watched, event):
        show_type = (QtCore.QEvent.Type.Show
                     if hasattr(QtCore.QEvent, "Type") else QtCore.QEvent.Show)
        if event.type() == show_type and isinstance(watched, QtWidgets.QWidget):
            if watched.isWindow():
                app = QtWidgets.QApplication.instance()
                theme = (app.property("angstrompro_native_theme")
                         if app is not None else None)
                if theme:
                    QtCore.QTimer.singleShot(
                        0, lambda selected=str(theme):
                        ThemeManager._sync_native_title_bars(selected))
        return super().eventFilter(watched, event)


class ThemeManager:
    def __init__(self, appearance_cfg: dict) -> None:
        self._cfg = appearance_cfg

    def apply(self, theme: str = "") -> None:
        """Apply the configured theme and font to the running application."""
        requested = (theme or self._cfg.get("theme", "dark")).lower()
        if requested not in _VALID_THEMES:
            log.warning("Unknown theme %r, falling back to 'dark'", requested)
            requested = "dark"

        app = QtWidgets.QApplication.instance()
        if app is None:
            return

        resolved = self._resolve_auto(requested, app)
        native_scheme_managed = self._apply_qt_color_scheme(resolved)
        if not app.property("angstrompro_fusion_initialized"):
            app.setStyle("Fusion")
            app.setProperty("angstrompro_fusion_initialized", True)
        app.setPalette(self._palette(resolved))
        # Replace, rather than append, so applying Preferences repeatedly does
        # not retain rules from the previous theme or grow the stylesheet.
        app.setStyleSheet(self._stylesheet(resolved))
        # Apply the selected font after the first stylesheet polish.  Reversing
        # this order lets Qt's style engine replace cached fonts on menu bars
        # and some labels during startup; a later Preferences Apply then seems
        # to "fix" them only because it emits another application-font event.
        self._apply_font(app)
        app.setProperty("angstrompro_native_theme", resolved)
        if (not native_scheme_managed and sys.platform == "win32"
                and not hasattr(app, "_angstrompro_titlebar_filter")):
            titlebar_filter = _NativeTitleBarFilter(app)
            app.installEventFilter(titlebar_filter)
            # QApplication must own a Python reference as well as QObject
            # parentage so the binding cannot garbage-collect the filter.
            app._angstrompro_titlebar_filter = titlebar_filter
        if not native_scheme_managed:
            self._sync_native_title_bars(resolved)
            # Older Qt versions can finish processing the palette after this
            # callback returns. Repeat the fallback on the next event turn.
            QtCore.QTimer.singleShot(
                0, lambda selected=resolved:
                self._sync_native_title_bars(selected))
        self._cfg["theme"] = requested
        log.info("AngstromPro theme applied: %s", resolved)

    def current_theme(self) -> str:
        return self._cfg.get("theme", "dark")

    @staticmethod
    def _apply_qt_color_scheme(theme: str) -> bool:
        """Let Qt's platform plugin manage native captions when supported."""
        hints = QtGui.QGuiApplication.styleHints()
        color_scheme = getattr(QtCore.Qt, "ColorScheme", None)
        if hints is None or color_scheme is None or not hasattr(hints, "setColorScheme"):
            return False
        try:
            scheme = (color_scheme.Dark if theme == "dark"
                      else color_scheme.Light)
            hints.setColorScheme(scheme)
            return hints.colorScheme() == scheme
        except Exception as exc:
            log.debug("Qt color-scheme API unavailable: %s", exc)
            return False

    @staticmethod
    def _resolve_auto(theme: str, app: QtWidgets.QApplication) -> str:
        if theme != "auto":
            return theme
        # Inspect the host/system palette before replacing it.  This also
        # works with Qt versions that predate native colour-scheme support.
        window = app.palette().color(_role("Window"))
        return "dark" if window.lightness() < 128 else "light"

    def _apply_font(self, app: QtWidgets.QApplication) -> None:
        family = self._font_family()
        font = QtGui.QFont(family)
        size = self._cfg.get("font_size", 10)
        try:
            font.setPointSize(max(7, int(float(size))))
        except (TypeError, ValueError):
            font.setPointSize(10)
        app.setFont(font)

    def _font_family(self) -> str:
        requested = str(self._cfg.get("font_family", "")).strip()
        if requested:
            return requested
        return next((name for name in _FONT_CANDIDATES
                     if _has_font_family(name)), "Sans Serif")

    @staticmethod
    def _monospace_family() -> str:
        return next((name for name in _MONOSPACE_CANDIDATES
                     if _has_font_family(name)), "monospace")

    @staticmethod
    def _sync_native_title_bars(theme: str) -> None:
        """Apply and immediately repaint native Windows title-bar colours."""
        if sys.platform != "win32":
            return
        app = QtWidgets.QApplication.instance()
        if app is None:
            return

        try:
            import ctypes
            from ctypes import wintypes

            dwm = ctypes.windll.dwmapi
            user32 = ctypes.windll.user32
            enabled = ctypes.c_int(1 if theme == "dark" else 0)

            def colorref(hex_color: str):
                color = QtGui.QColor(hex_color)
                # Windows COLORREF stores bytes as 0x00BBGGRR.
                return ctypes.c_uint(
                    color.red() | (color.green() << 8) | (color.blue() << 16))

            caption = colorref("#25282c" if theme == "dark" else "#f4f5f7")
            caption_text = colorref("#ffffff" if theme == "dark" else "#25282c")
            border = colorref("#555b63" if theme == "dark" else "#c5c9cf")

            # Attribute 20 is supported by current Windows 10/11 builds; 19 is
            # the equivalent on a small set of earlier Windows 10 releases.
            for widget in app.topLevelWidgets():
                if not widget.isWindow() or not widget.isVisible():
                    continue
                hwnd = wintypes.HWND(int(widget.winId()))
                result = dwm.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
                if result != 0:
                    dwm.DwmSetWindowAttribute(
                        hwnd, 19, ctypes.byref(enabled), ctypes.sizeof(enabled))

                # Windows 11 and recent Windows 10 builds support explicit
                # non-client colours.  These make light -> dark and dark ->
                # light transitions deterministic even when the immersive
                # flag is cached until the next activation change.
                for attribute, value in ((34, border),
                                         (35, caption),
                                         (36, caption_text)):
                    dwm.DwmSetWindowAttribute(
                        hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))

                # Tell Windows that the non-client frame changed, but do not
                # move, resize, reorder, or activate the window.
                user32.SetWindowPos(
                    hwnd, None, 0, 0, 0, 0,
                    0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
                user32.RedrawWindow(
                    hwnd, None, None, 0x0001 | 0x0080 | 0x0100 | 0x0400)
            dwm.DwmFlush()
        except Exception as exc:
            # Native title-bar colouring is cosmetic; never prevent a theme
            # change on unsupported Windows configurations.
            log.debug("Could not refresh native title bars: %s", exc)

    def _palette(self, theme: str) -> QtGui.QPalette:
        dark = theme == "dark"
        colors = ({
            "Window": "#25282c", "WindowText": "#e6e6e6",
            "Base": "#1f2226", "AlternateBase": "#2b2f34",
            "ToolTipBase": "#30343a", "ToolTipText": "#f2f2f2",
            "Text": "#e6e6e6", "Button": "#30343a",
            "ButtonText": "#e6e6e6", "BrightText": "#ffffff",
            "Highlight": "#3d8bfd",
            "HighlightedText": "#ffffff", "Mid": "#555b63",
            "Midlight": "#3a3f45", "Dark": "#17191c",
            "Light": "#444a51", "Link": "#65a8ff",
        } if dark else {
            "Window": "#f4f5f7", "WindowText": "#25282c",
            "Base": "#ffffff", "AlternateBase": "#f0f2f4",
            "ToolTipBase": "#ffffff", "ToolTipText": "#25282c",
            "Text": "#25282c", "Button": "#f7f8fa",
            "ButtonText": "#25282c", "BrightText": "#ffffff",
            "Highlight": "#1976d2",
            "HighlightedText": "#ffffff", "Mid": "#c5c9cf",
            "Midlight": "#e2e5e9", "Dark": "#9ca2aa",
            "Light": "#ffffff", "Link": "#0969da",
        })
        palette = QtGui.QPalette()
        for name, color in colors.items():
            palette.setColor(_role(name), QtGui.QColor(color))
        return palette

    def _stylesheet(self, theme: str) -> str:
        dark = theme == "dark"
        try:
            base_size = max(7, int(float(self._cfg.get("font_size", 10))))
        except (TypeError, ValueError):
            base_size = 10
        small_size = max(7, base_size - 1)
        action_size = base_size + 1
        title_size = base_size + 2
        body_family = self._font_family().replace('"', '')
        monospace_family = self._monospace_family().replace('"', '')
        accent = "#3d8bfd" if dark else "#1976d2"
        border = "#555b63" if dark else "#c5c9cf"
        hover = "#3a3f45" if dark else "#e8ebef"
        pressed = "#444a51" if dark else "#dce1e6"
        disabled = "#7f858d" if dark else "#969ca4"

        return f"""
/* Compact application controls.  Heights follow the application font and DPI;
   padding is intentionally modest so dense scientific panels remain usable. */
QWidget {{
    font-family: "{body_family}";
    font-size: {base_size}pt;
    selection-background-color: {accent};
}}
QToolTip {{ border: 1px solid {border}; padding: 3px 5px; }}

QPushButton, QToolButton {{
    border: 1px solid {border}; border-radius: 3px;
    padding: 2px 7px; min-height: 20px;
}}
QPushButton:hover, QToolButton:hover {{ background: {hover}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {pressed}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {disabled}; }}
QPushButton:default {{ border: 1px solid {accent}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    border: 1px solid {border}; border-radius: 3px;
    padding: 2px 5px; min-height: 20px;
}}
QComboBox {{ padding-right: 22px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {accent};
}}
QAbstractItemView {{ border: 1px solid {border}; outline: 0; }}
QAbstractItemView::item {{ padding: 2px 4px; }}

QCheckBox, QRadioButton {{ spacing: 5px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 14px; height: 14px; }}

QMenuBar {{ padding: 1px 3px; }}
QMenuBar::item {{ padding: 3px 9px; spacing: 4px; }}
QMenu::item {{ padding: 4px 24px 4px 8px; }}
QMenu::item:selected {{ background: {accent}; color: white; }}

QTabBar::tab {{ padding: 4px 10px; }}
QHeaderView::section {{ padding: 3px 6px; border: 0; border-right: 1px solid {border}; }}
QTableWidget, QTreeWidget, QListWidget {{ alternate-background-color: palette(alternate-base); }}
QScrollBar:vertical {{ width: 12px; margin: 0; }}
QScrollBar:horizontal {{ height: 12px; margin: 0; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}

/* Semantic typography roles.  Existing object names are grouped here while
   widgets outside these components can opt in with typographyRole. */
QLabel#card_instance_label,
QLabel#pref_section_title,
*[typographyRole="heading"] {{
    font-size: {title_size}pt; font-weight: 600;
}}
QLabel#card_category_header,
QLabel#pref_module_label,
QLabel#pref_section_header_label,
*[typographyRole="section"] {{
    font-size: {small_size}pt; font-weight: 600; letter-spacing: 0.05em;
}}
QLabel#panel_summary_label,
QLabel#pref_row_desc,
QLabel#param_dialog_desc,
*[typographyRole="secondary"] {{
    font-size: {small_size}pt; color: {disabled};
}}
*[typographyRole="hint"] {{
    font-size: {small_size}pt; color: {disabled}; font-style: italic;
}}
QLabel#card_status_label,
*[typographyRole="notification"] {{
    font-size: {base_size}pt; font-weight: 600;
}}
*[typographyRole="monospace"] {{
    font-family: "{monospace_family}";
    font-size: {small_size}pt;
    color: {disabled};
}}

/* Component layout rules; typography comes from the roles above. */
QPushButton#card_action_btn {{ font-size: {action_size}pt; min-height: 28px; padding: 1px 9px; }}
QPushButton#pref_nav_btn {{
    font-size: {base_size}pt; text-align: left; border: none;
    border-radius: 5px; padding: 6px 10px; margin: 1px 6px;
}}
"""
