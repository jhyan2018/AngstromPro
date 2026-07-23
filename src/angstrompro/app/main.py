# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 11:34:24 2026

@author: jiahaoYan
"""

from __future__ import annotations

import logging
import sys

from angstrompro.utils.qt_compat import QtWidgets

log = logging.getLogger(__name__)
from angstrompro.core.configs.config_manager import ConfigManager
from angstrompro.app.context import AppContext
from angstrompro.gui.appearance import ThemeManager, IconManager
from angstrompro.utils.platform_utils import set_windows_app_id
from angstrompro.app.user_data_folder import (
    apply_pending_user_data_folder_for_new_runtime,
    is_user_data_folder_set,
)


def _install_exception_hooks() -> None:
    """Route unhandled exceptions in the main thread and worker threads to the log."""
    import threading

    def _main_excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    def _thread_excepthook(args):
        if args.exc_type is SystemExit:
            return
        thread_name = getattr(args.thread, "name", "?")
        log.error(
            "Unhandled exception in thread %r",
            thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_tb),
        )

    sys.excepthook = _main_excepthook
    threading.excepthook = _thread_excepthook


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

    log.info("No user data folder configured — opening setup dialog…")
    try:
        from angstrompro.gui.dialogs.user_data_folder_dialog import UserDataFolderDialog
        path = UserDataFolderDialog.run()
    except Exception as exc:
        log.exception("Setup dialog failed: %s", exc)
        return False

    if path is None:
        log.info("Setup cancelled — exiting.")
    return path is not None


# ---- Main entry ----
def main(external_namespace=None, start_event_loop=True):
    # 1
    set_windows_app_id("com.angstrompro.app")
    # Apply a queued root before any configuration, logging, QSettings, cache,
    # or module can open. In a repeated Spyder launch the runtime ID is
    # unchanged, so the active hosted session is never redirected.
    apply_pending_user_data_folder_for_new_runtime()

    # 2
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    if not start_event_loop:
        # Spyder owns the kernel's Qt event loop.  Keep it alive when the last
        # AngstromPro window is hidden, and reuse an existing hosted session
        # instead of rebuilding Qt/VisPy objects in the same process.
        app.setQuitOnLastWindowClosed(False)
        session = getattr(app, "_angstrompro_hosted_session", None)
        if session is not None:
            context, window = session
            try:
                for module in context.module_manager.list_instances():
                    if getattr(module, "_hosted_restore_visible", False):
                        module.show()
                window.show()
                window.raise_()
                window.activateWindow()
                if external_namespace is not None:
                    external_namespace["window"] = window
                return app, window
            except RuntimeError:
                # The host discarded the underlying C++ window; create a fresh
                # session rather than retaining an invalid wrapper.
                delattr(app, "_angstrompro_hosted_session")

    # 3 — ensure user data folder is configured before anything reads from it
    if not _ensure_user_data_folder(app):
        return 1   # user cancelled first-launch setup

    from angstrompro.app.user_data_folder import setup_file_logging
    setup_file_logging()
    _install_exception_hooks()

    # 4
    config = ConfigManager()

    # 5
    theme = ThemeManager(config.get_group("appearance"))
    theme.apply()

    # 6
    icons = IconManager(config.get_group("appearance"))

    # 7
    context = AppContext(
        config,
        theme,
        icons,
        hosted=not start_event_loop,
    )
    # stop worker threads before Qt destroys their QThread objects —
    # Qt6 aborts hard on a still-running thread at teardown
    app.aboutToQuit.connect(context.tasks.shutdown)

    # 8 — register all built-in modules
    context.module_manager.load_builtin()
    import angstrompro.gui.workbench.main_workbench  # noqa: F401
    window = context.module_manager.create("main_workbench", context)
    window.show()

    if not start_event_loop:
        app._angstrompro_hosted_session = (context, window)

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
