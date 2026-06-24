"""
IconManager — resolve icon names to QIcon objects.

Resolution order
----------------
1. Cache hit → return immediately.
2. Name starts with "fa", "mdi", "ei", "ph" or contains "." → qtawesome.
3. Otherwise → look in bundled resources/icons/, then custom_icon_dir from config.

Usage
-----
    icons = IconManager(config.get_group("appearance"))
    icon  = icons.get("fa5s.folder-open")        # qtawesome
    icon  = icons.get("logo")                    # resources/icons/logo.png
    icon  = icons.get("logo", color="#4fc3f7")   # qtawesome with tint
"""

import logging
from pathlib import Path

from angstrompro.utils.qt_compat import QtGui

log = logging.getLogger(__name__)

# Bundled icons directory (sibling of this file's package root)
_BUNDLED_ICON_DIR = Path(__file__).parent.parent.parent / "resources" / "icons"

# Recognised qtawesome collection prefixes
_QTA_PREFIXES = ("fa", "mdi", "ei", "ph", "ri", "bi", "msc")


class IconManager:
    def __init__(self, appearance_cfg: dict) -> None:
        self._cfg = appearance_cfg
        self._cache: dict[str, QtGui.QIcon] = {}

        custom_dir = appearance_cfg.get("custom_icon_dir", "")
        self._custom_dir: Path | None = Path(custom_dir) if custom_dir else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, name: str, color: str = "", size: int = 0) -> QtGui.QIcon:
        """
        Return a QIcon for the given name.

        Parameters
        ----------
        name  : qtawesome name ("fa5s.save") or file stem ("logo")
        color : optional hex colour string, applied only for qtawesome icons
        size  : icon size hint in px (0 = use appearance config default)
        """
        cache_key = f"{name}:{color}:{size}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        icon = self._load(name, color, size)
        self._cache[cache_key] = icon
        return icon

    def clear_cache(self) -> None:
        self._cache.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self, name: str, color: str, size: int) -> QtGui.QIcon:
        if self._is_qta_name(name):
            return self._load_qta(name, color, size)
        return self._load_file(name)

    @staticmethod
    def _is_qta_name(name: str) -> bool:
        return "." in name and any(name.startswith(p) for p in _QTA_PREFIXES)

    def _load_qta(self, name: str, color: str, size: int) -> QtGui.QIcon:
        try:
            import qtawesome as qta
            kwargs: dict = {}
            if color:
                kwargs["color"] = color
            else:
                # Use accent colour from config if set
                accent = self._cfg.get("accent_color", "")
                if accent:
                    kwargs["color"] = accent
            if size:
                kwargs["scale_factor"] = size / (self._cfg.get("icon_size", 20) or 20)
            return qta.icon(name, **kwargs)
        except Exception as exc:
            log.warning("qtawesome failed for %r: %s", name, exc)
            return QtGui.QIcon()

    def _load_file(self, name: str) -> QtGui.QIcon:
        for directory in self._search_dirs():
            for ext in ("svg", "png", "ico"):
                candidate = directory / f"{name}.{ext}"
                if candidate.exists():
                    icon = QtGui.QIcon(str(candidate))
                    if not icon.isNull():
                        return icon
        log.warning("Icon file not found: %r", name)
        return QtGui.QIcon()

    def _search_dirs(self) -> list[Path]:
        dirs = [_BUNDLED_ICON_DIR]
        if self._custom_dir and self._custom_dir.is_dir():
            dirs.insert(0, self._custom_dir)  # custom takes priority
        return dirs
