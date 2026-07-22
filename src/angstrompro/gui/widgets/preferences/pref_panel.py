"""
PreferencesPanel — uniform sidebar + section-cards preferences UI.

Font sizes are NOT set here. They inherit from the app font (set in
ThemeManager) and are selectively adjusted via object-name QSS rules
added by ThemeManager._apply_font().

Usage
-----
    panel = PreferencesPanel(
        module_name = "Image Stack Viewer",
        schema      = ImageStackViewer.preferences_schema,
        config      = copy.deepcopy(self._config),
        on_apply    = lambda cfg: ...,
        on_save_as_default = lambda cfg: ...,
        parent      = dlg,
    )
"""
from __future__ import annotations

import copy
from typing import Callable

from angstrompro.utils.qt_compat import QtCore, QtGui, QtWidgets, IS_QT6
from .pref_schema import PrefSection, PrefItem, get_widget_class

# ── built-in control wrappers ──────────────────────────────────────────────────

class _CheckboxControl(QtWidgets.QCheckBox):
    def get_value(self):    return self.isChecked()
    def set_value(self, v): self.setChecked(bool(v))


class _NumberControl(QtWidgets.QDoubleSpinBox):
    def __init__(self, min: float = -1e9, max: float = 1e9, parent=None):
        super().__init__(parent)
        self.setDecimals(3)
        self.setRange(min, max)
        self.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons
            if IS_QT6 else
            QtWidgets.QAbstractSpinBox.NoButtons
        )
        self.setFixedWidth(90)
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight if IS_QT6 else QtCore.Qt.AlignRight
        )

    def get_value(self):
        # Apply can be clicked while the embedded editor still has focus.  In
        # that case QAbstractSpinBox may expose the previous numeric value even
        # though the new text is visible, producing a one-Apply delay.
        self.interpretText()
        return self.value()

    def set_value(self, v):
        try:
            self.setValue(float(v))
        except (TypeError, ValueError):
            pass


class _IntegerControl(QtWidgets.QSpinBox):
    def __init__(self, min: int = 0, max: int = 100, parent=None):
        super().__init__(parent)
        self.setRange(int(min), int(max))
        self.setFixedWidth(90)

    def get_value(self):
        self.interpretText()
        return self.value()

    def set_value(self, v):
        try:
            self.setValue(int(float(v)))
        except (TypeError, ValueError):
            pass


