# -*- coding: utf-8 -*-
"""
Created on Fri Jun  5 04:19:39 2026

@author: jiahaoYan
"""

# qt_compat.py

import sys
import importlib.util


# ------------------------------------------------------------
# Module detection
# ------------------------------------------------------------

def module_exists(module_name):
    """
    Check whether a Python package/module is available,
    without importing it.

    Returns:
        True or False
    """
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def module_loaded(module_name):
    """
    Check whether a package/module has already been imported
    in the current Python process.
    """
    return any(
        name == module_name or name.startswith(module_name + ".")
        for name in sys.modules
    )


def choose_qt_binding():
    """
    Choose Qt binding.

    Rule:
    1. If a Qt binding is already loaded, use that one.
       This is important for Spyder/IPython/Jupyter.
    2. If none is loaded, prefer:
       PyQt6 → PyQt5 → PySide6 → PySide2
    """

    loaded_order = ["PyQt6", "PyQt5", "PySide6", "PySide2"]
    available_order = ["PyQt6", "PyQt5", "PySide6", "PySide2"]

    for binding in loaded_order:
        if module_loaded(binding):
            return binding

    for binding in available_order:
        if module_exists(binding):
            return binding

    raise ImportError(
        "No supported Qt binding found. "
        "Please install one of: PyQt6, PyQt5, PySide6, PySide2."
    )


QT_API = choose_qt_binding()


# ------------------------------------------------------------
# Import selected binding
# ------------------------------------------------------------

if QT_API == "PyQt6":
    from PyQt6 import QtCore, QtGui, QtWidgets

    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    Property = QtCore.pyqtProperty

    QT_VERSION_STR = QtCore.QT_VERSION_STR
    BINDING_VERSION_STR = QtCore.PYQT_VERSION_STR

    def exec_app(app):
        return app.exec()


elif QT_API == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets

    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    Property = QtCore.pyqtProperty

    QT_VERSION_STR = QtCore.QT_VERSION_STR
    BINDING_VERSION_STR = QtCore.PYQT_VERSION_STR

    def exec_app(app):
        return app.exec_()


elif QT_API == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets

    Signal = QtCore.Signal
    Slot = QtCore.Slot
    Property = QtCore.Property

    QT_VERSION_STR = QtCore.qVersion()
    BINDING_VERSION_STR = QtCore.__version__

    def exec_app(app):
        return app.exec()


elif QT_API == "PySide2":
    from PySide2 import QtCore, QtGui, QtWidgets

    Signal = QtCore.Signal
    Slot = QtCore.Slot
    Property = QtCore.Property

    QT_VERSION_STR = QtCore.qVersion()
    BINDING_VERSION_STR = QtCore.__version__

    def exec_app(app):
        return app.exec_()


# ------------------------------------------------------------
# Binding type helpers
# ------------------------------------------------------------

IS_QT6 = QT_API in ("PyQt6", "PySide6")
IS_QT5 = QT_API in ("PyQt5", "PySide2")
IS_PYQT = QT_API in ("PyQt5", "PyQt6")
IS_PYSIDE = QT_API in ("PySide2", "PySide6")


# ------------------------------------------------------------
# Common enum compatibility helpers
# ------------------------------------------------------------

if IS_QT6:
    AlignmentFlag = QtCore.Qt.AlignmentFlag
    Orientation = QtCore.Qt.Orientation
    MouseButton = QtCore.Qt.MouseButton
    KeyboardModifier = QtCore.Qt.KeyboardModifier
    WindowType = QtCore.Qt.WindowType

    AlignCenter = QtCore.Qt.AlignmentFlag.AlignCenter
    AlignLeft = QtCore.Qt.AlignmentFlag.AlignLeft
    AlignRight = QtCore.Qt.AlignmentFlag.AlignRight
    AlignTop = QtCore.Qt.AlignmentFlag.AlignTop
    AlignBottom = QtCore.Qt.AlignmentFlag.AlignBottom

    Horizontal = QtCore.Qt.Orientation.Horizontal
    Vertical = QtCore.Qt.Orientation.Vertical

    LeftButton = QtCore.Qt.MouseButton.LeftButton
    RightButton = QtCore.Qt.MouseButton.RightButton
    MiddleButton = QtCore.Qt.MouseButton.MiddleButton

    NoModifier = QtCore.Qt.KeyboardModifier.NoModifier
    ControlModifier = QtCore.Qt.KeyboardModifier.ControlModifier
    ShiftModifier = QtCore.Qt.KeyboardModifier.ShiftModifier
    AltModifier = QtCore.Qt.KeyboardModifier.AltModifier

