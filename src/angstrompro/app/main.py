# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 11:34:24 2026

@author: jiahaoYan
"""

from __future__ import annotations

import sys

from angstrompro.utils.qt_compat import QtWidgets
from angstrompro.core.configs.config_manager import ConfigManager
from angstrompro.app.context import AppContext
from angstrompro.gui.appearance import ThemeManager, IconManager
from angstrompro.utils.platform_utils import set_windows_app_id
from angstrompro.app.user_data_folder import is_user_data_folder_set


def running_in_ipython():
    try:
        get_ipython()
        return True
    except NameError:
        return False


def _ensure_user_data_folder(app: QtWidgets.QApplication) -> bool:
    """
    If the user data folder has never been set, show the first-launch setup
    dialog.  Returns True if a folder is now configured, False if the user
    cancelled (caller should abort startup).
    """
    if is_user_data_folder_set():
        return True

    print("[AngstromPro] No user data folder configured — opening setup dialog…")
    try:
        from angstrompro.gui.dialogs.user_data_folder_dialog import UserDataFolderDialog
        path = UserDataFolderDialog.run()
    except Exception as exc:
        print(f"[AngstromPro] Setup dialog failed: {exc}")
        import traceback; traceback.print_exc()
        return False

    if path is None:
        print("[AngstromPro] Setup cancelled — exiting.")
    return path is not None


# ---- Main entry ----
def main(external_namespace=None, start_event_loop=True):
    # 1
    set_windows_app_id("com.angstrompro.app")

    # 2
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    # 3 — ensure user data folder is configured before anything reads from it
    if not _ensure_user_data_folder(app):
        return 1   # user cancelled first-launch setup

    # 4
    config = ConfigManager()

    # 5
    theme = ThemeManager(config.get_group("appearance"))
    theme.apply()

    # 6
    icons = IconManager(config.get_group("appearance"))

    # 7
    context = AppContext(config, theme, icons)

    # 8 — register all built-in modules
    context.module_manager.load_builtin()
    import angstrompro.gui.workbench.main_workbench  # noqa: F401
    window = context.module_manager.create("main_workbench", context)
    window.show()

    if external_namespace is not None:
        external_namespace["window"] = window

    if start_event_loop:
        exit_code = app.exec()
    else:
        exit_code = app, window

    return exit_code


# Important:
# In Spyder, if this file is executed in the console namespace,
# globals() is the console namespace.
if __name__ == "__main__":
    in_ipython = running_in_ipython()
    main(
        external_namespace=globals(),
        start_event_loop=not in_ipython,
    )
