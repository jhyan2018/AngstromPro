from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from angstrompro.core.data.annotation_data import ANNOTATION_ROLES, PointSetData
from angstrompro.gui.modules.image_stack_viewer import ImageStackViewer


def _module_with_primary(name: str = "sample"):
    item = SimpleNamespace(name=name, annotations={})
    status_bar = Mock()
    module = SimpleNamespace(
        _main_item=item,
        workspace=Mock(),
        statusBar=lambda: status_bar,
    )
    return module, item, status_bar


def test_general_primary_points_preserve_every_picked_point_in_order() -> None:
    panel = SimpleNamespace(
        img_picked_points_list=["4,7", "10,2", "0,9"]
    )
    coords = ImageStackViewer._get_picked_coords(None, panel)
    module, item, status_bar = _module_with_primary()
    module._get_picked_coords = lambda selected_panel: coords

    ImageStackViewer._set_general_points(
        module,
        panel,
        source_item=item,
        source_label="Primary",
        role="primary_points",
    )

    annotation = item.annotations["primary_points"]
    assert isinstance(annotation, PointSetData)
    np.testing.assert_array_equal(
        annotation.coords,
        np.asarray([[7, 4], [2, 10], [9, 0]]),
    )
    module.workspace.notify_changed.assert_called_once_with("sample")
    status_bar.showMessage.assert_called_once()


def test_general_reference_points_are_stored_on_primary_item() -> None:
    panel = object()
    reference_item = SimpleNamespace(name="reference")
    coords = np.asarray([[3, 8], [5, 13]])
    module, primary_item, _status_bar = _module_with_primary("primary")
    module._get_picked_coords = lambda selected_panel: coords

    ImageStackViewer._set_general_points(
        module,
        panel,
        source_item=reference_item,
        source_label="Reference",
        role="reference_points",
    )

    np.testing.assert_array_equal(
        primary_item.annotations["reference_points"].coords,
        coords,
    )
    assert not hasattr(reference_item, "annotations")
    module.workspace.notify_changed.assert_called_once_with("primary")


def test_general_point_roles_are_registered() -> None:
    assert "primary_points" in ANNOTATION_ROLES
    assert "reference_points" in ANNOTATION_ROLES
