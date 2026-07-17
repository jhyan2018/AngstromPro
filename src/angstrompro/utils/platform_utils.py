"""
Platform-specific startup helpers.
"""

import sys
import logging

log = logging.getLogger(__name__)


def set_windows_app_id(app_id: str) -> None:
    """
    Set the Windows AppUserModelID so the taskbar shows the app's own
    icon instead of the Python launcher icon.

    Must be called BEFORE QApplication is created (or at the very least
    before the first window is shown).

    No-op on macOS and Linux.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        log.debug("Windows AppUserModelID set to %r", app_id)
    except Exception as exc:
        log.warning("Could not set Windows AppUserModelID: %s", exc)
