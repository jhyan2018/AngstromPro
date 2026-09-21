"""Cross-platform file-manager reveal behavior."""

from __future__ import annotations

from pathlib import Path

from angstrompro.gui.utils import file_manager


def _file(tmp_path: Path) -> Path:
    path = tmp_path / "data file.3ds"
    path.write_bytes(b"test")
    return path


def test_windows_reveals_and_selects_file(tmp_path, monkeypatch):
    path = _file(tmp_path)
    calls = []
    monkeypatch.setattr(
        file_manager, "_start_detached",
        lambda program, arguments: calls.append((program, arguments)) or True,
    )
    monkeypatch.setattr(
        file_manager, "_open_directory",
        lambda _path: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
    )

    assert file_manager.show_in_file_manager(path, platform="win32")
    assert calls == [("explorer.exe", ["/select,", str(path)])]


def test_macos_reveals_and_selects_file(tmp_path, monkeypatch):
    path = _file(tmp_path)
    calls = []
    monkeypatch.setattr(
        file_manager, "_start_detached",
        lambda program, arguments: calls.append((program, arguments)) or True,
    )

    assert file_manager.show_in_file_manager(path, platform="darwin")
    assert calls == [("open", ["-R", str(path)])]


def test_linux_uses_filemanager1_with_encoded_url(tmp_path, monkeypatch):
    path = _file(tmp_path)
    urls = []
    monkeypatch.setattr(
        file_manager, "_show_items_via_dbus",
        lambda url: urls.append(url) or True,
    )

    assert file_manager.show_in_file_manager(path, platform="linux")
    assert urls == [path.as_uri()]


def test_reveal_failure_opens_parent_directory(tmp_path, monkeypatch):
    path = _file(tmp_path)
    opened = []
    monkeypatch.setattr(file_manager, "_show_items_via_dbus", lambda _url: False)
    monkeypatch.setattr(
        file_manager, "_open_directory",
        lambda folder: opened.append(folder) or True,
    )

    assert file_manager.show_in_file_manager(path, platform="linux")
    assert opened == [path.parent]


def test_missing_file_is_not_opened(tmp_path, monkeypatch):
    monkeypatch.setattr(
        file_manager, "_open_directory",
        lambda _path: (_ for _ in ()).throw(AssertionError("unexpected open")),
    )
    assert not file_manager.show_in_file_manager(
        tmp_path / "missing.3ds", platform="linux")
