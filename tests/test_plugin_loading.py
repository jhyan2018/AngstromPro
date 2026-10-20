from __future__ import annotations

import importlib
import logging
import sys

import angstrompro.app.context as context_module
from angstrompro.app.context import AppContext, PluginLoadResult
from angstrompro.gui.widgets.log_panel import _format_record_text
from angstrompro.gui.widgets.preferences.widgets.plugin_list import PluginListWidget
from angstrompro.utils.qt_compat import QtWidgets


class _Config:
    def __init__(self, path_plugins):
        self._path_plugins = path_plugins

    def get(self, group, key, default=None):
        if (group, key) == ("plugins", "path_plugins"):
            return self._path_plugins
        return default


class _EntryPoint:
    def __init__(self, name, value, loader):
        self.name = name
        self.value = value
        self._loader = loader

    def load(self):
        return self._loader()


def _load_with(monkeypatch, path_plugins, entry_point_values, importer):
    context = AppContext.__new__(AppContext)
    context._config = _Config(path_plugins)
    context._plugin_load_results = []
    monkeypatch.setattr(importlib, "import_module", importer)
    monkeypatch.setattr(
        context_module,
        "entry_points",
        lambda *, group: entry_point_values,
    )
    context._load_plugins()
    return context


def test_plugin_load_results_retain_path_and_entry_point_failures(
    monkeypatch, caplog,
):
    def importer(name):
        raise RuntimeError(f"cannot import {name}")

    def fail_entry_point():
        raise ValueError("entry point dependency is missing")

    entry_point = _EntryPoint(
        "broken-installed", "broken_installed", fail_entry_point
    )
    with caplog.at_level(logging.ERROR):
        context = _load_with(
            monkeypatch,
            [{"path": "C:/plugins/src", "module": "broken_path_plugin"}],
            [entry_point],
            importer,
        )

    results = context.plugin_load_results
    assert [result.source for result in results] == ["path", "entry_point"]
    assert all(result.status == "failed" for result in results)
    assert "RuntimeError: cannot import broken_path_plugin" in results[0].traceback
    assert "ValueError: entry point dependency is missing" in results[1].traceback
    assert context.plugin_load_failures == results
    assert all(record.exc_info is not None for record in caplog.records)


def test_plugin_load_results_include_loaded_and_invalid_configuration(
    monkeypatch,
):
    loaded = []

    def importer(name):
        loaded.append(name)
        return object()

    entry_point = _EntryPoint(
        "installed", "installed_plugin", lambda: loaded.append("entry-point")
    )
    context = _load_with(
        monkeypatch,
        [
            {"path": "C:/plugins/src", "module": "working_path_plugin"},
            {"path": "C:/plugins/incomplete", "module": ""},
        ],
        [entry_point],
        importer,
    )

    assert loaded == ["working_path_plugin", "entry-point"]
    assert [result.status for result in context.plugin_load_results] == [
        "loaded", "failed", "loaded",
    ]
    invalid = context.plugin_load_results[1]
    assert "module name" in invalid.error


def test_plugin_discovery_failure_is_retained_without_aborting_startup(
    monkeypatch, caplog,
):
    context = AppContext.__new__(AppContext)
    context._config = _Config([])
    context._plugin_load_results = []

    def fail_discovery(*, group):
        raise RuntimeError(f"cannot inspect {group}")

    monkeypatch.setattr(context_module, "entry_points", fail_discovery)
    with caplog.at_level(logging.ERROR):
        context._load_plugins()

    failure, = context.plugin_load_failures
    assert failure.name == "Installed plugin discovery"
    assert "RuntimeError: cannot inspect angstrompro.plugins" in failure.traceback
    assert caplog.records[-1].exc_info is not None


def test_log_panel_record_text_includes_full_traceback():
    try:
        raise RuntimeError("plugin failed deeply")
    except RuntimeError:
        record = logging.getLogger("angstrompro.tests.plugin").makeRecord(
            "angstrompro.tests.plugin",
            logging.ERROR,
            __file__,
            1,
            "Failed to load plugin %s",
            ("example",),
            sys.exc_info(),
        )

    text = _format_record_text(record)
    assert "Failed to load plugin example" in text
    assert "Traceback (most recent call last)" in text
    assert "RuntimeError: plugin failed deeply" in text


def test_plugins_preferences_show_installed_failure_and_error():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    class _Context:
        plugin_load_results = (
            PluginLoadResult(
                source="entry_point",
                name="broken-plugin",
                target="broken_plugin",
                status="failed",
                error="No module named 'dependency'",
                traceback="Traceback...",
            ),
        )

    widget = PluginListWidget(context=_Context())
    item = widget._status_tree.topLevelItem(0)
    assert item.text(0) == "Installed"
    assert item.text(1) == "broken-plugin"
    assert item.text(2) == "Failed"
    assert item.text(3) == "No module named 'dependency'"
    assert item.toolTip(3) == "Traceback..."
    widget.close()
    app.processEvents()
