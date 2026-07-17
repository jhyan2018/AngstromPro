# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 14:37:13 2026

@author: jiahaoYan
"""

"""
AppSignals — central Qt signal bus for app-wide cross-cutting events.

Usage
-----
    # emit
    context.signals.status_message.emit("Ready.")
    context.signals.error_occurred.emit("Process failed", traceback_text)

    # connect
    context.signals.status_message.connect(status_bar.showMessage)
    context.signals.error_occurred.connect(my_error_handler)
"""

from angstrompro.utils.qt_compat import QtCore, Signal


class AppSignals(QtCore.QObject):

    # -- Status / feedback --------------------------------------------------
    status_message  = Signal(str)        # short message → status bar
    error_occurred  = Signal(str, str)   # (title, detail) → error dialog or log panel

    # -- Config -------------------------------------------------------------
    config_changed  = Signal(str, str)   # (group, key) → modules that depend on config

    # -- Process registry ---------------------------------------------------
    processes_updated = Signal()         # emitted after load_user_processes()

    # -- Module lifecycle ---------------------------------------------------
    module_opened   = Signal(str)        # module_id → e.g. add tab to workbench
    module_closed   = Signal(str)        # module_id

    # Workspace signals live on WorkspaceManager (item_added, item_removed,
    # item_renamed, item_transferred, workspace_created, workspace_removed).