else:
    AlignmentFlag = QtCore.Qt
    Orientation = QtCore.Qt
    MouseButton = QtCore.Qt
    KeyboardModifier = QtCore.Qt
    WindowType = QtCore.Qt

    AlignCenter = QtCore.Qt.AlignCenter
    AlignLeft = QtCore.Qt.AlignLeft
    AlignRight = QtCore.Qt.AlignRight
    AlignTop = QtCore.Qt.AlignTop
    AlignBottom = QtCore.Qt.AlignBottom

    Horizontal = QtCore.Qt.Horizontal
    Vertical = QtCore.Qt.Vertical

    LeftButton = QtCore.Qt.LeftButton
    RightButton = QtCore.Qt.RightButton
    MiddleButton = QtCore.Qt.MiddleButton

    NoModifier = QtCore.Qt.NoModifier
    ControlModifier = QtCore.Qt.ControlModifier
    ShiftModifier = QtCore.Qt.ShiftModifier
    AltModifier = QtCore.Qt.AltModifier


# ------------------------------------------------------------
# QFileDialog compatibility
# ------------------------------------------------------------

def get_open_file_name(*args, **kwargs):
    """
    Wrapper for QFileDialog.getOpenFileName.
    Returns:
        filename, selected_filter
    """
    return QtWidgets.QFileDialog.getOpenFileName(*args, **kwargs)


def get_open_file_names(*args, **kwargs):
    """
    Wrapper for QFileDialog.getOpenFileNames.
    Returns:
        filenames, selected_filter
    """
    return QtWidgets.QFileDialog.getOpenFileNames(*args, **kwargs)


def get_save_file_name(*args, **kwargs):
    """
    Wrapper for QFileDialog.getSaveFileName.
    Returns:
        filename, selected_filter
    """
    return QtWidgets.QFileDialog.getSaveFileName(*args, **kwargs)


# ------------------------------------------------------------
# QApplication helper
# ------------------------------------------------------------

def get_app():
    """
    Return existing QApplication instance, or create one if missing.
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    return app

def ipython_qt_event_loop_is_active():
    """
    Return True if running inside IPython/Spyder/Jupyter with
    the Qt event loop already enabled, e.g. by `%gui qt`.
    """
    try:
        shell = get_ipython()
    except NameError:
        return False

    if shell is None:
        return False

    active_loop = getattr(shell, "active_eventloop", None)

    return active_loop in ("qt", "qt5", "qt6")


def run_qt_app(app):
    """
    Run the Qt event loop only when needed.

    In Spyder/IPython with `%gui qt`, the Qt event loop is already
    integrated with the console, so we should NOT call app.exec_()
    or app.exec().

    In normal terminal execution, we must call app.exec_()/app.exec().
    """
    if ipython_qt_event_loop_is_active():
        return None

    return exec_app(app)



# ------------------------------------------------------------
# Debug helper
# ------------------------------------------------------------

def qt_info():
    """
    Return basic Qt binding information as a dictionary.
    """
    return {
        "QT_API": QT_API,
        "QT_VERSION_STR": QT_VERSION_STR,
        "BINDING_VERSION_STR": BINDING_VERSION_STR,
        "IS_QT6": IS_QT6,
        "IS_QT5": IS_QT5,
        "IS_PYQT": IS_PYQT,
        "IS_PYSIDE": IS_PYSIDE,
        "PYTHON_EXECUTABLE": sys.executable,
    }


def print_qt_info():
    """
    Print basic Qt binding information.
    """
    info = qt_info()
    for key, value in info.items():
        print(f"{key}: {value}")