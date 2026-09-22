import h5py
import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.workspaces import WorkspaceManager
from angstrompro.io.angstrom_io import save_item, load_item
from angstrompro.io.workspace_io import save_workspace, load_workspace, import_workspace


def test_metadata_round_trip_copy_and_old_files(tmp_path):
    manager = WorkspaceManager()
    ws = manager.create_shared_workspace("workflow")
    item = ws.add_item(
        UdsDataStru(
            name="source", data=np.arange(3.0), axes=[Axis(np.arange(3.0), "x")]
        )
    )
    item.metadata = {
        "workflow": {
            "values": {"periods": np.array([12.4, 15.6])},
            "input": {"item_id": item.item_id},
        }
    }
    path = tmp_path / "source.uds"
    save_item(path, item)
    loaded = load_item(path)
    np.testing.assert_array_equal(
        loaded.metadata["workflow"]["values"]["periods"], [12.4, 15.6]
    )
    with h5py.File(path, "r+") as root:
        del root["workspace_item"]["metadata"]
    assert load_item(path).metadata == {}
    copied = manager.transfer_item(ws.workspace_id, ws.workspace_id, item.name)
    assert copied.metadata["workflow"]["input"]["item_id"] == copied.item_id
    copied.metadata["workflow"]["values"]["periods"][0] = 99
    assert item.metadata["workflow"]["values"]["periods"][0] == 12.4
    archive = tmp_path / "run.apws"
    save_workspace(archive, ws)
    restored, _ = import_workspace(load_workspace(archive), ws)
    assert restored[0].metadata["workflow"]["input"]["item_id"] == restored[0].item_id
    with h5py.File(archive, "r+") as root:
        for group in root["items"].values():
            del group["metadata"]
    assert all(not old.metadata for old in load_workspace(archive).items)


def test_metadata_preserves_empty_numerical_array_shape():
    from angstrompro.core.workspaces.item_metadata import metadata_dumps, metadata_loads

    restored = metadata_loads(metadata_dumps({"points": np.empty((0, 2))}))
    assert restored["points"].shape == (0, 2)


def test_single_item_id_collision_remaps_its_own_references():
    ws = WorkspaceManager().create_shared_workspace("Import")
    original = ws.add_item(UdsDataStru(name="original"))
    duplicate = ws.add_item(
        UdsDataStru(name="duplicate"),
        item_id=original.item_id,
        metadata={"workflow": {"input": {"item_id": original.item_id}}},
    )
    assert duplicate.item_id != original.item_id
    assert duplicate.metadata["workflow"]["input"]["item_id"] == duplicate.item_id
