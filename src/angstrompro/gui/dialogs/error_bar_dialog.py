"""Configure symmetric Y-error bars for a Curve Stack dataset."""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtGui, QtWidgets


class ErrorBarDialog(QtWidgets.QDialog):
    """Select a compatible error UDS and its presentation settings."""

    def __init__(self, target_name: str, candidates: list[tuple[str, object]],
                 current_style=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Error Bars")
        self.setMinimumWidth(430)
        self._color = str(getattr(current_style, "ecolor", "") or "#666666")

        layout = QtWidgets.QVBoxLayout(self)
        hint = QtWidgets.QLabel(
            f"Attach symmetric Y uncertainty to <b>{target_name}</b>.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QtWidgets.QFormLayout()
        self._source = QtWidgets.QComboBox()
        current_name = str(getattr(
            getattr(current_style, "yerr_data", None), "name", ""))
        selected_index = 0
        for index, (label, payload) in enumerate(candidates):
            self._source.addItem(label, payload)
            if current_name and getattr(payload, "name", "") == current_name:
                selected_index = index
        self._source.setCurrentIndex(selected_index)
        form.addRow("Y-error data:", self._source)

        self._capsize = QtWidgets.QDoubleSpinBox()
        self._capsize.setRange(0.0, 50.0)
        self._capsize.setDecimals(1)
        self._capsize.setSingleStep(0.5)
        self._capsize.setSuffix(" pt")
        current_capsize = getattr(current_style, "capsize", None)
        self._capsize.setValue(float(
            3.0 if current_capsize is None else current_capsize))
        form.addRow("Cap size:", self._capsize)

        self._linewidth = QtWidgets.QDoubleSpinBox()
        self._linewidth.setRange(0.1, 20.0)
        self._linewidth.setDecimals(1)
        self._linewidth.setSingleStep(0.2)
        self._linewidth.setValue(float(
            getattr(current_style, "linewidth", None) or 1.0))
        form.addRow("Error width:", self._linewidth)

        self._every = QtWidgets.QSpinBox()
        self._every.setRange(1, 1_000_000)
        self._every.setValue(max(
            1, int(getattr(current_style, "errorevery", 1) or 1)))
        self._every.setToolTip(
            "Draw one error bar every N data points; 1 draws every point")
        form.addRow("Every N points:", self._every)

        color_row = QtWidgets.QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        self._match_color = QtWidgets.QCheckBox("Match curve")
        self._match_color.setChecked(
            not bool(getattr(current_style, "ecolor", "")))
        self._match_color.toggled.connect(self._on_match_color_changed)
        color_row.addWidget(self._match_color)
        self._color_button = QtWidgets.QPushButton()
        self._color_button.setFixedSize(52, 24)
        self._color_button.setToolTip("Choose a fixed error-bar color")
        self._color_button.clicked.connect(self._choose_color)
        color_row.addWidget(self._color_button)
        color_row.addStretch()
        form.addRow("Color:", color_row)
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_color_button()
        self._on_match_color_changed(self._match_color.isChecked())

    def _choose_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self._color), self, "Choose Error-Bar Color")
        if color.isValid():
            self._color = color.name()
            self._refresh_color_button()

    def _refresh_color_button(self) -> None:
        self._color_button.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #888;")

    def _on_match_color_changed(self, checked: bool) -> None:
        self._color_button.setEnabled(not checked)

    def selected_error_data(self):
        return self._source.currentData()

    def settings(self) -> dict:
        return {
            "capsize": self._capsize.value(),
            "linewidth": self._linewidth.value(),
            "ecolor": "" if self._match_color.isChecked() else self._color,
            "errorevery": self._every.value(),
        }
