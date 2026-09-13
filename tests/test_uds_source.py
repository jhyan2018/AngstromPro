from __future__ import annotations

import h5py
import numpy as np

from angstrompro.core.data.uds_data import (
    UdsDataStru,
    file_source,
    propagate_uds_source,
    uds_has_multiple_sources,
)
from angstrompro.core.processes.registry import _record_history
from angstrompro.core.workspaces.workspace import Workspace
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.io.formats.npy_io import load as load_npy
from angstrompro.io.formats.txt_io import load as load_txt
from angstrompro.io.uds_io import load, save
from angstrompro.io.workspace_io import load_workspace, save_workspace


def _uds(name: str, source=None) -> UdsDataStru:
    info = {} if source is None else {"source": source}
    return UdsDataStru(
        name=name,
        data=np.zeros((1, 2, 2), dtype=np.float64),
        info=info,
    )


def test_single_input_source_is_copied_exactly() -> None:
    original_source = ["file-a", "planewave_synthesiser"]
    source = _uds("input", original_source)
    result = _uds("result", "discard-me")

    propagate_uds_source(result, [source])

    assert result.info["source"] == original_source
    assert result.info["source"] is not original_source


def test_multiple_input_sources_flatten_in_order_and_keep_duplicates() -> None:
    first = _uds("first", "same-source")
    second = _uds("second", ["same-source", "other-source"])
    result = _uds("result")

    propagate_uds_source(result, [first, second])

    assert result.info["source"] == [
        "same-source",
        "same-source",
        "other-source",
    ]
    assert uds_has_multiple_sources(result)


def test_standalone_save_warning_requires_multiple_list_entries() -> None:
    assert not uds_has_multiple_sources(_uds("scalar", "one-source"))
    assert not uds_has_multiple_sources(_uds("one-list", ["one-source"]))
    assert uds_has_multiple_sources(
        _uds("duplicates", ["same-source", "same-source"])
    )


def test_process_history_propagates_sources_and_labels_new_simulation() -> None:
    first = _uds("first", "same-source")
    second = _uds("second", "same-source")
    combined = _record_history(
        _uds("combined"),
        "math.add",
        {},
        {"left": first, "right": second},
    )

    assert combined.info["source"] == ["same-source", "same-source"]
    assert combined.proc_history[-1].step == "math.add"

    simulated = _record_history(
        _uds("simulated"),
        "simulate.sinusoidal2d",
        {},
        {},
    )
    assert simulated.info["source"] == "simulate.sinusoidal2d"


def test_raw_file_readers_store_the_resolved_path(tmp_path) -> None:
    txt_path = tmp_path / "values.txt"
    npy_path = tmp_path / "values.npy"
    np.savetxt(txt_path, np.arange(4).reshape(2, 2))
    np.save(npy_path, np.arange(4).reshape(2, 2))

    assert load_txt(txt_path).info["source"] == file_source(txt_path)
    assert load_npy(npy_path).info["source"] == file_source(npy_path)


def test_source_survives_uds_hdf5_and_legacy_format_is_ignored(tmp_path) -> None:
    path = tmp_path / "derived.uds"
    source = ["same-source", "same-source", "other-source"]
    save(path, _uds("derived", source))

    loaded = load(path)
    assert loaded.info["source"] == source

    legacy_metadata = _uds("legacy")
    legacy_metadata.info = {"_source_format": "nanonis_sxm"}
    legacy_metadata.__post_init__()
    assert "source" not in legacy_metadata.info
    assert "_source_format" not in legacy_metadata.info


def test_workspace_items_and_new_archives_have_no_source_path(tmp_path) -> None:
    workspace = Workspace("source-test")
    item = workspace.add_item(_uds("data", "root-source"))
    assert not hasattr(item, "source_path")
    assert "source_path" not in WorkspaceItem.__dataclass_fields__

    path = tmp_path / "workspace.apws"
    assert save_workspace(path, workspace) == []
    with h5py.File(path, "r+") as archive:
        stored = archive["items/00000000"]
        assert "source_path" not in stored.attrs
        # Old archives may still contain this attribute; the reader ignores it.
        stored.attrs["source_path"] = "discarded-old-path.sxm"

    archive = load_workspace(path)
    assert archive.items[0].payload.info["source"] == "root-source"
    assert not hasattr(archive.items[0], "source_path")
