# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 2026

@author: jiahaoYan

PlanewaveSynthesiser — real-time plane-wave synthesis viewer.

Allows the user to compose a 2-D image as a sum of plane waves:

    f(x,y) = Σ_j  A_j · cos(2π(qx_j·X + qy_j·Y)/size − φ_j)

Each wave is controlled by a WaveVectorRow widget (qx, qy, amplitude, and
phase).  The composite image updates live in an ImageStackViewerWidget on
every parameter change.

The actual sinusoidal kernel comes from the registered process
``simulate.sinusoidal2d`` (angstrompro.algorithms.simulate._sinusoidal2d)
so the math is identical to what the process produces.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from angstrompro.utils.qt_compat import (
    QtCore,
    QtWidgets,
    ScrollBarAlwaysOn,
    Signal,
)
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.widgets.image_stack_viewer_widget import ImageStackViewerWidget
from angstrompro.gui.widgets.math_label import MathLabel
from angstrompro.gui.widgets.preferences import PrefSection, PrefItem
import angstrompro.gui.widgets.preferences.widgets  # noqa: F401 - registers widgets

# reuse the inlined kernel from simulate.py — no duplication
from angstrompro.algorithms.simulate import _sinusoidal2d


_SOURCE = "planewave_synthesiser"
_RECIPE_INFO_KEY = "planewave"
_RECIPE_SCHEMA_VERSION = 2
_SUPPORTED_RECIPE_SCHEMA_VERSIONS = frozenset({1, _RECIPE_SCHEMA_VERSION})
_SYNTHESIS_EQUATION = (
    r"$f(x,y)=\sum_j A_j\cos\!\left["
    r"\frac{2\pi}{N}\left(q_{x,j}x+q_{y,j}y\right)-\phi_j"
    r"\right]$"
)


@dataclass(frozen=True)
class WaveVectorSettings:
    """Serializable state for one plane-wave control group."""

    qx: float = 0.0
    qy: float = 0.0
    amplitude: float = 1.0
    phase: float = 0.0


def _normalise_phase(value: float) -> float:
    """Return an equivalent phase in the principal interval [-pi, pi]."""
    if -np.pi <= value <= np.pi:
        return float(value)
    phase = float(np.arctan2(np.sin(value), np.cos(value)))
    # Preserve positive pi at the upper endpoint instead of displaying -pi.
    if np.isclose(phase, -np.pi) and value > 0:
        return float(np.pi)
    return phase


def _wave_settings_to_recipe(
    image_size: int,
    waves: tuple[WaveVectorSettings, ...],
) -> dict:
    return {
        "schema_version": _RECIPE_SCHEMA_VERSION,
        "image_size": image_size,
        "waves": [
            {
                "qx": wave.qx,
                "qy": wave.qy,
                "amplitude": wave.amplitude,
                "phase": _normalise_phase(wave.phase),
            }
            for wave in waves
        ],
    }


