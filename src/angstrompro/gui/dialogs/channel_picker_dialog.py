# -*- coding: utf-8 -*-
"""
ChannelPickerDialog — select which channels to load from a multi-channel file.

Reads FormatChannelConfig from ChannelManager (via AppContext).  Each logical
channel is shown as a checkbox row; channels with load_by_default=True are
pre-checked.  The matched raw file channel name is shown as a muted subtitle.
Unmatched logical channels are shown greyed out and unchecked.

Returns a list of (channel_config, file_channel_index) pairs for every checked
channel whose alias matched a file channel.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets
from angstrompro.io.channel_manager import ChannelConfig, FormatChannelConfig

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
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        file_path:     Path,
        file_channels: list[str],
        file_info:     dict,
        fmt_cfg:       FormatChannelConfig | None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select channels")
        self.setMinimumWidth(420)

        # Resolve matches: list of (ChannelConfig, file_idx | None)
        if fmt_cfg is not None:
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
        self._checkboxes: list[tuple[QtWidgets.QCheckBox, int]] = []  # (cb, file_idx)

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
                raw_lbl = QtWidgets.QLabel(file_channels[file_idx])
                raw_lbl.setObjectName("pref_row_desc")
                info_col.addWidget(raw_lbl)
                num_lbl = QtWidgets.QLabel(f"channel {file_idx + 1} of {n_file}")
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
            idx for cb, idx in self._checkboxes if cb.isChecked()
        )
