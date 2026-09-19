"""Nanonis .3ds sweep channels and per-pixel experiment parameters."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from angstrompro.gui.dialogs.channel_manager_dialog import ChannelManagerDialog
from angstrompro.gui.dialogs.channel_picker_dialog import ChannelPickerDialog
from angstrompro.gui.dialogs.unmatched_channels_dialog import (
    UnmatchedChannelsDialog, UnmatchedResolution,
)
from angstrompro.gui.modules.data_browser.render_task import (
    _load_3ds, render_file_task,
)
from angstrompro.gui.utils.file_loading import load_with_channel_picker
from angstrompro.io.channel_manager import (
    ChannelConfig, ChannelManager, FormatChannelConfig,
)
from angstrompro.io.formats.nanonis_3ds import (
    GridField, _find_header_sweep_value, _find_sweep_channel,
    field_names, load, match_field, parse_header,
)
from angstrompro.utils.qt_compat import QtWidgets


CHANNELS = [
    "Current (A)", "C2: Acc_square (V V)",
    "LI Demod 1 X (A)", "LI Demod 1 Y (A)",
]
PARAMETERS = [
    "X (m)", "Y (m)", "Z (m)", "Z offset (m)",
    "Settling time (s)", "Integration time (s)", "Z-Ctrl hold",
    "Final Z (m)", "Scan:Current (A)", "Scan:C2: Acc_square (V V)",
    "Scan:Z (m)", "Scan:LI Demod 1 X (A)", "Scan:LI Demod 1 Y (A)",
]


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _write_grid_file(path: Path, x_pixels: int = 2,
                     y_pixels: int = 2) -> Path:
    lines = [
        f'Grid dim="{x_pixels} x {y_pixels}"',
        'Grid settings="0;0;2;2;0"',
        'Sweep Signal="Bias (V)"',
        'Fixed parameters="Sweep Start;Sweep End"',
        f'Experiment parameters="{";".join(PARAMETERS)}"',
        '# Parameters (4 byte)=15',
        'Experiment size (bytes)=336',
        'Points=21',
        f'Channels="{";".join(CHANNELS)}"',
        ':HEADER_END:',
    ]
    records = []
    for pixel in range(x_pixels * y_pixels):
        fixed = [0.0, 1.0]
        parameters = [pixel * 100.0 + 2 + i for i in range(13)]
        channels = [pixel * 1000.0 + channel * 100.0 + point
                    for channel in range(4) for point in range(21)]
        records.extend(fixed + parameters + channels)
    path.write_bytes(
        ("\r\n".join(lines) + "\r\n").encode("latin-1") +
        np.asarray(records, dtype=">f4").tobytes()
    )
    return path


@pytest.fixture
def grid_file(tmp_path: Path) -> Path:
    return _write_grid_file(tmp_path / "grid.3ds")


def test_parameter_offsets_and_one_layer_maps(grid_file: Path) -> None:
    header, _ = parse_header(grid_file)
    channels, parameters = field_names(header)
    assert channels == CHANNELS
    assert parameters == PARAMETERS

    current, z, scan_z = load(grid_file, fields=[
        GridField("channel", 0),
        GridField("experiment_parameter", 2),
        GridField("experiment_parameter", 10),
    ])
    assert current.data.shape == (21, 2, 2)
    np.testing.assert_allclose(current.data[0], [[2000, 3000], [0, 1000]])
    assert current.info["field_source"] == "channel"
    assert current.info["channel_loaded"] == "Current (A)"
    assert z.data.shape == scan_z.data.shape == (1, 2, 2)
    np.testing.assert_allclose(z.data[0], [[204, 304], [4, 104]])
    np.testing.assert_allclose(scan_z.data[0], [[212, 312], [12, 112]])
    assert z.info["field_source"] == "experiment_parameter"
    assert z.info["experiment_parameter_loaded"] == "Z (m)"
    assert scan_z.info["experiment_parameter_loaded"] == "Scan:Z (m)"
    assert z.axes[0].label == "Layer"
    assert scan_z.name == "grid_Scan_Z (m)"


def test_rectangular_grid_parameter_and_channel_axes(tmp_path: Path) -> None:
    path = _write_grid_file(tmp_path / "rectangular.3ds", 3, 2)
    channel, z = load(path, fields=[
        GridField("channel", 0), GridField("experiment_parameter", 2),
    ])
    assert channel.data.shape == (21, 2, 3)
    assert z.data.shape == (1, 2, 3)
    np.testing.assert_allclose(z.data[0], [
        [304, 404, 504], [4, 104, 204],
    ])
    assert [len(axis.values) for axis in z.axes] == [1, 2, 3]


def test_line_cut_keeps_existing_x_order(tmp_path: Path) -> None:
    path = _write_grid_file(tmp_path / "line.3ds", 3, 1)
    channel, z = load(path, fields=[
        GridField("channel", 0), GridField("experiment_parameter", 2),
    ])
    assert channel.data.shape == (3, 21)
    np.testing.assert_allclose(channel.data[:, 0], [2000, 1000, 0])
    assert z.data.shape == (1, 1, 3)
    np.testing.assert_allclose(z.data[0, 0], [204, 104, 4])


def test_parameter_extraction_rejects_inconsistent_header_counts(
        grid_file: Path, tmp_path: Path) -> None:
    path = tmp_path / "bad_parameters.3ds"
    path.write_bytes(grid_file.read_bytes().replace(
        b'Fixed parameters="Sweep Start;Sweep End"',
        b'Fixed parameters="Sweep Start"',
    ))
    with pytest.raises(ValueError, match="Cannot locate experiment parameters"):
        load(path, fields=[GridField("experiment_parameter", 2)])


def test_parameter_offset_can_be_inferred_without_fixed_names(
        grid_file: Path, tmp_path: Path) -> None:
    path = tmp_path / "unnamed_fixed.3ds"
    path.write_bytes(grid_file.read_bytes().replace(
        b'Fixed parameters="Sweep Start;Sweep End"\r\n', b'',
    ))
    z = load(path, fields=[GridField("experiment_parameter", 2)])
    np.testing.assert_allclose(z.data[0], [[204, 304], [4, 104]])
    assert z.info["fixed_parameter_count"] == 2

    channel = load(path, fields=[GridField("channel", 0)])
    np.testing.assert_allclose(channel.axes[0].values,
                               np.linspace(0.0, 1.0, 21))


def test_partial_grid_uses_completed_record_for_axis_and_zero_fills_pixels(
        grid_file: Path, tmp_path: Path) -> None:
    header, data_offset = parse_header(grid_file)
    channels, _parameters = field_names(header)
    stride = (int(header["# parameters (4 byte)"]) +
              len(channels) * int(header["points"]))
    path = tmp_path / "partial.3ds"
    complete_pixels = 2
    trailing_floats = 10
    path.write_bytes(grid_file.read_bytes()[:
        data_offset + (complete_pixels * stride + trailing_floats) * 4])

    channel = load(path, fields=[GridField("channel", 0)])

    np.testing.assert_allclose(channel.axes[0].values,
                               np.linspace(0.0, 1.0, 21))
    assert np.count_nonzero(np.any(channel.data != 0.0, axis=0)) == 2
    assert channel.info["incomplete_acquisition"] is True
    assert channel.info["_complete_pixels"] == 2
    assert channel.info["_expected_pixels"] == 4
    assert channel.info["_trailing_floats_discarded"] == trailing_floats
    assert channel.info["sweep_axis_source"] == "fixed_parameters"


def test_channel_load_rejects_file_without_a_complete_pixel(
        grid_file: Path, tmp_path: Path) -> None:
    _header, data_offset = parse_header(grid_file)
    path = tmp_path / "header_only.3ds"
    path.write_bytes(grid_file.read_bytes()[:data_offset])

    with pytest.raises(ValueError, match="Cannot determine the sweep axis"):
        load(path, fields=[GridField("channel", 0)])


def test_header_only_grid_uses_textual_sweep_bounds_and_renders_thumbnail(
        grid_file: Path, tmp_path: Path) -> None:
    path = tmp_path / "header_bounds_only.3ds"
    content = grid_file.read_bytes().replace(
        b":HEADER_END:\r\n",
        b'Bias Spectroscopy>Sweep Start (V)="-1.6E-3"\r\n'
        b'Bias Spectroscopy>Sweep End (V)="-1.4E-3"\r\n'
        b":HEADER_END:\r\n",
    )
    path.write_bytes(content)
    _header, data_offset = parse_header(path)
    path.write_bytes(path.read_bytes()[:data_offset])

    channel = load(path, fields=[GridField("channel", 0)])

    np.testing.assert_allclose(
        channel.axes[0].values,
        np.linspace(-1.6e-3, -1.4e-3, 21),
    )
    assert np.count_nonzero(channel.data) == 0
    assert channel.info["incomplete_acquisition"] is True
    assert channel.info["_complete_pixels"] == 0
    assert channel.info["sweep_axis_source"] == "header_parameters"

    thumbnail_cache = tmp_path / "thumbnail-cache"
    thumbnail_cache.mkdir()
    rendered = render_file_task(
        str(path),
        str(thumbnail_cache),
        channel_cfg=[{
            "display_name": "Current",
            "aliases": ["Current (A)"],
            "load_by_default": True,
            "source": "channel",
        }],
    )
    assert rendered["thumbs"][0]["status"] == "ok"
    assert Path(rendered["thumbs"][0]["png_path"]).exists()


def test_textual_sweep_bound_prefers_matching_signal_section() -> None:
    header = {
        "bias spectroscopy>sweep start (v)": "-0.002",
        "gate spectroscopy>sweep start (v)": "-1.0",
    }
    assert _find_header_sweep_value(
        header, "sweep start", "Bias (V)") == pytest.approx(-0.002)
    assert _find_header_sweep_value(
        header, "sweep start", "Unknown (V)") is None


def test_sweep_parameter_names_accept_trailing_units(
        grid_file: Path, tmp_path: Path) -> None:
    path = tmp_path / "parameter_units.3ds"
    path.write_bytes(grid_file.read_bytes().replace(
        b'Fixed parameters="Sweep Start;Sweep End"',
        b'Fixed parameters="Sweep Start (V);Sweep End (V)"',
    ))
    channel = load(path, fields=[GridField("channel", 0)])
    np.testing.assert_allclose(channel.axes[0].values,
                               np.linspace(0.0, 1.0, 21))


def test_ambiguous_loose_sweep_channel_match_is_not_selected() -> None:
    assert _find_sweep_channel(
        ["Bias (V) forward", "Bias (V) backward"], "Bias (V)") is None


def test_source_specific_matching_does_not_confuse_equal_names() -> None:
    channels = ["Z (m)"]
    parameters = ["Z (m)", "Scan:Z (m)"]
    assert match_field(["Z (m)"], channels, parameters, "channel") == GridField(
        "channel", 0,
    )
    assert match_field(["Z (m)"], channels, parameters,
                       "experiment_parameter") == GridField(
        "experiment_parameter", 0,
    )
    assert match_field(["Scan:Z (m)"], channels, parameters,
                       "experiment_parameter") == GridField(
        "experiment_parameter", 1,
    )


def test_old_channel_config_without_source_keeps_builtin_z_choice() -> None:
    old_config = {"nanonis_3ds": {
        "Z": {"aliases": ["Scan:Z (m)"], "load_by_default": True},
    }}
    config = SimpleNamespace(get=lambda *_args: old_config)
    manager = ChannelManager(config)
    z = next(cc for cc in manager.get("nanonis_3ds").channels
             if cc.display_name == "Z")
    assert z.source == "either"
    assert z.aliases[0] == "Scan:Z (m)"


def test_picker_shows_both_z_parameter_sources(
        grid_file: Path, qapp) -> None:
    del qapp
    config = FormatChannelConfig("nanonis_3ds", [
        ChannelConfig("Z", ["Z (m)"], True, "either"),
    ])
    dialog = ChannelPickerDialog(
        None, grid_file, CHANNELS, {"x_pixels": 2, "y_pixels": 2,
                                    "n_points": 21}, config,
        experiment_parameters=PARAMETERS,
    )
    assert dialog.selected_fields() == [GridField("experiment_parameter", 2)]
    for checkbox, field in dialog._checkboxes:
        if field == GridField("experiment_parameter", 10):
            checkbox.setChecked(True)
    assert dialog.selected_fields() == [
        GridField("experiment_parameter", 2),
        GridField("experiment_parameter", 10),
    ]
    labels = [label.text() for label in dialog.findChildren(QtWidgets.QLabel)]
    assert any("Experiment parameter 11 of 13" in label for label in labels)
    assert any("one value per pixel" in label for label in labels)
    dialog.close()


def test_open_and_data_browser_keep_parameter_source(
        grid_file: Path, qapp, monkeypatch) -> None:
    del qapp
    config = FormatChannelConfig("nanonis_3ds", [
        ChannelConfig("Z", ["Z (m)"], True, "experiment_parameter"),
    ], auto_load=True)
    context = SimpleNamespace(channel_manager=SimpleNamespace(
        get=lambda _format: config,
    ))
    result = load_with_channel_picker(grid_file, context)
    assert result.data.shape == (1, 2, 2)
    assert result.info["field_source"] == "experiment_parameter"
    assert result.name == "grid_Z"

    monkeypatch.setattr(ChannelPickerDialog, "exec", lambda _self: 1)
    monkeypatch.setattr(ChannelPickerDialog, "selected_fields", lambda _self: [
        GridField("experiment_parameter", 2),
        GridField("experiment_parameter", 10),
    ])
    config.auto_load = False
    selected = load_with_channel_picker(grid_file, context)
    assert [item.info["experiment_parameter_loaded"] for item in selected] == [
        "Z (m)", "Scan:Z (m)",
    ]
    assert [item.name for item in selected] == ["grid_Z", "grid_Scan_Z (m)"]

    available, payloads, missing = _load_3ds(grid_file, [{
        "display_name": "Z", "aliases": ["Scan:Z (m)"],
        "load_by_default": True, "source": "experiment_parameter",
    }])
    assert "Experiment parameter: Scan:Z (m)" in available
    assert missing == []
    assert payloads[0][1].info["experiment_parameter_loaded"] == "Scan:Z (m)"
    assert payloads[0][1].data.shape == (1, 2, 2)


def test_data_browser_renders_parameter_as_one_layer_card(
        grid_file: Path, tmp_path: Path) -> None:
    result = render_file_task(
        str(grid_file), str(tmp_path), channel_cfg=[{
            "display_name": "Z", "aliases": ["Z (m)"],
            "load_by_default": True, "source": "experiment_parameter",
        }],
    )
    thumb = result["thumbs"][0]
    assert thumb["channel_id"] == "Z"
    assert thumb["layer_count"] == 1
    assert thumb["status"] == "ok"
    assert Path(thumb["png_path"]).exists()


def test_unmatched_dialog_displays_source_and_preserves_selected_index(
        grid_file: Path, qapp) -> None:
    del qapp
    dialog = UnmatchedChannelsDialog(
        None, [ChannelConfig("Z", [], True, "either")],
        ["Z (m)", "Z (m)"],
        display_labels=["Channel: Z (m)", "Experiment parameter: Z (m)"],
    )
    combo = dialog._rows[0][0]
    combo.setCurrentIndex(2)
    resolution = dialog.resolutions()[0]
    assert resolution.file_index == 1
    assert resolution.file_channel == "Z (m)"
    dialog.close()


def test_auto_load_saved_alias_also_saves_experiment_source(
        grid_file: Path, qapp, monkeypatch) -> None:
    del qapp
    channel = ChannelConfig("Z", [], True, "either")
    config = FormatChannelConfig("nanonis_3ds", [channel], auto_load=True)
    saved = []
    manager = SimpleNamespace(
        get=lambda _format: config,
        save_format=lambda _format, channels, auto_load: saved.extend(channels),
    )
    context = SimpleNamespace(channel_manager=manager)
    monkeypatch.setattr(UnmatchedChannelsDialog, "exec", lambda _self: 1)
    monkeypatch.setattr(UnmatchedChannelsDialog, "resolutions", lambda _self: [
        UnmatchedResolution(channel, "Scan:Z (m)", len(CHANNELS) + 10, True),
    ])

    result = load_with_channel_picker(grid_file, context)

    assert result.info["field_source"] == "experiment_parameter"
    assert result.info["experiment_parameter_loaded"] == "Scan:Z (m)"
    assert saved[0].source == "experiment_parameter"
    assert saved[0].aliases[0] == "Scan:Z (m)"


def test_channel_manager_dialog_preserves_source_choice(qapp) -> None:
    del qapp
    config = FormatChannelConfig("nanonis_3ds", [
        ChannelConfig("Z", ["Z (m)"], False, "either"),
    ])
    manager = SimpleNamespace(
        all_format_ids=lambda: ["nanonis_3ds"],
        get=lambda _format: config,
    )
    dialog = ChannelManagerDialog(SimpleNamespace(channel_manager=manager))
    combo = dialog._table.cellWidget(0, 2)
    assert combo.currentData() == "either"
    combo.setCurrentIndex(combo.findData("experiment_parameter"))
    assert dialog._collect_channels()[0].source == "experiment_parameter"
    dialog._dirty = False
    dialog.close()