def _recipe_to_wave_settings(
    recipe,
) -> tuple[int, tuple[WaveVectorSettings, ...]]:
    if not isinstance(recipe, Mapping):
        raise ValueError("The planewave synthesis recipe is missing.")
    schema_version = recipe.get("schema_version")
    if schema_version not in _SUPPORTED_RECIPE_SCHEMA_VERSIONS:
        raise ValueError(
            "This planewave synthesis recipe uses an unsupported schema version."
        )

    def integer_value(
        document,
        key: str,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        value = document.get(key)
        if isinstance(value, (bool, np.bool_)):
            raise ValueError(f"Invalid planewave recipe value: {key}")
        try:
            result = int(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Invalid planewave recipe value: {key}") from exc
        if result != value or not minimum <= result <= maximum:
            raise ValueError(f"Invalid planewave recipe value: {key}")
        return result

    def finite_number(document, key: str, default: float) -> float:
        try:
            value = float(document.get(key, default))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid planewave recipe value: {key}") from exc
        if not np.isfinite(value):
            raise ValueError(f"Planewave recipe value must be finite: {key}")
        return value

    image_size = integer_value(
        recipe,
        "image_size",
        minimum=16,
        maximum=4096,
    )
    wave_documents = recipe.get("waves")
    if not isinstance(wave_documents, list):
        raise ValueError("The planewave synthesis recipe has no wave list.")
    if len(wave_documents) > 50:
        raise ValueError("The planewave synthesis recipe contains too many waves.")

    defaults = WaveVectorSettings()
    waves: list[WaveVectorSettings] = []
    for document in wave_documents:
        if not isinstance(document, Mapping):
            raise ValueError("Invalid planewave recipe wave entry.")
        qx = finite_number(document, "qx", defaults.qx)
        qy = finite_number(document, "qy", defaults.qy)
        if schema_version == 1:
            amplitude_min = finite_number(document, "amplitude_min", 0.0)
            amplitude_max = finite_number(document, "amplitude_max", 1.0)
            amplitude_slider = integer_value(
                document, "amplitude_slider", minimum=0, maximum=100)
            phase_min = finite_number(document, "phase_min", -3.14)
            phase_max = finite_number(document, "phase_max", 3.14)
            phase_slider = integer_value(
                document, "phase_slider", minimum=0, maximum=100)
            amplitude = round(
                (amplitude_max - amplitude_min)
                * (amplitude_slider / 100.0)
                + amplitude_min,
                6,
            )
            phase = round(
                (phase_max - phase_min) * (phase_slider / 100.0)
                + phase_min,
                6,
            )
        else:
            amplitude = finite_number(
                document, "amplitude", defaults.amplitude)
            phase = finite_number(document, "phase", defaults.phase)
        waves.append(WaveVectorSettings(
            qx=qx,
            qy=qy,
            amplitude=amplitude,
            phase=_normalise_phase(phase),
        ))
    return image_size, tuple(waves)


def _make_planewave_uds(
    image: np.ndarray,
    image_size: int,
    waves: tuple[WaveVectorSettings, ...],
    *,
    name: str,
) -> UdsDataStru:
    return UdsDataStru(
        name=name,
        data=np.asarray(image, dtype=np.float64)[np.newaxis, :, :].copy(),
        axes=[
            Axis(values=np.array([0.0]), label="Layer", units=""),
            Axis(
                values=np.arange(image_size, dtype=np.float64),
                label="Row",
                units="px",
            ),
            Axis(
                values=np.arange(image_size, dtype=np.float64),
                label="Column",
                units="px",
            ),
        ],
        info={
            "source": _SOURCE,
            _RECIPE_INFO_KEY: _wave_settings_to_recipe(image_size, waves),
        },
        proc_history=[],
    )


# ─────────────────────────────────────────────────────────────────────────────
# WaveVectorRow  — one row of controls per wave component
# ─────────────────────────────────────────────────────────────────────────────

class WaveVectorRow(QtWidgets.QWidget):
    """Controls for a single plane wave (qx, qy, amplitude, phase)."""

    paramsChanged = Signal(int)   # emits own index

    def __init__(self, index: int, parent=None) -> None:
        super().__init__(parent)
        self._index = index
        self.qx        = 0.0
        self.qy        = 0.0
        self.amplitude = 1.0
        self.phase     = 0.0
        self._build_ui()

    # ── construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 8)
        outer.setSpacing(5)

        heading = QtWidgets.QLabel(f"Q{self._index + 1}")
        heading.setProperty("typographyRole", "heading")
        outer.addWidget(heading)

        vector_row = QtWidgets.QHBoxLayout()
        vector_row.setSpacing(5)
        vector_row.addWidget(QtWidgets.QLabel("qx"))
        self._le_qx = QtWidgets.QLineEdit("0")
        self._le_qx.setFixedWidth(82)
        self._le_qx.editingFinished.connect(self._on_qx)
        vector_row.addWidget(self._le_qx)
        vector_row.addSpacing(12)
        vector_row.addWidget(QtWidgets.QLabel("qy"))
        self._le_qy = QtWidgets.QLineEdit("0")
        self._le_qy.setFixedWidth(82)
        self._le_qy.editingFinished.connect(self._on_qy)
        vector_row.addWidget(self._le_qy)
        vector_row.addSpacing(12)
        vector_row.addWidget(QtWidgets.QLabel("A"))
        self._sb_amplitude = QtWidgets.QDoubleSpinBox()
        self._sb_amplitude.setRange(-1.0e12, 1.0e12)
        self._sb_amplitude.setDecimals(6)
        self._sb_amplitude.setSingleStep(0.01)
        self._sb_amplitude.setValue(1.0)
        self._sb_amplitude.setKeyboardTracking(False)
        self._sb_amplitude.setMinimumWidth(140)
        self._sb_amplitude.valueChanged.connect(self._on_amplitude)
        vector_row.addWidget(self._sb_amplitude)
        vector_row.addStretch()
        outer.addLayout(vector_row)

        phase_row = QtWidgets.QHBoxLayout()
        phase_row.setSpacing(5)
        phase_row.addWidget(QtWidgets.QLabel("φ"))
        self._cb_phase_unit = QtWidgets.QComboBox()
        self._cb_phase_unit.addItems(["rad", "deg"])
        self._cb_phase_unit.setFixedWidth(
            max(88, self._cb_phase_unit.sizeHint().width() + 12))
        phase_row.addWidget(self._cb_phase_unit)
        self._sb_phase = QtWidgets.QDoubleSpinBox()
        self._sb_phase.setDecimals(6)
        self._sb_phase.setWrapping(True)
        self._sb_phase.setKeyboardTracking(False)
        self._sb_phase.setMinimumWidth(140)
        self._sb_phase.valueChanged.connect(self._on_phase)
        phase_row.addWidget(self._sb_phase)
        self._lb_phase_conversion = QtWidgets.QLabel()
        self._lb_phase_conversion.setMinimumWidth(112)
        phase_row.addWidget(self._lb_phase_conversion)
        self._cb_phase_unit.currentTextChanged.connect(
            self._on_phase_unit_changed)
        self._sync_phase_editor()
        phase_row.addStretch()
        outer.addLayout(phase_row)

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_qx(self) -> None:
        try:
            self.qx = float(self._le_qx.text())
        except ValueError:
            pass
        self.paramsChanged.emit(self._index)

    def _on_qy(self) -> None:
        try:
            self.qy = float(self._le_qy.text())
        except ValueError:
            pass
        self.paramsChanged.emit(self._index)

    def _on_amplitude(self, value: float) -> None:
        self.amplitude = float(value)
        self.paramsChanged.emit(self._index)

    def _on_phase(self, value: float) -> None:
        if self._cb_phase_unit.currentText() == "deg":
            self.phase = _normalise_phase(float(np.deg2rad(value)))
        else:
            self.phase = _normalise_phase(float(value))
        self._update_phase_conversion()
        self.paramsChanged.emit(self._index)

    def _on_phase_unit_changed(self, _unit: str) -> None:
        self._sync_phase_editor()

    def _sync_phase_editor(self) -> None:
        with QtCore.QSignalBlocker(self._sb_phase):
            if self._cb_phase_unit.currentText() == "deg":
                self._sb_phase.setRange(-180.0, 180.0)
                self._sb_phase.setSingleStep(1.0)
                self._sb_phase.setValue(float(np.rad2deg(self.phase)))
            else:
                self._sb_phase.setRange(-float(np.pi), float(np.pi))
                self._sb_phase.setSingleStep(0.01)
                self._sb_phase.setValue(self.phase)
        self._update_phase_conversion()

    def _update_phase_conversion(self) -> None:
        if self._cb_phase_unit.currentText() == "deg":
            text = f"= {self.phase:.6f} rad"
        else:
            text = f"= {np.rad2deg(self.phase):.3f}°"
        self._lb_phase_conversion.setText(text)

    def wave_settings(self) -> WaveVectorSettings:
        return WaveVectorSettings(
            qx=self.qx,
            qy=self.qy,
            amplitude=self.amplitude,
            phase=self.phase,
        )

    def set_wave_settings(self, settings: WaveVectorSettings) -> None:
        widgets = (
            self._le_qx,
            self._le_qy,
            self._sb_amplitude,
            self._cb_phase_unit,
            self._sb_phase,
        )
        blockers = [QtCore.QSignalBlocker(widget) for widget in widgets]
        try:
            self.qx = settings.qx
            self.qy = settings.qy
            self.amplitude = settings.amplitude
            self.phase = _normalise_phase(settings.phase)

            self._le_qx.setText(str(settings.qx))
            self._le_qy.setText(str(settings.qy))
            self._sb_amplitude.setValue(self.amplitude)
            self._sync_phase_editor()
        finally:
            del blockers


# ─────────────────────────────────────────────────────────────────────────────
# PlanewaveSynthesiser
# ─────────────────────────────────────────────────────────────────────────────

@register_module
class PlanewaveSynthesiser(AGuiModule):
    """Real-time 2-D plane-wave synthesis module."""

    module_id      = "planewave_synthesiser"
    display_name   = "Planewave Synthesiser"
    category       = "Simulation"
    accepted_types = set()     # no workspace input — generates data internally
    staged_labels  = []
    clearable_slots = set()

    preferences_schema = [
        PrefSection("Color map", "palette", [
            PrefItem("colormap.cmap_palette_list", "", "colormap_picker", full_width=True),
        ]),
        PrefSection("Scale", "adjustments-horizontal", [
            PrefItem("factor.sigma",                    "Sigma",              "number", "σ window for histogram auto-scale"),
            PrefItem("factor.slider_scale_zoom_factor", "Slider zoom factor", "number", "Step size for zoom in/out buttons",
                     kwargs={"min": 0.001, "max": 0.999}),
            PrefItem("factor.canvas_wheel_zoom_sensitivity", "Wheel zoom sensitivity", "number",
                     "Canvas mouse-wheel and trackpad zoom multiplier",
                     kwargs={"min": 0.1, "max": 3.0}),
        ]),
        PrefSection("Canvas", "layout-kanban", [
            PrefItem("canvas.max_canvas_size", "Maximum canvas size", "integer",
                     "Largest square canvas side in pixels",
                     kwargs={"min": 160, "max": 4096}),
            PrefItem("canvas.bias_text",       "Show bias value", "checkbox", "Overlay bias setpoint text on image"),
            PrefItem("canvas.bias_text_color", "Bias text color", "dropdown", "Color of the bias annotation",
                     kwargs={"choices": ["Red", "Green", "Blue", "Yellow", "Black", "White"]}),
        ]),
    ]

    def __init__(self, context, parent=None) -> None:
        # initialise before super().__init__ because AGuiModule calls build_ui() inside it
        self._data_size  = 256
        self._rows: list[WaveVectorRow] = []
        self._wave_cache: list[np.ndarray] = []
        self._sum_data   = np.zeros((self._data_size, self._data_size))
        self._uds        = self._make_uds()
        super().__init__(context, parent)
        self.resize(1100, 680)

    # ── AGuiModule contract ───────────────────────────────────────────────

    def _build_file_menu(self) -> None:
        super()._build_file_menu()
        from angstrompro.gui.utils.image_export import (
            install_export_image_action,
        )

        install_export_image_action(self, self._on_export_image)

    def _on_export_image(self) -> None:
        from angstrompro.gui.utils.image_export import export_image

        export_image(self, self._viewer)

    def build_ui(self) -> None:
        from angstrompro.gui.appearance.colormap_catalog import register_all

        register_all()

        # ── left: image viewer ──────────────────────────────────────────
        self._viewer = ImageStackViewerWidget()
        self._viewer.setMinimumWidth(400)

        # ── right: controls ─────────────────────────────────────────────
        ctrl = QtWidgets.QWidget()
        ctrl.setMinimumWidth(320)
        vbox = QtWidgets.QVBoxLayout(ctrl)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(6)

        # Keep the governing equation at the top of the controls. MathText
        # provides proper sums, fractions, subscripts, and Greek glyphs.
        self._equation_label = MathLabel(_SYNTHESIS_EQUATION)
        self._equation_label.setToolTip("N is the image size in pixels.")
        self._equation_label.setAccessibleDescription(
            "Plane-wave synthesis equation; N is the image size in pixels."
        )
        vbox.addWidget(self._equation_label)

        # size + buttons row
        size_row = QtWidgets.QHBoxLayout()
        size_row.addWidget(QtWidgets.QLabel("Size (px):"))
        self._le_size = QtWidgets.QLineEdit(str(self._data_size))
        self._le_size.setFixedWidth(60)
        self._le_size.editingFinished.connect(self._on_size_changed)
        size_row.addWidget(self._le_size)
        size_row.addStretch()
        vbox.addLayout(size_row)

        edit_row = QtWidgets.QHBoxLayout()
        pb_add = QtWidgets.QPushButton("＋ Add wave")
        pb_add.clicked.connect(self._on_add_wave)
        pb_remove = QtWidgets.QPushButton("－ Remove wave")
        pb_remove.clicked.connect(self._on_remove_wave)
        pb_save = QtWidgets.QPushButton("Save to workspace")
        pb_save.clicked.connect(self._on_save_to_workspace)
        edit_row.addWidget(pb_add)
        edit_row.addWidget(pb_remove)
        vbox.addLayout(edit_row)
        vbox.addWidget(pb_save)

        # scrollable wave-vector list
        self._scroll_content = QtWidgets.QWidget()
        self._scroll_vbox    = QtWidgets.QVBoxLayout(self._scroll_content)
        self._scroll_vbox.setContentsMargins(0, 0, 0, 0)
        self._scroll_vbox.setSpacing(2)
        self._scroll_vbox.addStretch()

        sa = QtWidgets.QScrollArea()
        sa.setWidgetResizable(True)
        sa.setVerticalScrollBarPolicy(ScrollBarAlwaysOn)
        sa.setWidget(self._scroll_content)
        vbox.addWidget(sa, stretch=1)

        # ── splitter ────────────────────────────────────────────────────
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._viewer)
        splitter.addWidget(ctrl)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([720, 360])
        self.setCentralWidget(splitter)

        # apply config (palette, scale, canvas settings)
        self._apply_config_to_panels(self._config)
        self._restore_clean_label_state()
        self._viewer.ui_pb_img_clean_mode.toggled.connect(
            self._save_clean_label_state)
        self._add_rt_colormap_action()

        # seed one wave row so the viewer shows something
        self._add_wave_row()
        self._redraw()

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        pass   # module generates its own data; workspace loading unused

    def _populate_ws_item_context_menu(
        self,
        menu: QtWidgets.QMenu,
        item: WorkspaceItem,
    ) -> None:
        recipe = self._recipe_from_workspace_item(item)
        if recipe is None:
            return
        action = menu.addAction("Restore Planewave setup")
        action.triggered.connect(
            lambda _checked=False: self._restore_planewave_setup(item)
        )

    @staticmethod
    def _recipe_from_workspace_item(item: WorkspaceItem):
        if getattr(item, "type_id", None) != "uds":
            return None
        payload = getattr(item, "payload", None)
        info = getattr(payload, "info", None)
        if not isinstance(info, Mapping):
            return None
        if info.get("source") != _SOURCE:
            return None
        recipe = info.get(_RECIPE_INFO_KEY)
        if not isinstance(recipe, Mapping):
            return None
        if recipe.get("schema_version") not in _SUPPORTED_RECIPE_SCHEMA_VERSIONS:
            return None
        return recipe

    def _restore_planewave_setup(self, item: WorkspaceItem) -> None:
        try:
            recipe = self._recipe_from_workspace_item(item)
            if recipe is None:
                raise ValueError(
                    "This workspace item is not a compatible planewave snapshot."
                )
            image_size, waves = _recipe_to_wave_settings(recipe)
            payload = item.payload
            data = np.asarray(payload.data)
            if (
                data.ndim != 3
                or data.shape[0] < 1
                or data.shape[1] != data.shape[2]
            ):
                raise ValueError(
                    "The planewave snapshot must contain a square image layer."
                )
            if data.shape[1] != image_size:
                raise ValueError(
                    "The planewave recipe and stored image sizes do not match."
                )
            image = np.asarray(data[0], dtype=np.float64).copy()
        except (TypeError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot Restore Planewave Setup",
                str(exc),
            )
            return

        self._data_size = image_size
        with QtCore.QSignalBlocker(self._le_size):
            self._le_size.setText(str(image_size))
        self._replace_wave_rows(waves)

        self._sum_data = image
        self._wave_cache = [
            _sinusoidal2d(
                image_size,
                wave.qx,
                wave.qy,
                wave.phase,
                wave.amplitude,
            )
            for wave in waves
        ]
        self._uds = self._make_uds()
        self._viewer.setUdsData(self._uds)
        self.statusBar().showMessage(
            f"Restored Planewave setup from '{item.display_name}'.",
            8000,
        )

    def _apply_config_to_panels(self, cfg: dict) -> None:
        cmap_list = cfg.get("colormap", {}).get("cmap_palette_list", ["gray"])
        self._viewer.setup_palette(cmap_list)

        factor = cfg.get("factor", {})
        self._viewer.setScaleWidgetSigmaDefault(factor.get("sigma", 5))
        self._viewer.setScaleWidgetZoomFactor(factor.get("slider_scale_zoom_factor", 0.6))
        self._viewer.setCanvasWheelZoomSensitivity(
            factor.get("canvas_wheel_zoom_sensitivity", 1.0))

        canvas = cfg.get("canvas", {})
        self._viewer.setCanvasMaximumSize(canvas.get("max_canvas_size", 600))
        self._viewer.setBiasTextColor(canvas.get("bias_text_color", "Red"))
        self._viewer.setBiasTextShown(canvas.get("bias_text", False))

    def _add_rt_colormap_action(self) -> None:
        self._view_menu.addSeparator()
        self._view_menu.addAction("RT-ColorMap").triggered.connect(
            self._show_rt_colormap)

    def _show_rt_colormap(self) -> None:
        editor = self._viewer.ui_rt_cmp
        editor.setWidgetTitle("RT-CMP  Planewave")
        editor.show()
        editor.raise_()
        editor.activateWindow()

    # ── helpers ───────────────────────────────────────────────────────────

    def _restore_clean_label_state(self) -> None:
        from angstrompro.app.user_data_folder import get_qsettings

        qs = get_qsettings()
        key = f"{self._window_layout_qsettings_prefix()}/view/clean_labels"
        self._viewer.ui_pb_img_clean_mode.setChecked(
            qs.value(key, False, type=bool))

    def _save_clean_label_state(self, *_args) -> None:
        from angstrompro.app.user_data_folder import get_qsettings

        qs = get_qsettings()
        key = f"{self._window_layout_qsettings_prefix()}/view/clean_labels"
        qs.setValue(key, self._viewer.ui_pb_img_clean_mode.isChecked())
        qs.sync()

    def _make_uds(self) -> UdsDataStru:
        return _make_planewave_uds(
            self._sum_data,
            self._data_size,
            self._current_wave_settings(),
            name="planewave_synthesiser",
        )

    def _redraw(self) -> None:
        self._uds.data[0] = self._sum_data
        self._uds.info = {
            "source": _SOURCE,
            _RECIPE_INFO_KEY: _wave_settings_to_recipe(
                self._data_size,
                self._current_wave_settings(),
            ),
        }
        self._viewer.setUdsData(self._uds)

    def _current_wave_settings(self) -> tuple[WaveVectorSettings, ...]:
        return tuple(row.wave_settings() for row in self._rows)

    def _recompute_all(self) -> None:
        n = self._data_size
        self._sum_data = np.zeros((n, n))
        self._wave_cache.clear()
        for row in self._rows:
            wave = _sinusoidal2d(n, row.qx, row.qy, row.phase, row.amplitude)
            self._wave_cache.append(wave)
            self._sum_data += wave
        self._redraw()

    # ── wave row management ───────────────────────────────────────────────

    def _add_wave_row(
        self,
        settings: WaveVectorSettings | None = None,
    ) -> None:
        idx = len(self._rows)
        if idx >= 50:
            return
        row = WaveVectorRow(idx)
        if settings is not None:
            row.set_wave_settings(settings)
        row.paramsChanged.connect(self._on_wave_params_changed)
        self._rows.append(row)
        self._wave_cache.append(np.zeros((self._data_size, self._data_size)))
        # insert before the trailing stretch
        self._scroll_vbox.insertWidget(self._scroll_vbox.count() - 1, row)

    def _replace_wave_rows(
        self,
        waves: tuple[WaveVectorSettings, ...],
    ) -> None:
        for row in self._rows:
            self._scroll_vbox.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self._wave_cache.clear()
        for wave in waves:
            self._add_wave_row(wave)

    def _remove_wave_row(self) -> None:
        if not self._rows:
            return
        row = self._rows.pop()
        wave = self._wave_cache.pop()
        self._sum_data -= wave
        self._scroll_vbox.removeWidget(row)
        row.deleteLater()
        self._redraw()

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_add_wave(self) -> None:
        self._add_wave_row()

    def _on_remove_wave(self) -> None:
        self._remove_wave_row()

    def _on_wave_params_changed(self, index: int) -> None:
        if index >= len(self._rows):
            return
        n    = self._data_size
        row  = self._rows[index]
        new_wave = _sinusoidal2d(n, row.qx, row.qy, row.phase, row.amplitude)

        if index < len(self._wave_cache):
            self._sum_data -= self._wave_cache[index]
            self._wave_cache[index] = new_wave
        else:
            self._wave_cache.append(new_wave)
        self._sum_data += new_wave
        self._redraw()

    def _on_size_changed(self) -> None:
        txt = self._le_size.text().strip()
        if not txt.isdigit():
            return
        n = int(txt)
        if n < 16 or n > 4096:
            return
        self._data_size = n
        self._sum_data  = np.zeros((n, n))
        self._uds       = self._make_uds()
        self._recompute_all()

    def _on_save_to_workspace(self) -> None:
        uds = _make_planewave_uds(
            self._sum_data,
            self._data_size,
            self._current_wave_settings(),
            name="planewave_synthesiser_snapshot",
        )
        self.workspace.add_item(payload=uds)
