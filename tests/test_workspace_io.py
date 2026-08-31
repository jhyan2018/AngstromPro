# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 2026

@author: jiahaoYan
Tests for extensible workspace archive codecs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import h5py
import numpy as np
import pytest

from angstrompro.core.data import WorkspaceData
from angstrompro.core.data.scene_plot import ScenePlot
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.workspaces.workspace import Workspace
from angstrompro.io import angstrom_io
from angstrompro.io.angstrom_io import register_workspace_codec
from angstrompro.io.workspace_io import (
    load_workspace,
    save_workspace,
    split_supported_items,
)


@dataclass
class ExamplePayload(WorkspaceData):
    type_id: ClassVar[str] = "test.workspace_codec"

    name: str = ""
    value: int = 0


@dataclass
class RuntimeOnlyPayload(WorkspaceData):
    type_id: ClassVar[str] = "test.runtime_only"

    name: str = ""


def _write_example(group, payload: ExamplePayload) -> None:
    group.attrs["value"] = payload.value


def _read_example(group) -> ExamplePayload:
    return ExamplePayload(value=int(group.attrs["value"]))


def _remove_test_codec() -> None:
    angstrom_io._WORKSPACE_CODECS.pop(ExamplePayload.type_id, None)


def test_builtin_payloads_still_round_trip_through_registry(tmp_path: Path) -> None:
    workspace = Workspace("source")
    workspace.add_item(UdsDataStru(
        name="curve",
        data=np.asarray([1.0, 2.0]),
        axes=[Axis(values=np.asarray([0.0, 1.0]), label="x")],
    ))
    workspace.add_item(ScenePlot(name="plot"))

    archive_path = tmp_path / "builtins.apws"
    assert save_workspace(archive_path, workspace) == []
    loaded = load_workspace(archive_path)

    assert loaded.skipped == []
    assert [type(item.payload) for item in loaded.items] == [
        UdsDataStru,
        ScenePlot,
    ]
    np.testing.assert_allclose(loaded.items[0].payload.data, [1.0, 2.0])


def test_registered_codec_round_trip_and_missing_plugin_skip(tmp_path: Path) -> None:
    _remove_test_codec()
    register_workspace_codec(
        ExamplePayload.type_id,
        _read_example,
        _write_example,
        provider="example_plugin",
        version=3,
    )
    try:
        workspace = Workspace("source", "Example workspace")
        item = workspace.add_item(ExamplePayload(name="answer", value=42))
        item.alias = "result"
        runtime_only = workspace.add_item(RuntimeOnlyPayload(name="temporary"))

        supported, unsupported = split_supported_items(workspace.list_items())
        assert supported == [item]
        assert unsupported == [runtime_only]

        archive_path = tmp_path / "example.apws"
        skipped_on_save = save_workspace(archive_path, workspace)
        assert skipped_on_save == [runtime_only]

        with h5py.File(archive_path, "r") as archive:
            stored = archive["items/00000000"]
            assert stored.attrs["type_id"] == ExamplePayload.type_id
            assert stored.attrs["payload_provider"] == "example_plugin"
            assert stored.attrs["payload_version"] == 3

        loaded = load_workspace(archive_path)
        assert not loaded.skipped
        assert len(loaded.items) == 1
        assert isinstance(loaded.items[0].payload, ExamplePayload)
        assert loaded.items[0].payload.value == 42
        assert loaded.items[0].alias == "result"

        with h5py.File(archive_path, "r+") as archive:
            stored = archive["items/00000000"]
            stored.attrs["payload_provider"] = "different_plugin"
        mismatched = load_workspace(archive_path)
        assert not mismatched.items
        assert "does not match" in mismatched.skipped[0].reason

        with h5py.File(archive_path, "r+") as archive:
            stored = archive["items/00000000"]
            stored.attrs["payload_provider"] = "example_plugin"
            stored.attrs["payload_version"] = 4
        too_new = load_workspace(archive_path)
        assert not too_new.items
        assert "newer than" in too_new.skipped[0].reason

        with h5py.File(archive_path, "r+") as archive:
            archive["items/00000000"].attrs["payload_version"] = 3
        _remove_test_codec()
        unavailable = load_workspace(archive_path)
        assert not unavailable.items
        assert len(unavailable.skipped) == 1
        assert unavailable.skipped[0].type_id == ExamplePayload.type_id
        assert unavailable.skipped[0].provider == "example_plugin"
        assert unavailable.skipped[0].payload_version == 3
    finally:
        _remove_test_codec()


def test_codec_registration_rejects_provider_collisions() -> None:
    _remove_test_codec()
    try:
        register_workspace_codec(
            ExamplePayload.type_id,
            _read_example,
            _write_example,
            provider="first_plugin",
        )
        with pytest.raises(ValueError, match="already registered"):
            register_workspace_codec(
                ExamplePayload.type_id,
                _read_example,
                _write_example,
                provider="different_plugin",
            )
    finally:
        _remove_test_codec()
