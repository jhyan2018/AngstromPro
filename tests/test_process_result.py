from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar

from angstrompro.core.data.annotation_data import PointSetData
from angstrompro.core.data.base import WorkspaceData
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.processes import (
    AnnotationOutputSpec,
    MetricOutputSpec,
    ProcessResult,
    ProcessSchema,
    iter_process_data,
    normalize_process_result,
    primary_process_data,
)
from angstrompro.core.workspaces.workspace import Workspace


@dataclass
class ExampleData(WorkspaceData):
    type_id: ClassVar[str] = "test.process_result"
    name: str = ""


def test_legacy_return_normalizes_without_copying() -> None:
    payload = ExampleData("legacy")
    result = normalize_process_result(payload)

    assert result.data is payload
    assert result.annotations == {}
    assert result.metrics == {}
    assert list(iter_process_data(result)) == [payload]
    assert primary_process_data(result) is payload


def test_structured_result_accepts_named_and_nested_data() -> None:
    first = ExampleData("first")
    second = ExampleData("second")
    result = ProcessResult(
        data={"main": first, "extra": [second]},
        annotations={"bragg_peaks": PointSetData()},
        metrics={"quality": 0.99},
    )

    assert list(iter_process_data(result)) == [first, second]
    assert primary_process_data(result) is first


def test_schema_structured_outputs_are_optional_and_declared() -> None:
    legacy = ProcessSchema()
    assert legacy.annotation_outputs == []
    assert legacy.metric_outputs == []

    schema = ProcessSchema(
        annotation_outputs=[AnnotationOutputSpec("bragg_peaks", "point_set")],
        metric_outputs=[MetricOutputSpec("quality", units="")],
    )
    assert schema.annotation_outputs[0].role == "bragg_peaks"
    assert schema.metric_outputs[0].name == "quality"


def test_default_gui_result_handling_unwraps_data_and_applies_annotations() -> None:
    workspace = Workspace("module")
    source = workspace.add_item(ExampleData("source"))
    output = ExampleData("source_result")
    peaks = PointSetData()

    class ModuleStub:
        accessible_workspaces = staticmethod(lambda: [workspace])
        workspace_containing_item = staticmethod(
            lambda item: workspace if item in workspace.list_items() else None)
        _apply_process_result_aliases = AGuiModule._apply_process_result_aliases

        def _on_process_result_default(self, task_id, result):
            return AGuiModule._on_process_result_default(self, task_id, result)

    module = ModuleStub()
    module.workspace = workspace
    result = ProcessResult(
        data=output,
        annotations={"bragg_peaks": peaks},
        metrics={"quality": 1.0},
    )

    AGuiModule._dispatch_process_result(
        module,
        "task",
        result,
        module._on_process_result_default,
        [source],
    )

    assert workspace.get_item("source_result").payload is output
    assert source.annotations["bragg_peaks"] is peaks
    assert source.metadata["process_results"][0]["values"]["quality"] == 1.0


def test_values_and_metrics_share_a_namespace_without_new_payloads():
    from angstrompro.core.processes import ValueOutputSpec
    result = ProcessResult(metrics={"quality": .99}, values={"periods": [13.4, 20.7]},
                           value_units={"periods": "px"})
    schema = ProcessSchema(metric_outputs=[MetricOutputSpec("quality")],
                           value_outputs=[ValueOutputSpec("periods", units="px", sequence=True)])
    assert result.data is None
    assert result.values == {"quality": .99, "periods": [13.4, 20.7]}
    assert [spec.name for spec in schema.value_outputs] == ["quality", "periods"]
