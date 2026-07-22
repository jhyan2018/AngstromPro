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
    # PySide-style spellings — so QtCore.Signal works under every binding
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot
    QtCore.Property = QtCore.pyqtProperty
    
    Action = QtGui.QAction
    FileSystemModel = QtGui.QFileSystemModel

    QT_VERSION_STR = QtCore.QT_VERSION_STR
    BINDING_VERSION_STR = QtCore.PYQT_VERSION_STR

    def exec_app(app):
        return app.exec()


elif QT_API == "PyQt5":
    from PyQt5 import QtCore, QtGui, QtWidgets

    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    Property = QtCore.pyqtProperty
    # PySide-style spellings — so QtCore.Signal works under every binding
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot
    QtCore.Property = QtCore.pyqtProperty
    
    Action = QtWidgets.QAction
    FileSystemModel = QtWidgets.QFileSystemModel
    
    QT_VERSION_STR = QtCore.QT_VERSION_STR
    BINDING_VERSION_STR = QtCore.PYQT_VERSION_STR

    def exec_app(app):
        return app.exec_()


elif QT_API == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets

    Signal = QtCore.Signal
    Slot = QtCore.Slot
    Property = QtCore.Property
    
    Action = QtGui.QAction
    FileSystemModel = QtGui.QFileSystemModel

    QT_VERSION_STR = QtCore.qVersion()
    BINDING_VERSION_STR = QtCore.__version__

    def exec_app(app):
        return app.exec()


elif QT_API == "PySide2":
    from PySide2 import QtCore, QtGui, QtWidgets

    Signal = QtCore.Signal
    Slot = QtCore.Slot
    Property = QtCore.Property
    
    Action = QtWidgets.QAction
    FileSystemModel = QtWidgets.QFileSystemModel

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
    
    QIconNormal = QtGui.QIcon.Mode.Normal
    QIconDisabled = QtGui.QIcon.Mode.Disabled
    QIconActive = QtGui.QIcon.Mode.Active
    QIconSelected = QtGui.QIcon.Mode.Selected

    QIconOff = QtGui.QIcon.State.Off
    QIconOn = QtGui.QIcon.State.On

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
    
    QIconNormal = QtGui.QIcon.Normal
    QIconDisabled = QtGui.QIcon.Disabled
    QIconActive = QtGui.QIcon.Active
    QIconSelected = QtGui.QIcon.Selected

    QIconOff = QtGui.QIcon.Off
    QIconOn = QtGui.QIcon.On

# DockWidgetArea compatibility
if IS_QT6:
    LeftDockWidgetArea = QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
    RightDockWidgetArea = QtCore.Qt.DockWidgetArea.RightDockWidgetArea
    TopDockWidgetArea = QtCore.Qt.DockWidgetArea.TopDockWidgetArea
    BottomDockWidgetArea = QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
    AllDockWidgetAreas = QtCore.Qt.DockWidgetArea.AllDockWidgetAreas
    NoDockWidgetArea = QtCore.Qt.DockWidgetArea.NoDockWidgetArea
else:
    LeftDockWidgetArea = QtCore.Qt.LeftDockWidgetArea
    RightDockWidgetArea = QtCore.Qt.RightDockWidgetArea
    TopDockWidgetArea = QtCore.Qt.TopDockWidgetArea
    BottomDockWidgetArea = QtCore.Qt.BottomDockWidgetArea
    AllDockWidgetAreas = QtCore.Qt.AllDockWidgetAreas
    NoDockWidgetArea = QtCore.Qt.NoDockWidgetArea
    
# FocusPolicy and PenStyle compatibility
if IS_QT6:
    StrongFocus = QtCore.Qt.FocusPolicy.StrongFocus
    NoFocus = QtCore.Qt.FocusPolicy.NoFocus
    ClickFocus = QtCore.Qt.FocusPolicy.ClickFocus
    TabFocus = QtCore.Qt.FocusPolicy.TabFocus

    NoPen = QtCore.Qt.PenStyle.NoPen
    SolidLine = QtCore.Qt.PenStyle.SolidLine
    DashLine = QtCore.Qt.PenStyle.DashLine
    DotLine = QtCore.Qt.PenStyle.DotLine
else:
    StrongFocus = QtCore.Qt.StrongFocus
    NoFocus = QtCore.Qt.NoFocus
    ClickFocus = QtCore.Qt.ClickFocus
    TabFocus = QtCore.Qt.TabFocus

    NoPen = QtCore.Qt.NoPen
    SolidLine = QtCore.Qt.SolidLine
    DashLine = QtCore.Qt.DashLine
    DotLine = QtCore.Qt.DotLine
    
# ConnectionType compatibility
if IS_QT6:
    AutoConnection = QtCore.Qt.ConnectionType.AutoConnection
    DirectConnection = QtCore.Qt.ConnectionType.DirectConnection
    QueuedConnection = QtCore.Qt.ConnectionType.QueuedConnection
    BlockingQueuedConnection = QtCore.Qt.ConnectionType.BlockingQueuedConnection
    UniqueConnection = QtCore.Qt.ConnectionType.UniqueConnection
else:
    AutoConnection = QtCore.Qt.AutoConnection
    DirectConnection = QtCore.Qt.DirectConnection
    QueuedConnection = QtCore.Qt.QueuedConnection
    BlockingQueuedConnection = QtCore.Qt.BlockingQueuedConnection
    UniqueConnection = QtCore.Qt.UniqueConnection
    
# ScrollBarPolicy compatibility
if IS_QT6:
    ScrollBarAlwaysOn = QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn
    ScrollBarAlwaysOff = QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    ScrollBarAsNeeded = QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
