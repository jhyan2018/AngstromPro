# -*- coding: utf-8 -*-
"""
ChannelPickerDialog — select values to load from a multi-channel file.

Reads FormatChannelConfig from ChannelManager (via AppContext).  Each logical
channel is shown as a checkbox row; channels with load_by_default=True are
pre-checked.  The matched raw file channel name is shown as a muted subtitle.
Unmatched logical channels are shown greyed out and unchecked.

For .3ds files, experiment parameters are listed alongside sweep channels,
with their binary source and per-pixel value count shown explicitly.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets
from angstrompro.io.channel_manager import ChannelConfig, FormatChannelConfig
from angstrompro.io.formats.nanonis_3ds import GridField, match_field

if TYPE_CHECKING:
    pass


class ChannelPickerDialog(QtWidgets.QDialog):
    """
    Parameters
    ----------
    parent        : parent widget
    file_path     : path shown in the subtitle (display only)
    file_channels : raw channel names from the file header
    file_info     : extra header metadata shown in the subtitle
                    (keys: "x_pixels", "y_pixels", "n_points")
    fmt_cfg       : FormatChannelConfig from ChannelManager (may be None for
                    unknown formats — dialog then shows raw file channels)
    experiment_parameters : optional .3ds per-pixel parameter names; when
                    present, selected_fields() returns typed GridField values
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        file_path:     Path,
        file_channels: list[str],
        file_info:     dict,
        fmt_cfg:       FormatChannelConfig | None,
        experiment_parameters: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Select channels and experiment parameters"
            if experiment_parameters is not None else "Select channels"
        )
        self.setMinimumWidth(420)

        self._experiment_parameters = experiment_parameters
        self._grid_mode = experiment_parameters is not None
        # Resolve matches: each .3ds field retains its source, while other
        # formats keep their existing integer channel indices.
        if self._grid_mode:
            parameters = experiment_parameters or []
            self._resolved = [
                (cc, match_field(cc.aliases, file_channels, parameters, cc.source))
                for cc in fmt_cfg.channels
            ] if fmt_cfg is not None else []
            matched_fields = {field for _, field in self._resolved
                              if field is not None}
            for i, name in enumerate(file_channels):
                field = GridField("channel", i)
                if field not in matched_fields:
                    self._resolved.append((
                        ChannelConfig(name, [name], False, "channel"), field,
                    ))
            for i, name in enumerate(parameters):
                field = GridField("experiment_parameter", i)
                if field not in matched_fields:
                    self._resolved.append((
                        ChannelConfig(name, [name], False,
                                      "experiment_parameter"), field,
                    ))
            if fmt_cfg is None and file_channels:
                self._resolved[0][0].load_by_default = True
        elif fmt_cfg is not None:
            self._resolved = fmt_cfg.resolve(file_channels)
            # Append any file channels not matched by any logical channel
            matched_indices = {idx for _, idx in self._resolved if idx is not None}
            for i, fch in enumerate(file_channels):
                if i not in matched_indices:
                    self._resolved.append((
                        ChannelConfig(fch, [fch], load_by_default=False),
                        i,
                    ))
        else:
            # No config — show all raw file channels
            self._resolved = [
                (ChannelConfig(fch, [fch], load_by_default=(i == 0)), i)
                for i, fch in enumerate(file_channels)
            ]

        self._file_channels = file_channels
        self._checkboxes: list[tuple[QtWidgets.QCheckBox, int | GridField]] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────
        name_lbl = QtWidgets.QLabel(f"<b>{file_path.name}</b>")
        name_lbl.setObjectName("pref_section_title")
        layout.addWidget(name_lbl)

        x   = file_info.get("x_pixels", "?")
        y   = file_info.get("y_pixels", "?")
        pts = file_info.get("n_points", "")
        subtitle_parts = [f"{x}×{y} px"]
        if pts:
            subtitle_parts.append(f"{pts} pts")
        sub_lbl = QtWidgets.QLabel("  ·  ".join(subtitle_parts))
        sub_lbl.setObjectName("pref_row_desc")
        layout.addWidget(sub_lbl)
        if self._grid_mode:
            note = QtWidgets.QLabel(
                "Channels contain sweep spectra; experiment parameters "
                "contain one value per pixel. Check multiple candidates "
                "to compare their resulting maps."
            )
            note.setObjectName("pref_row_desc")
            note.setWordWrap(True)
            layout.addWidget(note)

        # ── Channel rows ──────────────────────────────────────────────
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        inner = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(inner)
        vbox.setSpacing(4)
        vbox.setContentsMargins(0, 0, 0, 0)

        n_file = len(file_channels)
        for cc, file_idx in self._resolved:
            matched = file_idx is not None
            frame = QtWidgets.QFrame()
            frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
            row = QtWidgets.QHBoxLayout(frame)
            row.setContentsMargins(8, 6, 8, 6)
            row.setSpacing(10)

            cb = QtWidgets.QCheckBox()
            cb.setChecked(cc.load_by_default and matched)
            cb.setEnabled(matched)
            row.addWidget(cb)

            info_col = QtWidgets.QVBoxLayout()
            name_label = QtWidgets.QLabel(cc.display_name)
            name_label.setObjectName("pref_row_label")
            if not matched:
                name_label.setEnabled(False)
            info_col.addWidget(name_label)

            if matched:
                if isinstance(file_idx, GridField):
                    is_parameter = file_idx.source == "experiment_parameter"
                    names = (experiment_parameters or []) if is_parameter else file_channels
                    source_label = ("Experiment parameter" if is_parameter
                                    else "Channel")
                    raw_name = names[file_idx.index]
                    source_count = len(names)
                    value_type = ("one value per pixel" if is_parameter
                                  else f"{pts or '?'} sweep values per pixel")
                    position = file_idx.index + 1
                else:
                    source_label = "Channel"
                    raw_name = file_channels[file_idx]
                    source_count = n_file
                    value_type = ""
                    position = file_idx + 1
                raw_lbl = QtWidgets.QLabel(raw_name)
                raw_lbl.setObjectName("pref_row_desc")
                info_col.addWidget(raw_lbl)
                num_lbl = QtWidgets.QLabel(
                    f"{source_label} {position} of {source_count}"
                    + (f" · {value_type}" if value_type else "")
                )
                num_lbl.setObjectName("pref_row_desc")
                info_col.addWidget(num_lbl)
            else:
                no_lbl = QtWidgets.QLabel("not found in this file")
                no_lbl.setObjectName("pref_row_desc")
                no_lbl.setEnabled(False)
                info_col.addWidget(no_lbl)

            row.addLayout(info_col)
            row.addStretch()

            vbox.addWidget(frame)
            if matched:
                self._checkboxes.append((cb, file_idx))

        vbox.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # ── Buttons ───────────────────────────────────────────────────
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Load")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected_indices(self) -> list[int]:
        """Return file-channel indices for all checked channels, in file order."""
        return sorted(
            idx for cb, idx in self._checkboxes
            if cb.isChecked() and isinstance(idx, int)
        )

    def selected_fields(self) -> list[GridField]:
        """Return checked .3ds fields with their binary source intact."""
        fields = [field for cb, field in self._checkboxes
                  if cb.isChecked() and isinstance(field, GridField)]
        return sorted(fields,
                      key=lambda field: (field.source != "channel", field.index))
