from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar

from angstrompro.core.data.base import WorkspaceData
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.workspaces.workspace import Workspace


@dataclass
class ExampleData(WorkspaceData):
    type_id: ClassVar[str] = "test.process_alias"
    name: str = ""


def test_derived_process_alias_requires_safe_name_relationship() -> None:
    workspace = Workspace("source")
    primary = workspace.add_item(
        ExampleData(name="very_long_source_name"), alias="sample")

    assert AGuiModule._derived_process_alias(
        primary, "very_long_source_name_fft") == "sample_fft"
    assert AGuiModule._derived_process_alias(
        primary, "very_long_source_name") == "sample"
    assert AGuiModule._derived_process_alias(
        primary, "very_long_source_name2") == ""
    assert AGuiModule._derived_process_alias(primary, "unrelated") == ""


def test_process_alias_propagates_to_each_new_output() -> None:
    workspace = Workspace("source")
    primary = workspace.add_item(
        ExampleData(name="long_scan_name"), alias="scan")
    fft_payload = ExampleData(name="long_scan_name_fft")
    quality_payload = ExampleData(name="long_scan_name_quality")
    fft_item = workspace.add_item(fft_payload)
    quality_item = workspace.add_item(quality_payload)
    changed = []
    workspace.item_changed.connect(changed.append)
    module = SimpleNamespace(
        workspace_containing_item=lambda _item: workspace)

    AGuiModule._apply_process_result_aliases(
        module,
        [primary],
        [fft_payload, quality_payload],
        [fft_item, quality_item],
    )

    assert fft_item.alias == "scan_fft"
    assert quality_item.alias == "scan_quality"
    assert changed == ["long_scan_name_fft", "long_scan_name_quality"]


def test_manual_output_alias_becomes_base_for_next_processing_step() -> None:
    workspace = Workspace("source")
    first = workspace.add_item(
        ExampleData(name="long_scan_name_fft"), alias="clean")
    next_payload = ExampleData(name="long_scan_name_fft_bg")
    next_item = workspace.add_item(next_payload)
    module = SimpleNamespace(
        workspace_containing_item=lambda _item: workspace)

    AGuiModule._apply_process_result_aliases(
        module, [first], next_payload, [next_item])

    assert next_item.alias == "clean_bg"


def test_existing_output_alias_and_unaliased_primary_are_not_overridden() -> None:
    workspace = Workspace("source")
    primary = workspace.add_item(ExampleData(name="source"))
    payload = ExampleData(name="source_fft")
    output = workspace.add_item(payload, alias="explicit")
    module = SimpleNamespace(
        workspace_containing_item=lambda _item: workspace)

    AGuiModule._apply_process_result_aliases(
        module, [primary], payload, [output])

    assert output.alias == "explicit"


def test_result_dispatch_propagates_alias_into_shared_output_workspace() -> None:
    private = Workspace("private")
    shared = Workspace("shared")
    primary = private.add_item(
        ExampleData(name="long_scan_name"), alias="scan")
    payload = ExampleData(name="long_scan_name_fft")

    class ModuleStub:
        _apply_process_result_aliases = (
            AGuiModule._apply_process_result_aliases)

        @staticmethod
        def accessible_workspaces():
            return [private, shared]

        @staticmethod
        def workspace_containing_item(item):
            for workspace in (private, shared):
                if workspace.find_item_by_id(item.item_id) is item:
                    return workspace
            return None

    def add_to_shared(_task_id, result):
        shared.add_item(result)

    AGuiModule._dispatch_process_result(
        ModuleStub(), "task", payload, add_to_shared, [primary])

    assert shared.list_items()[0].alias == "scan_fft"
