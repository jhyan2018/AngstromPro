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
