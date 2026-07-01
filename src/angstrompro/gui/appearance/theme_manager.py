"""
ThemeManager — applies pyqtdarktheme and font settings to the QApplication.

Usage
-----
    theme = ThemeManager(config.get_group("appearance"))
    theme.apply()           # apply at startup
    theme.apply("light")    # switch at runtime
"""

import logging

from angstrompro.utils.qt_compat import QtGui, QtWidgets

log = logging.getLogger(__name__)

_VALID_THEMES = ("dark", "light", "auto")


class ThemeManager:
    def __init__(self, appearance_cfg: dict) -> None:
        self._cfg = appearance_cfg

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(self, theme: str = "") -> None:
        """
        Apply theme and font to the running QApplication.

        Parameters
        ----------
        theme : "dark" | "light" | "auto" — overrides config if provided.
        """
        resolved = (theme or self._cfg.get("theme", "dark")).lower()
        if resolved not in _VALID_THEMES:
            log.warning("Unknown theme %r, falling back to 'dark'", resolved)
            resolved = "dark"

        self._apply_qdarktheme(resolved)
        self._apply_font()

    def current_theme(self) -> str:
        return self._cfg.get("theme", "dark")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_qdarktheme(self, theme: str) -> None:
        try:
            import qdarktheme

            kwargs: dict = {}
            accent = self._cfg.get("accent_color", "")
            if accent:
                kwargs["custom_colors"] = {"primary": accent}

            qdarktheme.setup_theme(theme, **kwargs)
            self._cfg["theme"] = theme
            log.info("Theme applied: %s", theme)

        except ImportError:
            log.warning(
                "pyqtdarktheme not installed — run: pip install pyqtdarktheme. "
                "Falling back to system style."
            )
        except Exception as exc:
            log.error("Failed to apply theme %r: %s", theme, exc)

    def _apply_font(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return

        family = self._cfg.get("font_family", "")
        size   = self._cfg.get("font_size", 12)

        font = app.font()
        if family:
            font.setFamily(family)
        if size:
            font.setPointSize(int(size))
        app.setFont(font)

        # Append custom component rules on top of the active theme stylesheet
        extra_qss = """
QMenuBar::item {
    padding: 4px 14px;
    spacing: 6px;
}
QMenuBar {
    padding: 2px 4px;
}

QPushButton#card_action_btn {
    font-size: 13pt;
    min-height: 38px;
    padding: 0 12px;
}
QLabel#card_instance_label {
    font-size: 14pt;
    font-weight: bold;
}
QLabel#card_info_label {
    font-size: 11pt;
}
QLabel#card_status_label {
    font-size: 11pt;
    font-weight: bold;
}
QLabel#card_category_header {
    font-size: 10pt;
    font-weight: bold;
}
QLabel#panel_summary_label {
    font-size: 10pt;
    color: grey;
}

/* ── Preferences panel ─────────────────────────────────────── */
QLabel#pref_module_label {
    font-size: 9pt;
    font-weight: 500;
    letter-spacing: 0.07em;
}
QPushButton#pref_nav_btn {
    font-size: 11pt;
    text-align: left;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 1px 6px;
}
QLabel#pref_section_title {
    font-size: 13pt;
    font-weight: 500;
}
QLabel#pref_section_header_label {
    font-size: 9pt;
    font-weight: 500;
    letter-spacing: 0.05em;
}
QLabel#pref_row_label {
    font-size: 11pt;
}
QLabel#pref_row_desc {
    font-size: 9pt;
}

/* ── Process param dialog ──────────────────────────────────── */
QLabel#param_dialog_desc {
    font-size: 10pt;
    color: grey;
}
QLabel#param_dialog_row_label {
    font-size: 11pt;
}
"""
        app.setStyleSheet(app.styleSheet() + extra_qss)
