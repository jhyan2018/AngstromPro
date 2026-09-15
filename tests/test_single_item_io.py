"""Standalone native files retain WorkspaceItem fields without changing payload IO."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import h5py
import numpy as np
import pytest

from angstrompro.core.data.base import WorkspaceData
from angstrompro.core.data.annotation_data import LineData, PointSetData, RegionData
from angstrompro.core.data.scene_plot import ScenePlot
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.workspaces.workspace import Workspace
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.modules.data_browser.data_browser_module import DataBrowserModule
from angstrompro.io import angstrom_io, load, load_item, save, save_item


def _uds() -> UdsDataStru:
    return UdsDataStru(
        name="scan",
        data=np.asarray([1.0, 2.0]),
        axes=[Axis(values=np.asarray([0.0, 1.0]), label="x")],
    )


@pytest.mark.parametrize(
    "payload, extension",
    [(_uds(), ".uds"), (ScenePlot(name="plot"), ".scplot")],
)
def test_native_single_item_round_trip(
        tmp_path: Path, payload: WorkspaceData, extension: str) -> None:
    item = WorkspaceItem(payload=payload, alias="reference")
    item.annotations = {
        "primary_points": PointSetData(coords=np.asarray([[3.5, 4.0]])),
        "interest_region": RegionData(1, 2, 3, 4),
        "line_cut": LineData((1.0, 2.0), (3.0, 4.0), 10),
    }
    path = tmp_path / f"item{extension}"

    save_item(path, item)

    with h5py.File(path, "r") as root:
        assert root["workspace_item"].attrs["version"] == 1
        assert root["workspace_item"].attrs["type_id"] == payload.type_id
        assert root["workspace_item"].attrs["item_id"] == item.item_id
    assert isinstance(load(path), type(payload))

    restored = load_item(path)
    assert restored.payload.name == payload.name
    assert restored.item_id == item.item_id
    assert restored.alias == item.alias
    np.testing.assert_allclose(
        restored.annotations["primary_points"].coords, [[3.5, 4.0]]
    )
    assert restored.annotations["interest_region"] == item.annotations["interest_region"]
    assert restored.annotations["line_cut"] == item.annotations["line_cut"]


@pytest.mark.parametrize(
    "payload, extension",
    [(_uds(), ".uds"), (ScenePlot(name="plot"), ".scplot")],
)
def test_old_payload_only_files_get_default_item_fields(
        tmp_path: Path, payload: WorkspaceData, extension: str) -> None:
    path = tmp_path / f"old{extension}"
    save(path, payload)
    item = load_item(path)
    assert item.payload.name == payload.name
    assert item.item_id.startswith("item_")
    assert item.alias == ""
    assert item.annotations == {}


@dataclass
class PluginPayload(WorkspaceData):
    type_id: ClassVar[str] = "test.single_item_plugin"
    name: str = ""
    value: int = 0


def _plugin_save(path: Path, payload: PluginPayload) -> None:
    with h5py.File(path, "w") as root:
        root.attrs["type_id"] = PluginPayload.type_id
        root.attrs["format_version"] = 7
        root.attrs["name"] = payload.name
        root.attrs["value"] = payload.value


def _plugin_load(path: Path) -> PluginPayload:
    with h5py.File(path, "r") as root:
        if int(root.attrs["format_version"]) != 7:
            raise ValueError("Unsupported plugin payload version")
        return PluginPayload(
            name=str(root.attrs["name"]), value=int(root.attrs["value"]),
        )


def test_registered_plugin_format_uses_shared_item_metadata(
        tmp_path: Path) -> None:
    angstrom_io.register_io(
        PluginPayload.type_id, _plugin_load, _plugin_save,
        extension=".plugin", display_name="Test plugin",
    )
    try:
        item = WorkspaceItem(payload=PluginPayload(name="bands", value=42))
        item.alias = "result"
        path = tmp_path / "bands.plugin"
        save_item(path, item)
        with h5py.File(path, "r") as root:
            assert root.attrs["format_version"] == 7
        restored = load_item(path)
        assert isinstance(restored.payload, PluginPayload)
        assert restored.payload.value == 42
        assert restored.alias == "result"
        assert restored.item_id == item.item_id
    finally:
        angstrom_io._READERS.pop(PluginPayload.type_id, None)
        angstrom_io._WRITERS.pop(PluginPayload.type_id, None)
        angstrom_io._FORMATS.pop(PluginPayload.type_id, None)


def test_myplugin_native_formats_use_shared_item_metadata(
        tmp_path: Path) -> None:
    pytest.importorskip("myplugin.io")
    from myplugin.core.data import AtomicStructureData, DispersionData, Scene3D

    structure = AtomicStructureData(
        cell=np.diag([2.0, 2.0, 12.0]),
        species=("C",),
        fractional_positions=np.zeros((1, 3)),
        charges=(None,),
        name="structure",
    )
    payloads = [
        (structure, ".astr"),
        (DispersionData(structure=structure, name="bands"), ".dps"),
        (Scene3D(name="scene"), ".sc3d"),
    ]
    for payload, extension in payloads:
        source = WorkspaceItem(payload=payload, alias="saved")
        path = tmp_path / f"{payload.name}{extension}"
        save_item(path, source)
        restored = load_item(path)
        assert isinstance(restored.payload, type(payload))
        assert restored.payload.name == payload.name
        assert restored.item_id == source.item_id
        assert restored.alias == "saved"


def test_import_renames_duplicate_name_and_id(tmp_path: Path) -> None:
    source = WorkspaceItem(payload=_uds(), alias="reference")
    path = tmp_path / "scan.uds"
    save_item(path, source)

    workspace = Workspace("target")
    existing = workspace.add_item(_uds(), item_id=source.item_id)
    loaded = load_item(path)
    imported = workspace.add_item(
        loaded.payload, alias=loaded.alias,
        annotations=loaded.annotations, item_id=loaded.item_id,
    )
    assert imported.name == "scan_2"
    assert imported.alias == "reference"
    assert imported.item_id != existing.item_id


@pytest.mark.parametrize(
    "alias, expected_name",
    [("preview", "preview.uds"), ("", "scan.uds")],
)
def test_file_save_dialog_suggests_alias_when_present(
        monkeypatch, alias: str, expected_name: str) -> None:
    workspace = Workspace("source")
    item = workspace.add_item(_uds())
    item.alias = alias
    module = SimpleNamespace(
        workspace=workspace,
        _selected_item_name=lambda: item.name,
        _confirm_standalone_uds_save=lambda _item: True,
    )
    suggested = []

    def choose_save_path(_parent, _title, default_name, _filters):
        suggested.append(default_name)
        return "", ""

    monkeypatch.setattr(
        "angstrompro.core.modules.a_gui_module.QtWidgets.QFileDialog.getSaveFileName",
        choose_save_path,
    )
    AGuiModule._on_file_save(module)

    assert suggested == [expected_name]
    assert item.name == "scan"


def test_file_menu_saves_and_opens_complete_item(
        tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "menu.uds"
    source_workspace = Workspace("source")
    source = source_workspace.add_item(_uds())
    source.alias = "preview"
    source.annotations["primary_points"] = PointSetData(
        coords=np.asarray([[1.0, 2.0]])
    )
    source_module = SimpleNamespace(
        workspace=source_workspace,
        _selected_item_name=lambda: source.name,
        _confirm_standalone_uds_save=lambda _item: True,
    )
    monkeypatch.setattr(
        "angstrompro.core.modules.a_gui_module.QtWidgets.QFileDialog.getSaveFileName",
        lambda *_args: (str(path), ""),
    )
    AGuiModule._on_file_save(source_module)

    target_workspace = Workspace("target")
    target_module = SimpleNamespace(
        workspace=target_workspace,
        _context=SimpleNamespace(config=SimpleNamespace(get=lambda *_args: "")),
    )
    monkeypatch.setattr(
        "angstrompro.core.modules.a_gui_module.QtWidgets.QFileDialog.getOpenFileName",
        lambda *_args: (str(path), ""),
    )
    AGuiModule._on_file_open(target_module)
    restored = target_workspace.list_items()[0]
    assert restored.name == source.name
    assert restored.item_id == source.item_id
    assert restored.alias == "preview"
    np.testing.assert_allclose(
        restored.annotations["primary_points"].coords, [[1.0, 2.0]]
    )


def test_data_browser_card_loader_retains_native_item_metadata(
        tmp_path: Path) -> None:
    source = WorkspaceItem(payload=_uds(), alias="from file")
    path = tmp_path / "card.uds"
    save_item(path, source)

    loaded = DataBrowserModule._load_channel_payload(
        SimpleNamespace(), str(path), "data",
    )
    assert isinstance(loaded, WorkspaceItem)
    assert loaded.alias == "from file"
    assert loaded.item_id == source.item_id


def test_non_hdf5_writer_cannot_overwrite_existing_item_file(
        tmp_path: Path) -> None:
    path = tmp_path / "item.npy"
    path.write_bytes(b"existing file")
    item = WorkspaceItem(payload=_uds())
    item.payload.type_id = "npy"
    try:
        with pytest.raises(TypeError, match="cannot store workspace-item metadata"):
            save_item(path, item)
        assert path.read_bytes() == b"existing file"
    finally:
        del item.payload.type_id
