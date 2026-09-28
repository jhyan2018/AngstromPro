"""Per-instance destination selection, independent of shared attachments."""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar

import pytest

from angstrompro.app.app_signals import AppSignals
from angstrompro.core.data.annotation_data import PointSetData
from angstrompro.core.data.base import WorkspaceData
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import AModuleManager
from angstrompro.core.processes import ProcessRegistry, ProcessResult
from angstrompro.core.tasks.task_handle import TaskHandle
from angstrompro.core.workspaces import WorkspaceManager
from angstrompro.gui.dialogs.send_item_dialog import SendItemDialog
from angstrompro.utils.qt_compat import QtCore, QtWidgets, IS_QT6


@dataclass
class ExampleData(WorkspaceData):
    type_id: ClassVar[str] = "test.destination"
    name: str = ""


class Config:
    def get(self, group, key, default=None):
        return default

    def get_group(self, group):
        return {}


class GuiModule(AGuiModule):
    module_id = "destination_test"
    display_name = "Destination test"
    persist_window_layout = False

    def build_ui(self):
        self.setCentralWidget(QtWidgets.QWidget())

    def on_item_loaded(self, item):
        self.process_inputs = [item]


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def modules(qapp):
    context = SimpleNamespace(
        config=Config(),
        workspace_manager=WorkspaceManager(),
        module_manager=AModuleManager(),
        processes=ProcessRegistry(),
        signals=AppSignals(),
        tasks=object(),
    )
    first, second = GuiModule(context), GuiModule(context)
    context.module_manager._instances[GuiModule.module_id] = [first, second]
    shared = context.workspace_manager.create_shared_workspace("Analysis")
    for module in (first, second):
        context.workspace_manager.attach_module(module.instance_id, shared.workspace_id)
    yield first, second, shared, context
    for module in (first, second):
        module._dispose_module_workspaces()
        module.close()
        module.deleteLater()
    qapp.processEvents()


def test_radio_selection_is_independent_without_moving_or_deselecting_items(modules):
    first, second, shared, context = modules
    private = first.private_workspace
    item = private.add_item(ExampleData("input"))
    shared.add_item(ExampleData("shared_input"))
    first.process_inputs = [item]
    selected = first._ws_list.topLevelItem(0).child(0)
    first._ws_list.setCurrentItem(selected)

    assert first.active_workspace is first.workspace is shared
    first._workspace_destination_buttons[private.workspace_id].click()

    assert first.workspace is first.active_workspace is private
    assert second.workspace is shared
    assert first.shared_workspace is shared
    assert context.workspace_manager.attached_module_ids(shared.workspace_id) == [
        first.instance_id,
        second.instance_id,
    ]
    assert first._ws_list.currentItem() is selected
    assert first._selected_workspace_item() is item
    assert first.process_inputs == [item]
    assert first.accessible_workspaces() == [private, shared]
    assert private.list_items() == [item]
    assert shared.list_names() == ["shared_input"]
    assert (
        sum(b.isChecked() for b in first._workspace_destination_buttons.values()) == 1
    )

    # Signal-driven tree rebuilds and rename must keep the selected destination.
    shared.add_item(ExampleData("more"))
    context.workspace_manager.rename_shared_workspace(shared.workspace_id, "Renamed")
    assert first._workspace_destination_buttons[private.workspace_id].isChecked()
    assert "Renamed" in first._workspace_destination_buttons[shared.workspace_id].text()
    first.set_active_workspace(shared.workspace_id)
    assert first._workspace_destination_buttons[shared.workspace_id].isChecked()


def test_workspace_groups_expand_collapse_and_keep_state_across_refreshes(modules):
    first, _, shared, context = modules
    private = first.private_workspace
    private.add_item(ExampleData("private_item"))
    shared.add_item(ExampleData("shared_item"))
    private_group = first._ws_list.topLevelItem(0)
    shared_group = first._ws_list.topLevelItem(1)

    private_group.setExpanded(False)
    shared_group.setExpanded(False)
    shared.add_item(ExampleData("another_shared_item"))

    assert not first._ws_list.topLevelItem(0).isExpanded()
    assert not first._ws_list.topLevelItem(1).isExpanded()

    first._ws_list.topLevelItem(0).setExpanded(True)
    context.workspace_manager.rename_shared_workspace(
        shared.workspace_id, "Expanded-state test"
    )
    assert first._ws_list.topLevelItem(0).isExpanded()
    assert not first._ws_list.topLevelItem(1).isExpanded()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("font_size", [10, 16])
