"""Small GUI module that exercises the example processes through TaskManager."""

from __future__ import annotations

from angstrompro.core.modules import AGuiModule, register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.utils.qt_compat import QtWidgets


@register_module
class ExampleWorkflowModule(AGuiModule):
    module_id = "angstrompro_example.workflow"
    display_name = "Example Workflow"
    category = "Examples"
    description = "Generate synthetic data and run a plugin process."
    accepted_types = {"uds"}
    accepted_ndim = 3
    max_instances = 1
    staged_labels = ["Input"]
    default_process_menu = ["angstrompro_example.scale_2D"]
    default_simulate_menu = ["angstrompro_example.gaussian_stack"]

    def build_ui(self) -> None:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)

        heading = QtWidgets.QLabel("AngstromPro example plugin")
        heading.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(heading)

        instructions = QtWidgets.QLabel(
            "Generate synthetic data, double-click a workspace item to make it "
            "active, then scale it through the registered process. Both actions "
            "run through AngstromPro's task system."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        generate_button = QtWidgets.QPushButton("Generate synthetic data")
        generate_button.clicked.connect(self._generate)
        layout.addWidget(generate_button)

        factor_row = QtWidgets.QHBoxLayout()
        factor_row.addWidget(QtWidgets.QLabel("Scale factor:"))
        self._factor = QtWidgets.QDoubleSpinBox()
        self._factor.setRange(-1_000_000.0, 1_000_000.0)
        self._factor.setDecimals(3)
        self._factor.setValue(2.0)
        factor_row.addWidget(self._factor)
        scale_button = QtWidgets.QPushButton("Scale active data")
        scale_button.clicked.connect(self._scale_active)
        factor_row.addWidget(scale_button)
        layout.addLayout(factor_row)

        self._summary = QtWidgets.QLabel("No active input.")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)
        layout.addStretch()
        self.setCentralWidget(panel)

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        if getattr(item.payload, "data", None) is None or item.payload.data.ndim != 3:
            QtWidgets.QMessageBox.warning(
                self,
                "Unsupported item",
                "The example workflow requires a three-dimensional UDS image stack.",
            )
            return
        self.process_inputs = [item]
        self._summary.setText(
            f"Active input: {item.name} — shape {item.payload.data.shape}, "
            f"dtype {item.payload.data.dtype}"
        )

    def _generate(self) -> None:
        self.submit_process(
            "angstrompro_example.gaussian_stack",
            [],
            {"size": 96, "sigma": 14.0},
        )

    def _scale_active(self) -> None:
        if not self.process_inputs:
            QtWidgets.QMessageBox.information(
                self,
                "Select input",
                "Generate or send data, then double-click its workspace item first.",
            )
            return
        self.submit_process(
            "angstrompro_example.scale_2D",
            [self.process_inputs[0]],
            {"factor": self._factor.value()},
        )