class _FontControl(QtWidgets.QComboBox):
    """Compact chooser for up to ten suitable installed UI fonts."""

    _RECOMMENDED = (
        "Inter",
        "Segoe UI Variable",
        "Segoe UI",
        "Aptos",
        "Bahnschrift",
        "Source Sans 3",
        "IBM Plex Sans",
        "Roboto",
        "Noto Sans",
        "Ubuntu",
        "Helvetica Neue",
        "DejaVu Sans",
        "Liberation Sans",
        "Arial",
        "Calibri",
        "Candara",
        "Corbel",
        "Tahoma",
        "Verdana",
        "Trebuchet MS",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        from angstrompro.gui.appearance.theme_manager import _has_font_family
        families = [name for name in self._RECOMMENDED
                    if _has_font_family(name)][:10]
        if not families:
            app = QtWidgets.QApplication.instance()
            families = [app.font().family() if app is not None else "Sans Serif"]

        for family in families:
            self.addItem(family)
            self.setItemData(self.count() - 1, QtGui.QFont(family),
                             QtCore.Qt.ItemDataRole.FontRole if IS_QT6
                             else QtCore.Qt.FontRole)

    def get_value(self):
        return self.currentText()

    def set_value(self, value):
        family = str(value or "").strip()
        if not family:
            app = QtWidgets.QApplication.instance()
            family = app.font().family() if app is not None else "Sans Serif"
        index = self.findText(family)
        if index >= 0:
            self.setCurrentIndex(index)


class _TextControl(QtWidgets.QLineEdit):
    def get_value(self):    return self.text()
    def set_value(self, v): self.setText(str(v) if v is not None else "")


class _DropdownControl(QtWidgets.QComboBox):
    def __init__(self, choices: list | None = None, parent=None):
        super().__init__(parent)
        self._choices = choices or []
        self.addItems(self._choices)
        self.setMinimumWidth(120)

    def get_value(self):
        return self.currentText()

    def set_value(self, v):
        idx = self.findText(str(v))
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(0)


_BUILTIN_CONTROLS = {
    "checkbox": _CheckboxControl,
    "number":   _NumberControl,
    "integer":  _IntegerControl,
    "font":     _FontControl,
    "text":     _TextControl,
    "dropdown": _DropdownControl,
}


def _make_control(item: PrefItem, value, context=None) -> QtWidgets.QWidget:
    import inspect
    cls = _BUILTIN_CONTROLS.get(item.widget) or get_widget_class(item.widget)
    if cls is None:
        raise ValueError(f"Unknown preference widget type: {item.widget!r}")
    kw = dict(item.kwargs) if item.kwargs else {}
    if context is not None and "context" in inspect.signature(cls.__init__).parameters:
        kw["context"] = context
    ctrl = cls(**kw) if kw else cls()
    if context is not None and hasattr(ctrl, "set_context"):
        ctrl.set_context(context)
    if hasattr(ctrl, "set_value"):
        ctrl.set_value(value)
    return ctrl


# ── path helpers ───────────────────────────────────────────────────────────────

def _get_path(cfg: dict, dot_key: str):
    parts = dot_key.split(".")
    node = cfg
    for p in parts:
        node = node.get(p, {})
    return node


def _set_path(cfg: dict, dot_key: str, value) -> None:
    parts = dot_key.split(".")
    node = cfg
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value


# ── section card ───────────────────────────────────────────────────────────────

class _SectionCard(QtWidgets.QFrame):
    def __init__(self, section: PrefSection, show_header: bool = True, parent=None):
        super().__init__(parent)
        self.setFrameShape(
            QtWidgets.QFrame.Shape.StyledPanel if IS_QT6
            else QtWidgets.QFrame.StyledPanel
        )
        self.setObjectName("pref_section_card")
        self.setStyleSheet(
            "QFrame#pref_section_card {"
            "  border: 0.5px solid palette(mid);"
            "  border-radius: 8px;"
            "}"
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if show_header:
            header = QtWidgets.QWidget()
            header.setObjectName("pref_section_header")
            header.setStyleSheet(
                "QWidget#pref_section_header {"
                "  background: palette(window);"
                "  border-bottom: 0.5px solid palette(mid);"
                "  border-top-left-radius: 8px;"
                "  border-top-right-radius: 8px;"
                "}"
            )
            h_row = QtWidgets.QHBoxLayout(header)
            h_row.setContentsMargins(12, 6, 12, 6)
            h_row.setSpacing(7)
            title_lbl = QtWidgets.QLabel(section.title.upper())
            title_lbl.setObjectName("pref_section_header_label")
            h_row.addWidget(title_lbl)
            h_row.addStretch()
            layout.addWidget(header)

        self._body_layout = QtWidgets.QVBoxLayout()
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        layout.addLayout(self._body_layout)

    def add_row_widget(self, widget: QtWidgets.QWidget) -> None:
        self._body_layout.addWidget(widget)

    def add_full_width(self, widget: QtWidgets.QWidget) -> None:
        self._body_layout.addWidget(widget)


# ── main panel ────────────────────────────────────────────────────────────────

class PreferencesPanel(QtWidgets.QWidget):
    def __init__(
        self,
        module_name: str,
        schema: list[PrefSection],
        config: dict,
        on_apply: Callable | None = None,
        on_save_as_default: Callable | None = None,
        on_reset: Callable | None = None,
        context=None,
        parent=None,
    ):
        super().__init__(parent)
        self._schema      = schema
        self._config      = copy.deepcopy(config)
        self._on_apply_cb = on_apply
        self._on_save_cb  = on_save_as_default
        self._on_reset_cb = on_reset
        self._context     = context
        self._controls: list[tuple[str, QtWidgets.QWidget]] = []

        self._build_ui(module_name)

    # ------------------------------------------------------------------

    def _build_ui(self, module_name: str) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── sidebar ───────────────────────────────────────────────────
        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(190)
        sidebar.setObjectName("pref_sidebar")
        sidebar.setStyleSheet(
            "QWidget#pref_sidebar {"
            "  background: palette(window);"
            "  border-right: 0.5px solid palette(mid);"
            "}"
        )
        sb_layout = QtWidgets.QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 10, 0, 12)
        sb_layout.setSpacing(2)

        mod_lbl = QtWidgets.QLabel(module_name.upper())
        mod_lbl.setObjectName("pref_module_label")
        mod_lbl.setContentsMargins(14, 0, 14, 8)
        sb_layout.addWidget(mod_lbl)

        self._btn_group = QtWidgets.QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._stack = QtWidgets.QStackedWidget()

        for i, section in enumerate(self._schema):
            btn = QtWidgets.QPushButton(f"  {section.title}")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setObjectName("pref_nav_btn")
            btn.setStyleSheet(
                "QPushButton#pref_nav_btn:checked {"
                "  background: palette(highlight); color: palette(highlighted-text);"
                "}"
                "QPushButton#pref_nav_btn:hover:!checked {"
                "  background: palette(midlight);"
                "}"
            )
            if i == 0:
                btn.setChecked(True)
            self._btn_group.addButton(btn, i)
            sb_layout.addWidget(btn)
            self._stack.addWidget(self._build_page(section, self._context))

        sb_layout.addStretch()
        self._btn_group.idClicked.connect(self._stack.setCurrentIndex)

        root.addWidget(sidebar)

        # ── right panel ───────────────────────────────────────────────
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._stack, stretch=1)
        right_layout.addWidget(self._build_bottom_bar())
        root.addWidget(right, stretch=1)

    def _build_page(self, section: PrefSection, context=None) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(
            QtWidgets.QFrame.Shape.NoFrame if IS_QT6
            else QtWidgets.QFrame.NoFrame
        )

        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QtWidgets.QLabel(section.title)
        title.setObjectName("pref_section_title")
        layout.addWidget(title)

        # count how many cards this section will produce
        _n_cards = sum(1 for it in section.items if it.full_width)
        if any(not it.full_width for it in section.items):
            _n_cards += 1
        _show_header = _n_cards > 1

        pending: list[PrefItem] = []

        def _flush(items: list[PrefItem]) -> None:
            if not items:
                return
            card = _SectionCard(section, show_header=_show_header)
            for j, it in enumerate(items):
                value = _get_path(self._config, it.key)
                ctrl  = _make_control(it, value, context)
                self._controls.append((it.key, ctrl))

                row = QtWidgets.QWidget()
                row_layout = QtWidgets.QHBoxLayout(row)
                row_layout.setContentsMargins(14, 10, 14, 10)

                lbl_col = QtWidgets.QVBoxLayout()
                lbl_col.setSpacing(2)

                lbl = QtWidgets.QLabel(it.label)
                lbl.setObjectName("pref_row_label")
                lbl_col.addWidget(lbl)

                if it.desc:
                    d = QtWidgets.QLabel(it.desc)
                    d.setObjectName("pref_row_desc")
                    lbl_col.addWidget(d)

                row_layout.addLayout(lbl_col, stretch=1)
                row_layout.addWidget(ctrl)

                if j < len(items) - 1:
                    row.setStyleSheet(
                        "QWidget { border-bottom: 0.5px solid palette(mid); }"
                    )
                card.add_row_widget(row)
            layout.addWidget(card)

        has_expandable = False
        for item in section.items:
            if item.full_width:
                _flush(pending)
                pending = []
                card = _SectionCard(section, show_header=_show_header)
                value = _get_path(self._config, item.key)
                ctrl  = _make_control(item, value, context)
                self._controls.append((item.key, ctrl))
                card.add_full_width(ctrl)
                layout.addWidget(card, stretch=1 if item.expandable else 0)
                if item.expandable:
                    has_expandable = True
            else:
                pending.append(item)

        _flush(pending)
        if not has_expandable:
            layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def _build_bottom_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setObjectName("pref_bottom_bar")
        bar.setStyleSheet(
            "QWidget#pref_bottom_bar {"
            "  border-top: 0.5px solid palette(mid);"
            "  background: palette(window);"
            "}"
        )
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(12, 10, 12, 10)

        btn_reset = QtWidgets.QPushButton("Reset to default")
        btn_apply = QtWidgets.QPushButton("Apply")
        btn_save  = QtWidgets.QPushButton("Save as default")
        btn_save.setDefault(True)

        btn_reset.clicked.connect(self._on_reset)
        btn_apply.clicked.connect(self._on_apply)
        btn_save.clicked.connect(self._on_save_as_default)

        layout.addWidget(btn_reset)
        layout.addStretch()
        layout.addWidget(btn_apply)
        layout.addWidget(btn_save)
        return bar

    # ------------------------------------------------------------------

    def _collect(self) -> dict:
        cfg = copy.deepcopy(self._config)
        for dot_key, ctrl in self._controls:
            if dot_key and hasattr(ctrl, "get_value"):
                _set_path(cfg, dot_key, ctrl.get_value())
            elif not dot_key and hasattr(ctrl, "get_value"):
                ctrl.get_value()  # trigger side-effects (e.g. channel manager save)
        return cfg

    def _on_apply(self) -> None:
        cfg = self._collect()
        self._config = cfg
        if self._on_apply_cb:
            self._on_apply_cb(copy.deepcopy(cfg))

    def _on_save_as_default(self) -> None:
        self._on_apply()
        if self._on_save_cb:
            self._on_save_cb(copy.deepcopy(self._config))

    def _on_reset(self) -> None:
        if self._on_reset_cb:
            self._on_reset_cb()
