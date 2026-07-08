# -*- coding: utf-8 -*-
"""
Created on 2026-07-07

@author: jiahaoYan

PersistentDialog — QDialog base that saves and restores its size via QSettings.

Subclass must set ``_settings_key`` to a unique string.  A missing or duplicate
key is caught at save time so two dialogs never silently share state.

Usage
-----
    class MyDialog(PersistentDialog):
        _settings_key = "MyDialog"

        def __init__(self, parent=None):
            super().__init__(parent, default_size=(700, 480))
            ...
"""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets

# Maps settings_key → class name; catches duplicate keys at runtime.
_REGISTERED_KEYS: dict[str, str] = {}


class PersistentDialog(QtWidgets.QDialog):
    """QDialog that persists its size across sessions via QSettings."""

    _settings_key: str = ""

    def __init__(self, parent=None, *, default_size: tuple[int, int] = (800, 500)) -> None:
        super().__init__(parent)
        self._default_size = QtCore.QSize(*default_size)
        self._size_restored = False
        self.finished.connect(self._save_size)

    # ------------------------------------------------------------------
    # Qt event override — restore on first show
    # ------------------------------------------------------------------

    def showEvent(self, event: QtCore.QEvent) -> None:
        super().showEvent(event)
        if not self._size_restored:
            self._size_restored = True
            self._restore_size()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _qsettings_key(self) -> str:
        key = self._settings_key or type(self).__name__
        return f"dialogs/{key}/size"

    def _restore_size(self) -> None:
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            geo = get_qsettings().value(self._qsettings_key())
            if geo:
                self.restoreGeometry(geo)
            else:
                self.resize(self._default_size)
        except Exception:
            self.resize(self._default_size)

    def _save_size(self) -> None:
        key = self._settings_key or type(self).__name__
        cls_name = type(self).__name__
        existing = _REGISTERED_KEYS.get(key)
        if existing is None:
            _REGISTERED_KEYS[key] = cls_name
        elif existing != cls_name:
            import warnings
            warnings.warn(
                f"PersistentDialog key collision: {cls_name!r} and {existing!r} "
                f"share _settings_key={key!r}. One will overwrite the other's geometry.",
                stacklevel=2,
            )
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            get_qsettings().setValue(self._qsettings_key(), self.saveGeometry())
        except Exception:
            pass
