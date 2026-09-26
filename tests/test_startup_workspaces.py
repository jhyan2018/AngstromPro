"""Startup slots are configuration identities, never live instance suffixes."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from angstrompro.core.modules.a_module_manager import AModuleManager
from angstrompro.core.modules.module_mixin import ModuleMixin
from angstrompro.core.modules.startup_setup import (
    build_startup_plan,
    StartupWorkspaceSetup,
)
from angstrompro.core.workspaces import WorkspaceManager
from angstrompro.gui.widgets.preferences import PreferencesPanel
from angstrompro.gui.workbench.main_workbench import MainWorkbench
from angstrompro.utils.qt_compat import QtWidgets


class Viewer(ModuleMixin):
    module_id = "image_stack_viewer"
    display_name = "Image Stack Viewer"

    def __init__(self, context, parent=None):
        self._init_module(context)


class CurveViewer(Viewer):
    module_id = "curve_stack_viewer"
    display_name = "Curve Stack Viewer"


class Browser(Viewer):
    module_id = "data_browser"
    display_name = "Data Browser"
    max_instances = 1


class PluginStudio(Viewer):
    module_id = "example_plugin.workflow_studio"
    display_name = "Workflow Studio"


REGISTERED = {
    cls.module_id: cls for cls in (Viewer, CurveViewer, Browser, PluginStudio)
}
MODULES = [
    {"module_id": Browser.module_id, "count": 1},
    {"module_id": Viewer.module_id, "count": 2},
    {"module_id": CurveViewer.module_id, "count": 1},
    {"module_id": PluginStudio.module_id, "count": 1},
]


def binding(mid=Viewer.module_id, number=1, destination="shared"):
    return {"module_id": mid, "instance": number, "active_destination": destination}


WORKSPACES = [
    {
        "name": "Analysis",
        "attachments": [
            binding(number=2, destination="private"),
            binding(PluginStudio.module_id),
        ],
    },
    {"name": "Comparison", "attachments": [binding()]},
]


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class Config:
    def __init__(self):
        self.data = {
            "app": {
                "startup_modules": deepcopy(MODULES),
                "startup_workspaces": deepcopy(WORKSPACES),
            }
        }

    def get(self, group, key, default=None):
        return deepcopy(self.data.get(group, {}).get(key, default))


@pytest.fixture
def context(qapp, monkeypatch):
    manager = AModuleManager()
    manager._modules = dict(REGISTERED)
    monkeypatch.setattr(manager, "_snapshot", lambda: None)
    context = SimpleNamespace(
        config=Config(),
        module_manager=manager,
        workspace_manager=WorkspaceManager(),
        tasks=object(),
        processes=object(),
    )
    yield context
    for instance in manager.list_instances():
        instance._dispose_module_workspaces()


def test_plan_uses_explicit_startup_slots_and_preserves_config():
    before = deepcopy((MODULES, WORKSPACES))
    plan = build_startup_plan(MODULES, WORKSPACES, REGISTERED)
    assert not plan.errors
    assert plan.workspaces == ["Analysis", "Comparison"]
    assert plan.attachments[Viewer.module_id, 2] == ("Analysis", "private")
    assert plan.attachments[Viewer.module_id, 1] == ("Comparison", "shared")
    assert (MODULES, WORKSPACES) == before


@pytest.mark.parametrize(
    "modules,workspaces,message",
    [
        (
            [{"module_id": Viewer.module_id, "count": 1}],
            WORKSPACES,
            "exceeds startup count 1",
        ),
        ([], WORKSPACES, "removed from startup or unavailable"),
        (
            [{"module_id": Viewer.module_id, "count": 0}],
            WORKSPACES,
            "exceeds startup count 0",
        ),
        (MODULES, [{"name": "Same"}, {"name": " same "}], "name is already used"),
        (MODULES, [{"name": " "}], "enter a name"),
        (
            MODULES,
            [{"name": "A", "attachments": [binding(), binding()]}],
            "more than once",
        ),
        (
            MODULES,
            [
                {"name": "A", "attachments": [binding()]},
                {"name": "B", "attachments": [binding()]},
            ],
            "more than once",
        ),
        (
            MODULES,
            [{"name": "A", "attachments": [binding(destination="unknown")]}],
            "Private or Shared",
        ),
        ([{"module_id": "missing", "count": 1}], [], "module is unavailable"),
        ([{"module_id": Browser.module_id, "count": 2}], [], "between 0 and 1"),
        ([{"module_id": Viewer.module_id, "count": True}], [], "startup count"),
        ([{"module_id": Viewer.module_id, "count": "two"}], [], "startup count"),
        ([MODULES[1], MODULES[1]], [], "duplicate startup module"),
        (MODULES, [{"name": "A", "attachments": [binding(number=True)]}], "is invalid"),
        (MODULES, [{"name": "A", "attachments": [binding(number="2")]}], "is invalid"),
        (MODULES, [None], "enter a name"),
        (MODULES, [{"name": "A", "attachments": None}], "must be a list"),
        (MODULES, [{"name": "A", "attachments": [None]}], "invalid attachment"),
    ],
)
def test_invalid_setup_reports_issues_without_mutation(modules, workspaces, message):
    before = deepcopy((modules, workspaces))
    plan = build_startup_plan(modules, workspaces, REGISTERED)
    assert any(message in error for error in plan.errors)
    assert (modules, workspaces) == before


def test_duplicate_attachment_never_uses_first_or_last_wins():
    plan = build_startup_plan(
        MODULES,
        [
            {"name": "A", "attachments": [binding()]},
            {"name": "B", "attachments": [binding()]},
        ],
        REGISTERED,
    )
    assert (Viewer.module_id, 1) not in plan.attachments
    assert plan.errors


def test_runtime_builds_plugin_and_viewer_bindings_without_saving_session_changes(
    context, monkeypatch
):
    monkeypatch.setitem(ModuleMixin._instance_counters, Viewer.module_id, 40)
    before = deepcopy(context.config.data)
    plan = build_startup_plan(MODULES, WORKSPACES, REGISTERED)
    errors = []
    setup = StartupWorkspaceSetup(context, plan, errors.append)
    setup.prepare()
    created = {slot: setup.create_slot(slot) for slot in plan.slots}
    first = created[Viewer.module_id, 1]
    second = created[Viewer.module_id, 2]
    studio = created[PluginStudio.module_id, 1]
    assert first.instance_id.endswith("_41")
    assert second.instance_id.endswith("_42")
    assert first.shared_workspace.label == "Comparison"
    assert first.active_workspace is first.shared_workspace
    assert second.shared_workspace is studio.shared_workspace
    assert second.shared_workspace.label == "Analysis"
    assert second.active_workspace is second.private_workspace
    assert studio.active_workspace is studio.shared_workspace
    assert created[CurveViewer.module_id, 1].shared_workspace is None
    assert not errors
    manager = context.workspace_manager
    manager.detach_module(first.instance_id)
    manager.remove_shared_workspace(setup.workspaces["Analysis"].workspace_id)
    new = manager.create_shared_workspace("Runtime only")
    manager.attach_module(second.instance_id, new.workspace_id)
    assert context.config.data == before


def test_failed_first_instance_does_not_shift_second_slot_attachment(
    context, monkeypatch
):
    plan = build_startup_plan(
        [MODULES[1]], [{"name": "A", "attachments": [binding(number=2)]}], REGISTERED
    )
    errors = []
    setup = StartupWorkspaceSetup(context, plan, errors.append)
    setup.prepare()
    create = context.module_manager.create
    calls = []

    def fail_once(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError("construction failed")
        return create(*args, **kwargs)

    monkeypatch.setattr(context.module_manager, "create", fail_once)
    assert setup.create_slot(plan.slots[0]) is None
    second = setup.create_slot(plan.slots[1])
    assert second.shared_workspace is setup.workspaces["A"]
    assert len(errors) == 1


def test_reused_singleton_is_not_reattached(context):
    existing = context.module_manager.create(Browser.module_id, context)
    workspace = context.workspace_manager.create_shared_workspace("Existing")
    context.workspace_manager.attach_module(
        existing.instance_id, workspace.workspace_id
    )
    plan = build_startup_plan(
        [MODULES[0]],
        [{"name": "Startup", "attachments": [binding(Browser.module_id)]}],
        REGISTERED,
    )
    errors = []
    setup = StartupWorkspaceSetup(context, plan, errors.append)
    setup.prepare()
    assert setup.create_slot(plan.slots[0]) is existing
    assert existing.shared_workspace is workspace
    assert "reused" in errors[0]


def test_workspace_creation_conflict_never_attaches_to_unrelated_existing_workspace(
    context,
):
    existing = context.workspace_manager.create_shared_workspace("Analysis")
    errors = []
    plan = build_startup_plan(MODULES, WORKSPACES, REGISTERED)
    setup = StartupWorkspaceSetup(context, plan, errors.append)
    setup.prepare()
    studio = setup.create_slot((PluginStudio.module_id, 1))
    assert studio.shared_workspace is None
    assert existing.count() == 0
    assert len(errors) == 2


@pytest.fixture
def panel(context, qapp):
    applied, saved = [], []
    startup = next(
        section
        for section in MainWorkbench._global_preferences_schema
        if section.title == "Startup"
    )
    panel = PreferencesPanel(
        "Startup test",
        [startup],
        context.config.data,
        on_apply=applied.append,
        on_save_as_default=saved.append,
        context=context,
    )
    editors = dict(panel._controls)
    yield (
        panel,
        editors["app.startup_modules"],
        editors["app.startup_workspaces"],
        applied,
        saved,
    )
    panel.close()
    panel.deleteLater()
    qapp.processEvents()


def test_preferences_block_apply_and_save_after_count_reduction(panel, monkeypatch):
    widget, modules, workspaces, applied, saved = panel
    assert workspaces.get_value() == WORKSPACES
    row = next(
        r for r in modules._rows if r.get_value()["module_id"] == Viewer.module_id
    )
    row._count_spin.setValue(1)
    assert "exceeds startup count 1" in workspaces._warning.text()
    attachment = workspaces._cards[0].rows[0]
    assert attachment.instance.currentData() == 2
    assert "invalid" in attachment.instance.currentText()
    assert (
        not attachment.instance.model()
        .item(attachment.instance.currentIndex())
        .isEnabled()
    )
    warnings = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", lambda *args: warnings.append(args[2])
    )
    assert widget._on_apply() is False
    widget._on_save_as_default()
    assert not applied and not saved
    assert len(warnings) == 2
    # Correcting the count restores validity without touching the attachment.
    row._count_spin.setValue(2)
    assert not workspaces.validation_errors()
    widget._on_save_as_default()
    assert len(applied) == len(saved) == 1
    assert saved[0]["app"]["startup_workspaces"] == WORKSPACES


def test_removing_startup_module_preserves_invalid_binding_until_user_removes_it(panel):
    widget, modules, workspaces, applied, saved = panel
    row = next(
        r for r in modules._rows if r.get_value()["module_id"] == PluginStudio.module_id
    )
    modules._remove_row(row)
    attachment = workspaces._cards[0].rows[1]
    assert attachment.module.currentData() == PluginStudio.module_id
    assert "removed from startup or unavailable" in workspaces._warning.text()
    workspaces._cards[0].remove_attachment(attachment)
    assert not workspaces.validation_errors()
    assert widget._on_apply() is True


def test_missing_plugin_remains_visible_without_switching_to_another_module(
    panel, context
):
    widget, modules, workspaces, applied, saved = panel
    del context.module_manager._modules[PluginStudio.module_id]
    modules.set_value(MODULES)
    row = next(
        r for r in modules._rows if r.get_value()["module_id"] == PluginStudio.module_id
    )
    assert "unavailable" in row._combo.currentText()
    assert workspaces._cards[0].rows[1].module.currentData() == PluginStudio.module_id
    assert workspaces.validation_errors()


def test_instance_options_follow_count_and_do_not_offer_out_of_range_values(panel):
    widget, modules, workspaces, applied, saved = panel
    row = workspaces._cards[0].rows[0]
    assert [row.instance.itemData(i) for i in range(row.instance.count())] == [1, 2]
    module = next(
        r for r in modules._rows if r.get_value()["module_id"] == Viewer.module_id
    )
    module._count_spin.setValue(3)
    assert [row.instance.itemData(i) for i in range(row.instance.count())] == [1, 2, 3]
    assert row.instance.currentData() == 2
    module._count_spin.setValue(0)
    assert row.instance.currentData() == 2
    assert "exceeds startup count 0" in workspaces._warning.text()


def test_draft_changes_do_not_mutate_live_workspace_manager_or_config(panel, context):
    widget, modules, workspaces, applied, saved = panel
    before = deepcopy(context.config.data)
    workspaces.add_workspace().add_attachment()
    workspaces._cards[0].name.setText("Changed draft")
    assert context.workspace_manager.count() == 0
    assert context.config.data == before
    assert not applied and not saved


def test_apply_validates_count_still_being_edited(panel, monkeypatch):
    widget, modules, workspaces, applied, saved = panel
    row = next(
        r for r in modules._rows if r.get_value()["module_id"] == Viewer.module_id
    )
    row._count_spin.setKeyboardTracking(False)
    row._count_spin.lineEdit().setText("1")
    warnings = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", lambda *args: warnings.append(args[2])
    )
    assert widget._on_apply() is False
    assert "exceeds startup count 1" in warnings[0]
    assert not applied


def test_reset_removes_workspace_setup_without_touching_runtime(panel, context):
    from angstrompro.core.configs.defaults import DEFAULTS

    widget, modules, workspaces, applied, saved = panel
    current = context.workspace_manager.create_shared_workspace("Live")
    defaults = {"app": deepcopy(DEFAULTS["app"])}
    widget._on_reset_cb = lambda: defaults
    widget._on_reset()
    assert workspaces.get_value() == []
    assert not workspaces.validation_errors()
    assert context.workspace_manager.list_shared_workspaces() == [current]
    assert not saved


def test_config_roundtrip_and_empty_defaults(tmp_path, monkeypatch):
    from angstrompro.core.configs import config_manager

    monkeypatch.setattr(
        config_manager, "get_config_file", lambda: tmp_path / "config.json"
    )
    cfg = config_manager.ConfigManager()
    assert cfg.get("app", "startup_workspaces") == []
    cfg.set("app", "startup_modules", MODULES)
    cfg.set("app", "startup_workspaces", WORKSPACES)
    cfg.save_defaults()
    reloaded = config_manager.ConfigManager()
    assert reloaded.get("app", "startup_workspaces") == WORKSPACES
    assert reloaded.get("app", "startup_modules") == MODULES


def test_live_startup_queue_creates_workspaces_first_and_can_be_cancelled(
    context, monkeypatch
):
    from angstrompro.gui.widgets.live_modules_panel import LiveModulesPanel

    queued = []
    monkeypatch.setattr(
        "angstrompro.gui.widgets.live_modules_panel.QtCore.QTimer.singleShot",
        lambda _delay, callback: queued.append(callback),
    )
    panel = SimpleNamespace(_context=context, _startup_cancelled=False)
    panel._launch_next_startup_module = (
        lambda: LiveModulesPanel._launch_next_startup_module(panel)
    )
    LiveModulesPanel._launch_startup_modules(panel)
    assert len(context.workspace_manager.list_shared_workspaces()) == 2
    assert context.module_manager.instance_count() == 1
    LiveModulesPanel.cancel_startup_launch(panel)
    for callback in queued:
        callback()
    assert context.module_manager.instance_count() == 1
