# -*- coding: utf-8 -*-
"""
UnmatchedChannelsDialog — shown during auto-load when one or more default
channels could not be matched against the file's channel list.

For each unmatched logical channel the user can:
  - Pick a file channel from a dropdown  (maps it for this load)
  - Check "Save alias" to prepend that file channel name to the logical
    channel's alias list in ChannelManager, so it never asks again
  - Leave the dropdown on "— skip —" to omit that channel from this load

Returns a list of UnmatchedResolution namedtuples via .resolutions().
"""
from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

from angstrompro.utils.qt_compat import QtWidgets
from angstrompro.io.channel_manager import ChannelConfig

if TYPE_CHECKING:
    pass

_SKIP = "— skip —"


class UnmatchedResolution(NamedTuple):
    channel_config: ChannelConfig
    file_channel:   str | None   # None = skipped
    file_index:     int | None   # index into file_channels list
    save_alias:     bool


class UnmatchedChannelsDialog(QtWidgets.QDialog):
    """
    Parameters
    ----------
    parent          : parent widget
    unmatched       : list of ChannelConfig whose aliases found no match
    file_channels   : full ordered list of raw channel names from the file
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        unmatched: list[ChannelConfig],
        file_channels: list[str],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Unmatched channels")
        self.setMinimumWidth(520)

        self._unmatched = unmatched
        self._file_channels = file_channels
        self._rows: list[tuple[QtWidgets.QComboBox, QtWidgets.QCheckBox]] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────
        hdr = QtWidgets.QLabel(
            "<b>Some default channels were not found in this file.</b><br>"
            "Select the matching file channel for each, or skip."
        )
        hdr.setWordWrap(True)
        layout.addWidget(hdr)

        # ── Available channels info ───────────────────────────────────
        avail_lbl = QtWidgets.QLabel(
            "Available in file:  " + ",  ".join(file_channels)
        )
        avail_lbl.setObjectName("pref_row_desc")
        avail_lbl.setWordWrap(True)
        layout.addWidget(avail_lbl)

        # ── One row per unmatched channel ─────────────────────────────
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(1, 1)

        for row_idx, cc in enumerate(unmatched):
            name_lbl = QtWidgets.QLabel(cc.display_name)
            name_lbl.setObjectName("pref_row_label")

            combo = QtWidgets.QComboBox()
            combo.addItem(_SKIP)
            for fch in file_channels:
                combo.addItem(fch)

            save_cb = QtWidgets.QCheckBox("Save alias")
            save_cb.setToolTip(
                "Prepend this file channel name to the alias list so it "
                "auto-matches next time."
            )
            save_cb.setChecked(True)

            grid.addWidget(name_lbl, row_idx, 0)
            grid.addWidget(combo,    row_idx, 1)
            grid.addWidget(save_cb,  row_idx, 2)
            self._rows.append((combo, save_cb))

        layout.addLayout(grid)

        # ── Buttons ───────────────────────────────────────────────────
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Load")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def resolutions(self) -> list[UnmatchedResolution]:
        """Call after exec() == Accepted to get the user's choices."""
        result: list[UnmatchedResolution] = []
        for cc, (combo, save_cb) in zip(self._unmatched, self._rows):
            text = combo.currentText()
            if text == _SKIP:
                result.append(UnmatchedResolution(cc, None, None, False))
            else:
                idx = self._file_channels.index(text)
                result.append(UnmatchedResolution(cc, text, idx, save_cb.isChecked()))
        return result