def test_workspace_headings_have_one_text_painter_under_app_stylesheet(
    modules, qapp, theme, font_size
):
    from angstrompro.gui.appearance.theme_manager import ThemeManager

    first, _, shared, _ = modules
    stylesheet = qapp.styleSheet()
    manager = ThemeManager({"font_family": "Segoe UI", "font_size": font_size})
    try:
        qapp.setStyleSheet(manager._stylesheet(theme))
        first.private_workspace.add_item(ExampleData("input"))
        first.show()
        qapp.processEvents()
        accessible_role = (
            QtCore.Qt.ItemDataRole.AccessibleTextRole
            if IS_QT6
            else QtCore.Qt.AccessibleTextRole
        )
        for index, workspace in enumerate((first.private_workspace, shared)):
            row = first._ws_list.topLevelItem(index)
            button = first._workspace_destination_buttons[workspace.workspace_id]
            assert row.text(0) == ""  # No second title beneath the widget.
            assert row.data(0, accessible_role) == button.text()
            assert first._ws_list.itemWidget(row, 0) is button
            assert (
                first._ws_list.visualItemRect(row).height()
                >= button.sizeHint().height()
            )
        first._ws_list.setCurrentItem(first._ws_list.topLevelItem(0))
        first._workspace_destination_buttons[
            first.private_workspace.workspace_id
        ].click()
        qapp.processEvents()
        assert first.active_workspace is first.private_workspace
        assert first._ws_list.topLevelItem(0).text(0) == ""
    finally:
        qapp.setStyleSheet(stylesheet)


def test_destination_validation_and_attachment_lifecycle(modules):
    first, second, shared, context = modules
    private = first.private_workspace
    manager = context.workspace_manager
    other = manager.create_shared_workspace("Other")
    for invalid in (
        other.workspace_id,
        second.private_workspace.workspace_id,
        "missing",
    ):
        with pytest.raises(ValueError, match="private or attached"):
            first.set_active_workspace(invalid)
        assert first.active_workspace is shared
    with pytest.raises(ValueError):
        first.workspace = other
    first.workspace = private
    manager.attach_module(first.instance_id, other.workspace_id)
    assert first.workspace is private
    first.set_active_workspace(other.workspace_id)
    manager.attach_module(first.instance_id, shared.workspace_id)
    assert first.workspace is shared
    manager.remove_shared_workspace(shared.workspace_id)
    assert first.workspace is private
    assert first.shared_workspace is None
    assert first._workspace_destination_buttons == {}
    private_group = first._ws_list.topLevelItem(0)
    assert private_group.text(0) == "Private workspace"
    assert private_group.data(0, (
        QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole
    )) == ("workspace", private.workspace_id)
    private_group.setExpanded(False)
    assert not private_group.isExpanded()


@pytest.mark.parametrize("default_send", [False, True])
@pytest.mark.parametrize("source_shared", [False, True])
@pytest.mark.parametrize("target_shared", [False, True])
def test_send_uses_selected_item_owner_and_receivers_active_destination(
    modules, monkeypatch, default_send, source_shared, target_shared
):
    sender, receiver, shared, context = modules
    source = shared if source_shared else sender.private_workspace
    destination = shared if target_shared else receiver.private_workspace
    receiver.set_active_workspace(destination.workspace_id)
    item = source.add_item(ExampleData("send_me"))
    monkeypatch.setattr(sender, "_selected_workspace_item", lambda: item)
    monkeypatch.setattr(sender, "_selected_item_workspace", lambda: source)
    sender._send_default_cb.blockSignals(True)
    sender._send_default_cb.setChecked(default_send)
    sender._send_default_cb.blockSignals(False)
    monkeypatch.setattr(
        context.module_manager, "get_default_targets", lambda _id: [receiver]
    )

    class Picker:
        selected_module = receiver

        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return True

    monkeypatch.setattr(
        "angstrompro.gui.dialogs.send_item_dialog.SendItemDialog", Picker
    )
    sender._on_send_item()
    received = destination.get_item("send_me")
    if destination is source:
        assert received is item  # No duplicate and no delete-after-send.
    else:
        assert received is not item
        assert received.payload is not item.payload
        assert not source.has_item("send_me")  # Existing move-like preference.
    assert receiver.shared_workspace is shared


def test_send_picker_shows_receivers_destination(modules):
    sender, receiver, shared, context = modules
    receiver.set_active_workspace(receiver.private_workspace.workspace_id)
    dialog = SendItemDialog(context, sender.instance_id, sender)
    assert "Destination: Private" in dialog._list.item(0).text()
    dialog.close()


@pytest.mark.parametrize("accepted", [False, True])
def test_data_browser_send_keeps_source_stable_across_destination_changes(
    modules, monkeypatch, accepted
):
    from angstrompro.gui.modules.data_browser.data_browser_module import (
        DataBrowserModule,
    )

    sender, receiver, shared, _ = modules
    receiver.set_active_workspace(receiver.private_workspace.workspace_id)
    original = sender.private_workspace.add_item(ExampleData("channel"))
    monkeypatch.setattr(
        sender,
        "_gallery",
        SimpleNamespace(
            gallery_model=lambda: SimpleNamespace(row_for_key=lambda _key: None)
        ),
        raising=False,
    )
    monkeypatch.setattr(
        sender,
        "_load_channel_payload",
        lambda *_args: ExampleData("channel"),
        raising=False,
    )

    class Picker:
        selected_module = receiver

        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            sender.set_active_workspace(sender.private_workspace.workspace_id)
            return accepted

    monkeypatch.setattr(
        "angstrompro.gui.dialogs.send_item_dialog.SendItemDialog", Picker
    )
    DataBrowserModule._on_send_card(sender, ("example.uds", "channel"))
    assert sender.private_workspace.get_item("channel") is original
    assert not shared.has_item("channel")
    assert receiver.private_workspace.has_item("channel") == accepted