else:
    ScrollBarAlwaysOn = QtCore.Qt.ScrollBarAlwaysOn
    ScrollBarAlwaysOff = QtCore.Qt.ScrollBarAlwaysOff
    ScrollBarAsNeeded = QtCore.Qt.ScrollBarAsNeeded
    
# WindowState compatibility
if IS_QT6:
    WindowState = QtCore.Qt.WindowState

    WindowNoState = QtCore.Qt.WindowState.WindowNoState
    WindowMinimized = QtCore.Qt.WindowState.WindowMinimized
    WindowMaximized = QtCore.Qt.WindowState.WindowMaximized
    WindowFullScreen = QtCore.Qt.WindowState.WindowFullScreen
    WindowActive = QtCore.Qt.WindowState.WindowActive

else:
    WindowState = QtCore.Qt

    WindowNoState = QtCore.Qt.WindowNoState
    WindowMinimized = QtCore.Qt.WindowMinimized
    WindowMaximized = QtCore.Qt.WindowMaximized
    WindowFullScreen = QtCore.Qt.WindowFullScreen
    WindowActive = QtCore.Qt.WindowActive

# QPainter RenderHint compatibility
if IS_QT6:
    RenderHint = QtGui.QPainter.RenderHint

    Antialiasing = QtGui.QPainter.RenderHint.Antialiasing
    TextAntialiasing = QtGui.QPainter.RenderHint.TextAntialiasing
    SmoothPixmapTransform = QtGui.QPainter.RenderHint.SmoothPixmapTransform

else:
    RenderHint = QtGui.QPainter

    Antialiasing = QtGui.QPainter.Antialiasing
    TextAntialiasing = QtGui.QPainter.TextAntialiasing
    SmoothPixmapTransform = QtGui.QPainter.SmoothPixmapTransform
    
# QDir Filter compatibility
if IS_QT6:
    QDirFilter = QtCore.QDir.Filter

    QDirAllEntries = QtCore.QDir.Filter.AllEntries
    QDirNoDotAndDotDot = QtCore.QDir.Filter.NoDotAndDotDot
    QDirFiles = QtCore.QDir.Filter.Files
    QDirDirs = QtCore.QDir.Filter.Dirs
    QDirNoFilter = QtCore.QDir.Filter.NoFilter

else:
    QDirFilter = QtCore.QDir

    QDirAllEntries = QtCore.QDir.AllEntries
    QDirNoDotAndDotDot = QtCore.QDir.NoDotAndDotDot
    QDirFiles = QtCore.QDir.Files
    QDirDirs = QtCore.QDir.Dirs
    QDirNoFilter = QtCore.QDir.NoFilter
    
# DateFormat compatibility
if IS_QT6:
    DateFormat = QtCore.Qt.DateFormat

    ISODate = QtCore.Qt.DateFormat.ISODate
    ISODateWithMs = QtCore.Qt.DateFormat.ISODateWithMs
    TextDate = QtCore.Qt.DateFormat.TextDate

else:
    DateFormat = QtCore.Qt

    ISODate = QtCore.Qt.ISODate
    ISODateWithMs = QtCore.Qt.ISODateWithMs
    TextDate = QtCore.Qt.TextDate
    
# AspectRatioMode compatibility
if IS_QT6:
    AspectRatioMode = QtCore.Qt.AspectRatioMode

    KeepAspectRatio = QtCore.Qt.AspectRatioMode.KeepAspectRatio
    KeepAspectRatioByExpanding = QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding
    IgnoreAspectRatio = QtCore.Qt.AspectRatioMode.IgnoreAspectRatio

else:
    AspectRatioMode = QtCore.Qt

    KeepAspectRatio = QtCore.Qt.KeepAspectRatio
    KeepAspectRatioByExpanding = QtCore.Qt.KeepAspectRatioByExpanding
    IgnoreAspectRatio = QtCore.Qt.IgnoreAspectRatio
    
# CheckState compatibility
if IS_QT6:
    CheckState = QtCore.Qt.CheckState

    Unchecked = QtCore.Qt.CheckState.Unchecked
    PartiallyChecked = QtCore.Qt.CheckState.PartiallyChecked
    Checked = QtCore.Qt.CheckState.Checked

else:
    CheckState = QtCore.Qt

    Unchecked = QtCore.Qt.Unchecked
    PartiallyChecked = QtCore.Qt.PartiallyChecked
    Checked = QtCore.Qt.Checked
    
    
# QMouseEvent position compatibility
def event_X(event):
    """
    Return mouse event x position.

    Qt5:
        event.x()

    Qt6:
        event.position().x()
    """
    if IS_QT6:
        return event.position().x()
    else:
        return event.x()


def event_Y(event):
    """
    Return mouse event y position.

    Qt5:
        event.y()

    Qt6:
        event.position().y()
    """
    if IS_QT6:
        return event.position().y()
    else:
        return event.y()


def event_POS(event):
    """
    Return mouse event position.

    Qt5:
        event.pos()

    Qt6:
        event.position().toPoint()

    Always returns QPoint because widget hit-testing and QGraphicsView mapping
    APIs use integer viewport coordinates under both Qt generations.
    """
    if IS_QT6:
        position = event.position()
        return position.toPoint() if hasattr(position, "toPoint") else position
    else:
        return event.pos()

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

def available_screen_geometry():
    """
    Return available geometry of the primary screen.
    Works for PyQt5/PyQt6/PySide2/PySide6.
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    if hasattr(QtWidgets.QApplication, "desktop"):
        return QtWidgets.QApplication.desktop().availableGeometry()
    else:
        return app.primaryScreen().availableGeometry()

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
