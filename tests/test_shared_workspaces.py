from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

from angstrompro.core.data.base import WorkspaceData
from angstrompro.core.modules.module_mixin import ModuleMixin
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.workspaces.workspace_manager import WorkspaceManager
from angstrompro.io.workspace_io import load_workspace, save_workspace


@dataclass
class ExampleData(WorkspaceData):
    type_id: ClassVar[str] = "test.shared_workspace"
    name: str = ""
    value: int = 0


class ExampleModule(ModuleMixin):
    module_id = "test_shared_module"
    display_name = "Shared workspace test module"


def _module_context(manager: WorkspaceManager):
    return SimpleNamespace(
        workspace_manager=manager,
        tasks=object(),
        processes=object(),
    )


def test_shared_workspaces_are_app_owned_and_unlimited() -> None:
    manager = WorkspaceManager()
    first = manager.create_shared_workspace("Experiment A")
    second = manager.create_shared_workspace("Experiment B")

    assert first.is_shared and second.is_shared
    assert first.owner_id is None and second.owner_id is None
    assert first.workspace_id != second.workspace_id
    assert manager.list_shared_workspaces() == [first, second]


def test_module_keeps_private_workspace_and_shared_workspace_takes_output() -> None:
    manager = WorkspaceManager()
    module = ExampleModule()
    module._init_module(_module_context(manager))
    private = module.private_workspace
    private.add_item(ExampleData(name="private_item", value=1))

    shared = manager.create_shared_workspace("Analysis")
    manager.attach_module(module.instance_id, shared.workspace_id)

    assert module.private_workspace is private
    assert module.shared_workspace is shared
    assert module.workspace is shared
    assert module.accessible_workspaces() == [private, shared]

    module.workspace.add_item(ExampleData(name="new_result", value=2))
    assert shared.has_item("new_result")
    assert private.has_item("private_item")
    assert not private.has_item("new_result")

    manager.detach_module(module.instance_id)
    assert module.shared_workspace is None
    assert module.workspace is private


def test_module_can_be_reassigned_but_only_to_one_shared_workspace() -> None:
    manager = WorkspaceManager()
    module = ExampleModule()
    module._init_module(_module_context(manager))
    first = manager.create_shared_workspace("First")
    second = manager.create_shared_workspace("Second")

    manager.attach_module(module.instance_id, first.workspace_id)
    manager.attach_module(module.instance_id, second.workspace_id)

    assert manager.shared_workspace_for_module(module.instance_id) is second
    assert manager.attached_module_ids(first.workspace_id) == []
    assert manager.attached_module_ids(second.workspace_id) == [module.instance_id]
    assert module.workspace is second


def test_deleting_shared_workspace_returns_modules_to_private() -> None:
    manager = WorkspaceManager()
    module = ExampleModule()
    module._init_module(_module_context(manager))
    private = module.private_workspace
    shared = manager.create_shared_workspace("Temporary")
    manager.attach_module(module.instance_id, shared.workspace_id)

    manager.remove_shared_workspace(shared.workspace_id)

    assert module.workspace is private
    assert module.shared_workspace is None
    assert manager.list_shared_workspaces() == []


def test_transfer_copies_payload_and_item_metadata() -> None:
    manager = WorkspaceManager()
    source = manager.create_workspace("source")
    destination = manager.create_workspace("destination")
    original = source.add_item(
        ExampleData(name="result", value=7),
        alias="important",
    )

    copied = manager.transfer_item(
        source.workspace_id,
        destination.workspace_id,
        original.name,
        new_name="result_copy",
    )

    assert copied.item_id != original.item_id
    assert copied.alias == "important"
    assert copied.payload is not original.payload
    assert copied.name == "result_copy"
    assert original.name == "result"


def test_shared_workspace_archive_has_no_module_owner(tmp_path: Path) -> None:
    manager = WorkspaceManager()
    shared = manager.create_shared_workspace("Shared experiment")
    path = tmp_path / "shared.apws"

    save_workspace(path, shared)
    archive = load_workspace(path)

    assert archive.label == "Shared experiment"
    assert archive.owner_id == ""


def test_attached_module_archive_target_defaults_to_shared(monkeypatch) -> None:
    manager = WorkspaceManager()
    private = manager.create_workspace("module", "Private")
    shared = manager.create_shared_workspace("Shared")
    module = SimpleNamespace(
        private_workspace=private,
        shared_workspace=shared,
    )

    monkeypatch.setattr(
        "angstrompro.core.modules.a_gui_module.QtWidgets.QInputDialog.getItem",
        lambda *_args: ("Shared — Shared (active output)", True),
    )
    assert AGuiModule._choose_workspace_archive_target(
        module, "Save") is shared

    monkeypatch.setattr(
        "angstrompro.core.modules.a_gui_module.QtWidgets.QInputDialog.getItem",
        lambda *_args: ("Private — Private", True),
    )
    assert AGuiModule._choose_workspace_archive_target(
        module, "Save") is private
