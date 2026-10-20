from __future__ import annotations

import pytest

from angstrompro.core.data.base import WorkspaceData
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.widgets.workspace_item_inspector import WorkspaceItemInspector
from angstrompro.utils.qt_compat import QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class _ScalarInspectorPayload(WorkspaceData):
    type_id = "scalar_inspector_test"

    def __init__(self) -> None:
        self.name = "scalar values"

    def inspect_fields(self) -> list[dict]:
        return [
            {
                "kind": "group",
                "label": "counts",
                "summary": 2,
                "children": [
                    {"kind": "value", "label": 1, "value": 7},
                ],
            },
        ]


def test_inspector_stringifies_scalar_node_columns(qapp):
    inspector = WorkspaceItemInspector()

    inspector.set_item(WorkspaceItem(payload=_ScalarInspectorPayload()))

    group = inspector._tree.topLevelItem(0)
    assert group.text(0) == "counts"
    assert group.text(1) == "2"
    assert group.child(0).text(0) == "1"
    assert group.child(0).text(1) == "7"
    inspector.close()
