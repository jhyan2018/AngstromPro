# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 2026

@author: jiahaoYan

LiveModuleCard — compact card widget for one live module instance.

Displays:
  - Category colour strip on the left
  - Display name + instance_id
  - Category badge
  - Workspace item count
  - process_inputs count
  - Task status indicator (Idle / Running / Error)
  - Show and Remove quick-action buttons

Call refresh() to update counts and status without rebuilding the card.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QtGui

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext
    from angstrompro.core.modules.module_mixin import ModuleMixin

# Category → left-strip colour (hashed from category name if not in table)
_CATEGORY_COLOURS: dict[str, str] = {
    "Test":        "#7c6af7",
    "Imaging":     "#3fa7d6",
    "Analysis":    "#f4a261",
    "Spectroscopy":"#57cc99",
    "Main Workbench": "#888888",
}

_STATUS_COLOURS = {
    "Idle":    "#57cc99",
    "Running": "#f4a261",
    "Error":   "#e63946",
}


def _category_colour(category: str) -> str:
    if category in _CATEGORY_COLOURS:
        return _CATEGORY_COLOURS[category]
    # deterministic colour from hash
    h = abs(hash(category)) % 360
    return f"hsl({h}, 60%, 55%)"


class LiveModuleCard(QtWidgets.QFrame):

    sig_show   = QtCore.Signal(str)   # instance_id
    sig_remove = QtCore.Signal(str)   # instance_id

    def __init__(
        self,
        instance:  "ModuleMixin",
        context:   "AppContext",
        parent:    QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._instance = instance
        self._context  = context
        self._status   = "Idle"

        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.setMinimumHeight(130)
        self.setMaximumHeight(155)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._setup_ui()
        self.refresh()

        # Track tasks from this instance
        context.tasks.task_submitted.connect(self._on_task_submitted)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 12, 0)
        outer.setSpacing(8)

        # coloured left strip
        self._strip = QtWidgets.QFrame()
        self._strip.setFixedWidth(6)
        colour = _category_colour(self._instance.category)
        self._strip.setStyleSheet(f"background-color: {colour}; border: none;")
        outer.addWidget(self._strip)

        # main content
        content = QtWidgets.QVBoxLayout()
        content.setContentsMargins(0, 6, 0, 6)
        content.setSpacing(2)

        # top row: alias/instance_id (double-click to edit alias)
        top_row = QtWidgets.QHBoxLayout()

        self._alias: str = ""
        self._lbl_name = QtWidgets.QLabel()
        self._lbl_name.setObjectName("card_instance_label")
        self._lbl_name.setTextFormat(
            QtCore.Qt.TextFormat.RichText
            if hasattr(QtCore.Qt.TextFormat, "RichText")
            else QtCore.Qt.RichText
        )
        self._lbl_name.setToolTip("Double-click to set an alias")
        self._update_name_label()

        self._edit_name = QtWidgets.QLineEdit()
        self._edit_name.setObjectName("card_instance_label")
        self._edit_name.setVisible(False)
        self._edit_name.returnPressed.connect(self._commit_alias)
        self._edit_name.editingFinished.connect(self._commit_alias)

        self._lbl_name.mouseDoubleClickEvent = lambda _e: self._start_edit()

        top_row.addWidget(self._lbl_name)
        top_row.addWidget(self._edit_name)
        top_row.addStretch()
        content.addLayout(top_row)

        # middle row: accepted type + ndim + workspace count
        mid_row = QtWidgets.QHBoxLayout()
        mid_row.setSpacing(10)

        accepted = getattr(self._instance, "accepted_types", None)
        if accepted:
            type_str = ", ".join(sorted(accepted))
        else:
            type_str = "any"
        ndim     = getattr(self._instance, "accepted_ndim", None)
        ndim_str = f"{ndim}D" if ndim is not None else "any dim"
        meta_text = f"accepts: {type_str}  •  {ndim_str}"

        self._lbl_ws = QtWidgets.QLabel()
        self._lbl_ws.setObjectName("card_info_label")
        mid_row.addWidget(self._lbl_ws)

        sep = QtWidgets.QLabel("•")
        sep.setObjectName("card_info_label")
        mid_row.addWidget(sep)

        lbl_meta = QtWidgets.QLabel(meta_text)
        lbl_meta.setObjectName("card_info_label")
        mid_row.addWidget(lbl_meta)

        mid_row.addStretch()

        content.addLayout(mid_row)

        # bottom row: status + buttons
        bot_row = QtWidgets.QHBoxLayout()
        bot_row.setSpacing(10)

        self._lbl_status = QtWidgets.QLabel()
        self._lbl_status.setObjectName("card_status_label")
        bot_row.addWidget(self._lbl_status)

        bot_row.addStretch()

        btn_show = QtWidgets.QPushButton("Show")
        btn_show.setObjectName("card_action_btn")
        btn_show.setMinimumSize(100, 38)
        btn_show.clicked.connect(
            lambda: self.sig_show.emit(self._instance.instance_id))

        btn_remove = QtWidgets.QPushButton("Remove")
        btn_remove.setObjectName("card_action_btn")
        btn_remove.setMinimumSize(120, 38)
        btn_remove.clicked.connect(
            lambda: self.sig_remove.emit(self._instance.instance_id))

        bot_row.addWidget(btn_show)
        bot_row.addWidget(btn_remove)
        content.addLayout(bot_row)

        outer.addLayout(content)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Update counts and status label. Call after workspace or task changes."""
        ws_count = len(self._instance.workspace.list_items())
        self._lbl_ws.setText(f"workspace: {ws_count}")

        colour = _STATUS_COLOURS.get(self._status, "grey")
        self._lbl_status.setText(f"● {self._status}")
        self._lbl_status.setStyleSheet(
            f"QLabel#card_status_label {{ color: {colour}; font-weight: bold; }}")

    def _update_name_label(self) -> None:
        iid = self._instance.instance_id
        if self._alias:
            self._lbl_name.setText(
                f"<b>{self._alias}</b>"
                f"  <span style='color:grey;font-size:9pt'>({iid})</span>")
        else:
            self._lbl_name.setText(f"<b>{iid}</b>")

    def _start_edit(self) -> None:
        self._edit_name.setText(self._alias or self._instance.instance_id)
        self._edit_name.setVisible(True)
        self._lbl_name.setVisible(False)
        self._edit_name.setFocus()
        self._edit_name.selectAll()

    def _commit_alias(self) -> None:
        text = self._edit_name.text().strip()
        self._alias = "" if text == self._instance.instance_id else text
        self._edit_name.setVisible(False)
        self._lbl_name.setVisible(True)
        self._update_name_label()

    @property
    def instance_id(self) -> str:
        return self._instance.instance_id

    # ------------------------------------------------------------------
    # Task observation
    # ------------------------------------------------------------------

    def _on_task_submitted(self, request, handle) -> None:
        if request.source_id != self._instance.instance_id:
            return
        Q = QtCore.Qt.ConnectionType.QueuedConnection
        handle.started.connect(
            lambda _tid: self._set_status("Running"), Q)
        handle.result.connect(
            lambda _tid, _r: self._set_status("Idle"), Q)
        handle.error.connect(
            lambda _tid, _e: self._set_status("Error"), Q)
        handle.cancelled.connect(
            lambda _tid: self._set_status("Idle"), Q)

    def _set_status(self, status: str) -> None:
        self._status = status
        self.refresh()
