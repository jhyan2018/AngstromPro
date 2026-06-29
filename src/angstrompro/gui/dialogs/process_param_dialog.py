# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 2026

@author: jiahaoYan

ProcessParamDialog — parameter entry dialog for a single registered process.

Builds an editable form from ProcessSchema.params, loads last-used values
from ParamHistoryManager, and returns the confirmed param dict to the caller.

The "Run" button saves params to history (when "Remember parameters" is
checked) and accepts the dialog. Actual process submission is handled by the
caller — this dialog only owns parameter collection.

Usage
-----
    entry = context.processes.get("spatial.crop2d")
    dlg   = ProcessParamDialog(entry, context, parent=self)
    if dlg.exec():
        params = dlg.params()
        # TODO: submit_process(entry.name, input_items, params)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from angstrompro.utils.qt_compat import QtCore, QtWidgets

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext
    from angstrompro.core.processes.process_entry import ProcessEntry
    from angstrompro.core.processes.param_schema import ParameterSpec


class ProcessParamDialog(QtWidgets.QDialog):

    def __init__(
        self,
        entry:   "ProcessEntry",
        context: "AppContext",
        parent:  QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._entry   = entry
        self._context = context
        self._widgets: dict[str, QtWidgets.QWidget] = {}

        self.setWindowTitle(entry.label)
        self.setMinimumWidth(380)
        self._setup_ui()
        self._load_values()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # description (hidden if empty)
        if self._entry.description:
            lbl = QtWidgets.QLabel(self._entry.description)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: grey; font-size: 10px;")
            root.addWidget(lbl)
            root.addWidget(_hline())

        # parameter form
        if self._entry.schema.params:
            form_widget = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(form_widget)
            form.setContentsMargins(0, 0, 0, 0)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(6)

            for spec in self._entry.schema.params:
                widget = _make_widget(spec)
                self._widgets[spec.name] = widget

                row_label = spec.label or spec.name
                if spec.units:
                    row_label += f"  ({spec.units})"

                if spec.description:
                    widget.setToolTip(spec.description)

                form.addRow(row_label + ":", widget)

            root.addWidget(form_widget)
        else:
            root.addWidget(QtWidgets.QLabel("This process has no parameters."))

        root.addWidget(_hline())

        # remember checkbox
        self._remember_cb = QtWidgets.QCheckBox("Remember these parameters")
        self._remember_cb.setChecked(True)
        root.addWidget(self._remember_cb)

        # buttons
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_reset = QtWidgets.QPushButton("Reset to defaults")
        self._btn_reset.clicked.connect(self._reset_to_defaults)
        btn_row.addWidget(self._btn_reset)
        btn_row.addStretch()

        btn_box = QtWidgets.QDialogButtonBox()
        self._btn_run = btn_box.addButton(
            "Run", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._on_run)
        btn_box.rejected.connect(self.reject)
        btn_row.addWidget(btn_box)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Value loading
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        """Populate widgets from ParamHistoryManager (falls back to schema defaults)."""
        defaults = self._entry.schema.defaults()
        values   = self._context.param_history.get(self._entry.name, defaults)
        self._apply_values(values)

    def _reset_to_defaults(self) -> None:
        self._apply_values(self._entry.schema.defaults())

    def _apply_values(self, values: dict[str, Any]) -> None:
        for spec in self._entry.schema.params:
            widget = self._widgets.get(spec.name)
            value  = values.get(spec.name, spec.default)
            if widget is None:
                continue
            _set_widget_value(widget, spec, value)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def params(self) -> dict[str, Any]:
        """Return the current param values as a plain dict."""
        result: dict[str, Any] = {}
        for spec in self._entry.schema.params:
            widget = self._widgets.get(spec.name)
            if widget is not None:
                result[spec.name] = _get_widget_value(widget, spec)
        return result

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def _on_run(self) -> None:
        collected = self.params()
        if self._remember_cb.isChecked():
            self._context.param_history.save(self._entry.name, collected)
        self.accept()


# ---------------------------------------------------------------------------
# Widget factory
# ---------------------------------------------------------------------------

def _make_widget(spec: "ParameterSpec") -> QtWidgets.QWidget:
    """Create the appropriate Qt widget for a ParameterSpec."""

    if spec.choices:
        w = QtWidgets.QComboBox()
        for choice in spec.choices:
            w.addItem(str(choice), choice)
        return w

    if spec.type is bool:
        return QtWidgets.QCheckBox()

    if spec.type is int:
        w = QtWidgets.QSpinBox()
        w.setRange(
            int(spec.min) if spec.min is not None else -2_147_483_648,
            int(spec.max) if spec.max is not None else  2_147_483_647,
        )
        if spec.step is not None:
            w.setSingleStep(int(spec.step))
        return w

    if spec.type is float:
        w = QtWidgets.QDoubleSpinBox()
        w.setDecimals(6)
        w.setRange(
            float(spec.min) if spec.min is not None else -1e18,
            float(spec.max) if spec.max is not None else  1e18,
        )
        if spec.step is not None:
            w.setSingleStep(float(spec.step))
        else:
            # auto step: 1% of range, or 0.01 if range is huge/unknown
            if spec.min is not None and spec.max is not None:
                rng = abs(float(spec.max) - float(spec.min))
                w.setSingleStep(rng / 100.0 if rng > 0 else 0.01)
            else:
                w.setSingleStep(0.01)
        return w

    # str fallback
    return QtWidgets.QLineEdit()


def _set_widget_value(
    widget: QtWidgets.QWidget,
    spec:   "ParameterSpec",
    value:  Any,
) -> None:
    if spec.choices:
        idx = widget.findData(value)
        if idx >= 0:
            widget.setCurrentIndex(idx)
        else:
            # fallback: match by string
            idx = widget.findText(str(value))
            if idx >= 0:
                widget.setCurrentIndex(idx)
        return

    if spec.type is bool:
        state = (QtCore.Qt.CheckState.Checked if value
                 else QtCore.Qt.CheckState.Unchecked)
        widget.setCheckState(state)
        return

    if spec.type is int:
        widget.setValue(int(value))
        return

    if spec.type is float:
        widget.setValue(float(value))
        return

    # str
    widget.setText(str(value))


def _get_widget_value(widget: QtWidgets.QWidget, spec: "ParameterSpec") -> Any:
    if spec.choices:
        return widget.currentData()

    if spec.type is bool:
        checked = (QtCore.Qt.CheckState.Checked
                   if hasattr(QtCore.Qt.CheckState, "Checked")
                   else QtCore.Qt.Checked)
        return widget.checkState() == checked

    if spec.type is int:
        return widget.value()

    if spec.type is float:
        return widget.value()

    # str
    return widget.text()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine
                       if hasattr(QtWidgets.QFrame.Shape, "HLine")
                       else QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken
                        if hasattr(QtWidgets.QFrame.Shadow, "Sunken")
                        else QtWidgets.QFrame.Sunken)
    return line