def test_archive_dialog_defaults_to_active_private_workspace(modules, monkeypatch):
    first, _, shared, _ = modules
    first.set_active_workspace(first.private_workspace.workspace_id)

    def choose(_parent, _title, _label, choices, index, _editable):
        assert index == 1
        assert choices[index].endswith("(active destination)")
        assert choices[0] == f"Shared — {shared.label}"
        return choices[index], True

    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", choose)
    assert first._choose_workspace_archive_target("Open") is first.private_workspace


@pytest.mark.parametrize("initial_shared", [False, True])
def test_file_open_captures_selected_destination(modules, monkeypatch, initial_shared):
    first, _, shared, _ = modules
    destination = shared if initial_shared else first.private_workspace
    other = first.private_workspace if initial_shared else shared
    first.set_active_workspace(destination.workspace_id)

    def choose(*args):
        first.set_active_workspace(other.workspace_id)
        return "example.uds", ""

    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", choose)
    monkeypatch.setattr("angstrompro.io.angstrom_io._is_hdf5", lambda _path: True)
    monkeypatch.setattr("angstrompro.io.load_item", lambda _path: ExampleData("opened"))
    first._on_file_open()
    assert destination.has_item("opened")
    assert not other.has_item("opened")
    assert first.active_workspace is other


def fake_process_runner(module, context):
    handles = []

    def run(**kwargs):
        handle = TaskHandle(f"task_{len(handles)}")
        handles.append(handle)
        return handle

    context.processes = SimpleNamespace(
        get=lambda _name: SimpleNamespace(label="Example")
    )
    module.process_runner = SimpleNamespace(run=run)
    return handles


@pytest.mark.parametrize("custom_callback", [False, True])
@pytest.mark.parametrize("detach", [False, True])
def test_in_flight_process_keeps_destination_and_input_annotation_owner(
    modules, custom_callback, detach
):
    first, _, shared, context = modules
    private = first.private_workspace
    source = private.add_item(ExampleData("source"), alias="sample")
    handles = fake_process_runner(first, context)
    callback_destinations = []

    def add_result(task_id, result):
        callback_destinations.append((first.workspace, first.active_workspace))
        first.workspace.add_item(result.data)

    handle = first.submit_process(
        "example", [source], on_result=add_result if custom_callback else None
    )
    if detach:
        context.workspace_manager.detach_module(first.instance_id)
    else:
        first.set_active_workspace(private.workspace_id)
    peaks = PointSetData()
    result = ProcessResult(
        data=ExampleData("source_result"),
        annotations={"peaks": peaks},
        values={"quality": 0.99},
    )
    handle.result.emit(handle.task_id, result)
    assert handles == [handle]
    assert shared.get_item("source_result").alias == "sample_result"
    assert not private.has_item("source_result")
    assert first.active_workspace is first.workspace is private
    assert source.annotations["peaks"] is peaks
    assert source.metadata["process_results"][0]["values"] == {"quality": 0.99}
    if custom_callback:
        assert callback_destinations == [(shared, private)]


def test_concurrent_processes_keep_independent_destinations(modules):
    first, _, shared, context = modules
    fake_process_runner(first, context)
    shared_job = first.submit_process("example", [])
    first.set_active_workspace(first.private_workspace.workspace_id)
    private_job = first.submit_process("example", [])
    first.set_active_workspace(shared.workspace_id)
    private_job.result.emit(private_job.task_id, ExampleData("private_result"))
    shared_job.result.emit(shared_job.task_id, ExampleData("shared_result"))
    assert first.private_workspace.list_names() == ["private_result"]
    assert shared.list_names() == ["shared_result"]
    assert first.workspace is first.active_workspace is shared


def test_result_scope_is_restored_after_callback_error(modules):
    first, _, shared, _ = modules
    first.set_active_workspace(first.private_workspace.workspace_id)

    def fail(*args):
        assert first.workspace is shared
        raise RuntimeError("callback error")

    with pytest.raises(RuntimeError, match="callback error"):
        first._dispatch_process_result("task", None, fail, [], output_workspace=shared)
    assert first.workspace is first.active_workspace is first.private_workspace


def test_removed_destination_is_reported_without_silent_rerouting(modules, monkeypatch):
    first, _, shared, context = modules
    fake_process_runner(first, context)
    handle = first.submit_process("example", [])
    context.workspace_manager.remove_shared_workspace(shared.workspace_id)
    warnings = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", lambda *args: warnings.append(args[2])
    )
    handle.result.emit(handle.task_id, ExampleData("result"))
    assert warnings and "was removed" in warnings[0]
    assert first.private_workspace.count() == shared.count() == 0
