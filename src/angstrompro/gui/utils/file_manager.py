"""Reveal local files in the platform file manager."""

from __future__ import annotations

from pathlib import Path
import sys

from angstrompro.utils.qt_compat import QtCore, QtGui, IS_QT6


def _started(result) -> bool:
    """Normalise QProcess.startDetached across Qt bindings."""
    return bool(result[0] if isinstance(result, tuple) else result)


def _start_detached(program: str, arguments: list[str]) -> bool:
    return _started(QtCore.QProcess.startDetached(program, arguments))


def _open_directory(path: Path) -> bool:
    return bool(QtGui.QDesktopServices.openUrl(
        QtCore.QUrl.fromLocalFile(str(path))))


def _show_items_via_dbus(file_url: str) -> bool:
    """Use the freedesktop FileManager1 interface when it is available."""
    executable = QtCore.QStandardPaths.findExecutable("dbus-send")
    if not executable:
        return False
    process = QtCore.QProcess()
    process.start(executable, [
        "--session",
        "--print-reply",
        "--dest=org.freedesktop.FileManager1",
        "/org/freedesktop/FileManager1",
        "org.freedesktop.FileManager1.ShowItems",
        f"array:string:{file_url}",
        "string:",
    ])
    if not process.waitForStarted(500):
        return False
    if not process.waitForFinished(1000):
        process.kill()
        process.waitForFinished(100)
        return False
    normal_exit = (QtCore.QProcess.ExitStatus.NormalExit if IS_QT6
                   else QtCore.QProcess.NormalExit)
    return process.exitStatus() == normal_exit and process.exitCode() == 0


def show_in_file_manager(file_path: str | Path,
                         *, platform: str | None = None) -> bool:
    """Reveal *file_path*, selecting it where the platform supports that.

    Explorer and Finder have direct reveal commands. Linux first uses the
    standard FileManager1 D-Bus interface and falls back to opening the parent
    directory. The parent-folder fallback is also used if a reveal command
    cannot be started.
    """
    path = Path(file_path).absolute()
    if not path.exists():
        return False

    platform = platform or sys.platform
    native_path = QtCore.QDir.toNativeSeparators(str(path))
    revealed = False
    if platform.startswith("win"):
        revealed = _start_detached("explorer.exe", ["/select,", native_path])
    elif platform == "darwin":
        revealed = _start_detached("open", ["-R", str(path)])
    else:
        url = QtCore.QUrl.fromLocalFile(str(path))
        file_url = bytes(url.toEncoded()).decode("ascii")
        revealed = _show_items_via_dbus(file_url)

    if revealed:
        return True
    return _open_directory(path.parent)
