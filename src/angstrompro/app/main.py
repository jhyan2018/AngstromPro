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


#
def running_in_ipython():
    try:
        get_ipython()
        return True
    except NameError:
        return False


# ---- Main entry ----
def main(external_namespace=None, start_event_loop=True):
    # 1
    set_windows_app_id("com.angstrompro.app")
    
    # 2
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    # 3
    config = ConfigManager()
    
    # 4
    theme   = ThemeManager(config.get_group("appearance"))
    theme.apply()                          # must be called before any window opens
    
    # 5
    icons   = IconManager(config.get_group("appearance"))
    
    # 6
    context = AppContext(config, theme, icons)
    
    # 7 — import triggers @register_module on MainWorkbench and other built-ins
    import angstrompro.gui.workbench.main_workbench  # noqa: F401
    window = context.module_manager.create("main_workbench", context)
    window.show()

    # keep references alive
    if external_namespace is not None:
        #external_namespace["data_manager"] = data_manager
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