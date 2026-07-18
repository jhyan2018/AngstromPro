# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

RcParamsStylePanel — dialog for editing common matplotlib rcParams.

Delta model: the dialog NEVER mutates global mpl.rcParams.  It displays the
effective style (mpl defaults overlaid with the scene's rcparams_delta,
pulled via ``delta_provider``) and, on Apply, emits ``delta_changed(dict)``
with the new delta.  The owner writes it into the RuntimeScene and rebuilds.

Keys not managed by this dialog (e.g. set by a loaded template) are
preserved in the delta untouched.  "Reset to Defaults" emits an empty delta.
"""
from __future__ import annotations

import matplotlib as mpl

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QtGui, Signal


class RcParamsStylePanel(QtWidgets.QDialog):
    """Edit common rcParams as a scene-owned delta."""

    # Emitted with the full new delta whenever the user applies changes
    delta_changed = Signal(dict)

    def __init__(self, delta_provider, parent=None) -> None:
        """
        Parameters
        ----------
        delta_provider : callable () -> dict
            Returns the scene's current rcparams_delta (JSON-safe).
        """
        super().__init__(parent,
                         QtCore.Qt.WindowType.Tool |
                         QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Plot Style (rcParams)")
        self.setModal(False)
        self._delta_provider = delta_provider
        self._loading = False
        self._loaded: dict = {}      # widget values at load — Apply skips unchanged
        self._adv_edits: dict = {}   # pending "All keys" table edits (key → text)
        # colors picked but not yet applied (rc_key → hex string)
        self._picked_colors: dict[str, str] = {}
        self._build()
        self._load()
        self._restore_geometry()

    # ── Window geometry persistence (QSettings) ───────────────────────────

    _QS_PREFIX = "curve_stack/plot_style_dialog"

    def _restore_geometry(self) -> None:
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            qs = get_qsettings()
            geom = qs.value(f"{self._QS_PREFIX}/geometry")
            if geom:
                self.restoreGeometry(geom)
            tab = qs.value(f"{self._QS_PREFIX}/tab")
            if tab is not None:
                self._tabs.setCurrentIndex(int(tab))
        except Exception:
            pass   # fresh install / unreadable settings — defaults are fine

    def closeEvent(self, event) -> None:
        try:
            from angstrompro.app.user_data_folder import get_qsettings
            qs = get_qsettings()
            qs.setValue(f"{self._QS_PREFIX}/geometry", self.saveGeometry())
            qs.setValue(f"{self._QS_PREFIX}/tab", self._tabs.currentIndex())
            qs.sync()
        except Exception:
            pass
        super().closeEvent(event)

    # ── Effective-value helper ────────────────────────────────────────────

    def _delta(self) -> dict:
        try:
            return dict(self._delta_provider() or {})
        except Exception:
            return {}

    def _eff(self, key: str, delta: dict | None = None):
        """Effective value: scene delta overlaid on matplotlib defaults."""
        d = self._delta() if delta is None else delta
        if key in d:
            return d[key]
        return mpl.rcParamsDefault.get(key)

    # relative font-size names → factor of font.size (matplotlib scalings)
    _REL_SIZE = {"xx-small": 0.579, "x-small": 0.694, "small": 0.833,
                 "medium": 1.0, "large": 1.2, "x-large": 1.44,
                 "xx-large": 1.728, "larger": 1.2, "smaller": 0.833}

    def _size_eff(self, key: str, delta: dict) -> float:
        """Resolve a font-size rcParam to points ('large' → 1.2 × font.size)."""
        v = self._eff(key, delta)
        if isinstance(v, (int, float)):
            return float(v)
        base = self._eff("font.size", delta)
        base = float(base) if isinstance(base, (int, float)) else 10.0
        return base * self._REL_SIZE.get(str(v), 1.0)

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(self._build_lines_tab(),  "Lines")
        self._tabs.addTab(self._build_axes_tab(),   "Axes")
        self._tabs.addTab(self._build_ticks_tab(),  "Ticks")
        self._tabs.addTab(self._build_font_tab(),   "Font")
        self._tabs.addTab(self._build_legend_tab(), "Legend")
        self._tabs.addTab(self._build_cycle_tab(),  "Color cycle")
        self._tabs.addTab(self._build_all_keys_tab(), "All keys")
        layout.addWidget(self._tabs)

        btn_row = QtWidgets.QHBoxLayout()
        btn_reset = QtWidgets.QPushButton("Reset to Defaults")
        btn_reset.clicked.connect(self._reset)
        btn_apply = QtWidgets.QPushButton("Apply")
        btn_apply.setDefault(True)
        btn_apply.clicked.connect(self._apply)
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.setMinimumWidth(440)   # "All keys" table needs the room

    def _form(self) -> tuple[QtWidgets.QWidget, QtWidgets.QFormLayout]:
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        f.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        f.setSpacing(6)
        f.setContentsMargins(8, 8, 8, 8)
        return w, f

    def _spin(self, lo, hi, step=0.1, dec=1) -> QtWidgets.QDoubleSpinBox:
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi); s.setSingleStep(step); s.setDecimals(dec)
        s.setFixedWidth(80)
        return s

    def _color_btn(self) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton()
        btn.setFixedSize(56, 22)
        return btn

    def _size_row(self, spin) -> tuple[QtWidgets.QWidget, QtWidgets.QCheckBox]:
        """Spin + 'auto' checkbox row for a font-size field.

        auto checked = the rcParam stays relative and follows font.size;
        unchecked   = pinned to the spinbox value.
        """
        auto = QtWidgets.QCheckBox("auto")
        auto.setToolTip("Follow the base Font size (relative, e.g. 1.2×);\n"
                        "uncheck to pin this element to an absolute size")
        auto.toggled.connect(lambda on: spin.setEnabled(not on))
        row = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(spin)
        h.addWidget(auto)
        h.addStretch()
        return row, auto

    # ── Tabs ──────────────────────────────────────────────────────────────

    def _build_lines_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._lw   = self._spin(0.1, 20.0, 0.5)
        self._ls   = QtWidgets.QComboBox()
        self._ls.addItems(["solid", "dashed", "dotted", "dashdot"])
        self._mk   = QtWidgets.QComboBox()
        self._mk.addItems(["None", "o", "s", "^", "D", "+", "x"])
        self._mks  = self._spin(0.5, 30.0, 1.0)
        f.addRow("Line width:",   self._lw)
        f.addRow("Line style:",   self._ls)
        f.addRow("Marker:",       self._mk)
        f.addRow("Marker size:",  self._mks)
        return w

    def _build_axes_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._axes_fc  = self._color_btn()
        self._axes_fc.clicked.connect(lambda: self._pick("axes.facecolor", self._axes_fc))
        self._axes_ec  = self._color_btn()
        self._axes_ec.clicked.connect(lambda: self._pick("axes.edgecolor", self._axes_ec))
        self._axes_lw  = self._spin(0.1, 5.0, 0.5)
        self._title_sz = self._spin(4, 40, 1, 0)
        self._label_sz = self._spin(4, 40, 1, 0)
        title_row, self._title_sz_auto = self._size_row(self._title_sz)
        label_row, self._label_sz_auto = self._size_row(self._label_sz)
        self._grid_cb  = QtWidgets.QCheckBox()
        self._grid_ls  = QtWidgets.QComboBox()
        self._grid_ls.addItems(["--", "-", ":", "-."])
        self._grid_lw  = self._spin(0.1, 5.0, 0.1)
        self._grid_alpha = self._spin(0.0, 1.0, 0.05, 2)
        f.addRow("Face color:",   self._axes_fc)
        f.addRow("Edge color:",   self._axes_ec)
        f.addRow("Edge width:",   self._axes_lw)
        f.addRow("Title size:",   title_row)
        f.addRow("Label size:",   label_row)
        f.addRow("Grid on:",      self._grid_cb)
        f.addRow("Grid style:",   self._grid_ls)
        f.addRow("Grid width:",   self._grid_lw)
        f.addRow("Grid alpha:",   self._grid_alpha)
        return w

    def _build_ticks_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._tick_dir   = QtWidgets.QComboBox()
        self._tick_dir.addItems(["in", "out", "inout"])
        self._major_sz   = self._spin(0, 20, 1, 1)
        self._minor_sz   = self._spin(0, 20, 1, 1)
        self._tick_lw    = self._spin(0.1, 5, 0.1)
        self._tick_lsz   = self._spin(4, 40, 1, 0)
        lsz_row, self._tick_lsz_auto = self._size_row(self._tick_lsz)
        f.addRow("Direction:",    self._tick_dir)
        f.addRow("Major size:",   self._major_sz)
        f.addRow("Minor size:",   self._minor_sz)
        f.addRow("Line width:",   self._tick_lw)
        f.addRow("Label size:",   lsz_row)
        return w

    def _build_font_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._font_sz  = self._spin(4, 40, 1, 0)
        self._font_fam = QtWidgets.QComboBox()
        self._font_fam.addItems(["sans-serif", "serif", "monospace", "cursive"])
        self._font_wt  = QtWidgets.QComboBox()
        self._font_wt.addItems(["normal", "bold", "light"])
        f.addRow("Size:",    self._font_sz)
        f.addRow("Family:", self._font_fam)
        f.addRow("Weight:", self._font_wt)
        return w

    def _build_legend_tab(self) -> QtWidgets.QWidget:
        w, f = self._form()
        self._leg_sz     = self._spin(4, 40, 1, 0)
        leg_row, self._leg_sz_auto = self._size_row(self._leg_sz)
        self._leg_frame  = QtWidgets.QCheckBox()
        self._leg_alpha  = self._spin(0.0, 1.0, 0.05, 2)
        f.addRow("Font size:",     leg_row)
        f.addRow("Frame:",         self._leg_frame)
        f.addRow("Frame alpha:",   self._leg_alpha)
        return w

    def _build_cycle_tab(self) -> QtWidgets.QWidget:
        w  = QtWidgets.QWidget()
        ll = QtWidgets.QHBoxLayout(w)
        ll.setContentsMargins(8, 8, 8, 8)
        ll.setSpacing(8)

        self._cycle_list = QtWidgets.QListWidget()
        self._cycle_list.setFixedHeight(180)
        self._cycle_list.itemDoubleClicked.connect(self._cycle_edit_color)
        ll.addWidget(self._cycle_list, stretch=1)

        btns = QtWidgets.QVBoxLayout()
        btn_add    = QtWidgets.QPushButton("Add…")
        btn_remove = QtWidgets.QPushButton("Remove")
        btn_up     = QtWidgets.QPushButton("Up")
        btn_down   = QtWidgets.QPushButton("Down")
        btn_add.setToolTip("Pick a color and append it to the cycle")
        btn_remove.setToolTip("Remove the selected color")
        btn_up.setToolTip("Move the selected color earlier in the cycle")
        btn_down.setToolTip("Move the selected color later in the cycle")
        btn_add.clicked.connect(self._cycle_add)
        btn_remove.clicked.connect(self._cycle_remove)
        btn_up.clicked.connect(lambda: self._cycle_move(-1))
        btn_down.clicked.connect(lambda: self._cycle_move(+1))
        for b in (btn_add, btn_remove, btn_up, btn_down):
            btns.addWidget(b)
        btns.addStretch()
        hint = QtWidgets.QLabel("Empty list =\ndefault cycle")
        hint.setStyleSheet("color: gray; font-style: italic;")
        btns.addWidget(hint)
        ll.addLayout(btns)
        return w

    # ── "All keys" tab — every tracked rcParam, searchable ────────────────

    def _build_all_keys_tab(self) -> QtWidgets.QWidget:
        from .template_manager import _tracked_keys

        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        self._adv_filter = QtWidgets.QLineEdit()
        self._adv_filter.setPlaceholderText(
            "Filter keys…  (e.g. spines, tick.top, figsize, weight)")
        self._adv_filter.setClearButtonEnabled(True)
        self._adv_filter.textChanged.connect(self._adv_apply_filter)
        v.addWidget(self._adv_filter)

        self._adv_table = QtWidgets.QTableWidget(0, 2)
        self._adv_table.setHorizontalHeaderLabels(["rcParam key", "Value"])
        self._adv_table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._adv_table.horizontalHeader().setStretchLastSection(True)
        self._adv_table.verticalHeader().setVisible(False)
        self._adv_table.setMinimumHeight(260)
        self._adv_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked |
            QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed)
        self._adv_table.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._adv_table.customContextMenuRequested.connect(self._adv_context_menu)
        self._adv_table.itemChanged.connect(self._adv_item_changed)

        # rows are static (key set never changes) — values refresh in _load
        # axes.prop_cycle is excluded: the Color cycle tab owns it
        keys = sorted(k for k in _tracked_keys() if k != "axes.prop_cycle")
        self._adv_table.setRowCount(len(keys))
        self._adv_table.blockSignals(True)
        for row, key in enumerate(keys):
            k_item = QtWidgets.QTableWidgetItem(key)
            k_item.setFlags(k_item.flags()
                            & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self._adv_table.setItem(row, 0, k_item)
            self._adv_table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))
        self._adv_table.blockSignals(False)

        v.addWidget(self._adv_table, stretch=1)
        hint = QtWidgets.QLabel(
            "Bold = pinned in this scene's style.  Edit a value and Apply; "
            "right-click for color picker / reset to default.")
        hint.setStyleSheet("color: gray; font-style: italic;")
        hint.setWordWrap(True)
        v.addWidget(hint)
        return w

    @staticmethod
    def _adv_val_to_text(v) -> str:
        if v is None:
            return "None"
        if isinstance(v, bool):
            return "True" if v else "False"
        if isinstance(v, (list, tuple)):
            return ", ".join(str(x) for x in v)
        return str(v)

    def _adv_refresh_values(self, delta: dict) -> None:
        """Fill the value column with effective values; bold pinned keys."""
        self._adv_table.blockSignals(True)
        for row in range(self._adv_table.rowCount()):
            key    = self._adv_table.item(row, 0).text()
            v_item = self._adv_table.item(row, 1)
            v_item.setText(self._adv_val_to_text(self._eff(key, delta)))
            bold = key in delta
            f = v_item.font(); f.setBold(bold); v_item.setFont(f)
            k = self._adv_table.item(row, 0)
            f = k.font(); f.setBold(bold); k.setFont(f)
        self._adv_table.blockSignals(False)
        self._adv_edits: dict[str, str] = {}

    def _adv_apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self._adv_table.rowCount()):
            key = self._adv_table.item(row, 0).text().lower()
            self._adv_table.setRowHidden(row, bool(needle) and needle not in key)

    def _adv_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if self._loading or item.column() != 1:
            return
        key = self._adv_table.item(item.row(), 0).text()
        self._adv_edits[key] = item.text()
        f = item.font(); f.setBold(True); item.setFont(f)

    def _adv_context_menu(self, pos) -> None:
        item = self._adv_table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        key = self._adv_table.item(row, 0).text()
        v_item = self._adv_table.item(row, 1)

        menu = QtWidgets.QMenu(self)
        if "color" in key:
            act_pick = menu.addAction("Pick color…")
        else:
            act_pick = None
        act_reset = menu.addAction("Reset to default")
        chosen = menu.exec(self._adv_table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_pick:
            import matplotlib.colors as mcolors
            try:
                r, g, b, _ = mcolors.to_rgba(v_item.text())
                initial = QtGui.QColor.fromRgbF(r, g, b)
            except Exception:
                initial = QtGui.QColor("white")
            color = QtWidgets.QColorDialog.getColor(
                initial, self, f"Pick color: {key}")
            if color.isValid():
                v_item.setText(color.name())   # triggers _adv_item_changed
        elif chosen is act_reset:
            v_item.setText(self._adv_val_to_text(mpl.rcParamsDefault.get(key)))

    def _adv_collect(self, delta: dict) -> list[str]:
        """Validate pending table edits into the delta.  Returns error list."""
        import matplotlib.rcsetup as rcsetup
        errors: list[str] = []
        for key, text in self._adv_edits.items():
            validator = rcsetup._validators.get(key)
            try:
                if text.strip() == "None":
                    value = None
                elif validator is not None:
                    value = validator(text)
                else:
                    value = text
            except Exception as exc:
                errors.append(f"{key} = {text!r}: {exc}")
                continue
            if value == mpl.rcParamsDefault.get(key):
                delta.pop(key, None)
            else:
                delta[key] = value
        return errors

    # ── Color-cycle list helpers ──────────────────────────────────────────

    @staticmethod
    def _cycle_swatch(color: str) -> QtGui.QIcon:
        pm = QtGui.QPixmap(28, 16)
        pm.fill(QtGui.QColor(color))
        return QtGui.QIcon(pm)

    def _cycle_append_item(self, color: str) -> None:
        item = QtWidgets.QListWidgetItem(self._cycle_swatch(color), color)
        self._cycle_list.addItem(item)

    def _cycle_colors(self) -> list[str]:
        return [self._cycle_list.item(i).text()
                for i in range(self._cycle_list.count())]

    def _cycle_set_colors(self, colors: list[str]) -> None:
        self._cycle_list.clear()
        for c in colors:
            self._cycle_append_item(c)

    def _cycle_add(self) -> None:
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor("#1f77b4"), self, "Add cycle color")
        if color.isValid():
            self._cycle_append_item(color.name())

    def _cycle_remove(self) -> None:
        row = self._cycle_list.currentRow()
        if row >= 0:
            self._cycle_list.takeItem(row)

    def _cycle_move(self, direction: int) -> None:
        row = self._cycle_list.currentRow()
        new = row + direction
        if row < 0 or not (0 <= new < self._cycle_list.count()):
            return
        item = self._cycle_list.takeItem(row)
        self._cycle_list.insertItem(new, item)
        self._cycle_list.setCurrentRow(new)

    def _cycle_edit_color(self, item: QtWidgets.QListWidgetItem) -> None:
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(item.text()), self, "Edit cycle color")
        if color.isValid():
            item.setText(color.name())
            item.setIcon(self._cycle_swatch(color.name()))

    # ── Load effective values (defaults + delta) ──────────────────────────

    def _load(self) -> None:
        self._loading = True
        self._picked_colors.clear()
        delta = self._delta()
        eff = lambda k: self._eff(k, delta)
        try:
            self._lw.setValue(eff("lines.linewidth"))
            ls = str(eff("lines.linestyle"))
            self._ls.setCurrentText({"-": "solid", "--": "dashed",
                                     ":": "dotted", "-.": "dashdot"}.get(ls, ls))
            mk = str(eff("lines.marker"))
            self._mk.setCurrentText(mk if mk in [self._mk.itemText(i)
                                                  for i in range(self._mk.count())] else "None")
            self._mks.setValue(eff("lines.markersize"))

            self._set_color_btn(self._axes_fc, eff("axes.facecolor"))
            self._set_color_btn(self._axes_ec, eff("axes.edgecolor"))
            self._axes_lw.setValue(eff("axes.linewidth"))
            # font-size fields show the RESOLVED effective size ('large' →
            # 1.2 × font.size).  auto = key absent from delta → stays
            # relative and follows font.size; pinned = absolute in delta.
            self._title_sz.setValue(self._size_eff("axes.titlesize", delta))
            self._label_sz.setValue(self._size_eff("axes.labelsize", delta))
            self._title_sz_auto.setChecked("axes.titlesize" not in delta)
            self._label_sz_auto.setChecked("axes.labelsize" not in delta)
            self._grid_cb.setChecked(bool(eff("axes.grid")))
            self._grid_ls.setCurrentText(str(eff("grid.linestyle")))
            self._grid_lw.setValue(eff("grid.linewidth"))
            self._grid_alpha.setValue(eff("grid.alpha") or 0.4)

            # the plot widgets force "in" (house style) when the delta has no
            # direction — display THAT effective value, not mpl's "out"
            self._tick_dir.setCurrentText(
                str(delta.get("xtick.direction", "in")))
            self._major_sz.setValue(eff("xtick.major.size"))
            self._minor_sz.setValue(eff("xtick.minor.size"))
            self._tick_lw.setValue(eff("xtick.major.width"))
            self._tick_lsz.setValue(self._size_eff("xtick.labelsize", delta))
            self._tick_lsz_auto.setChecked("xtick.labelsize" not in delta)

            v = eff("font.size")
            self._font_sz.setValue(v if isinstance(v, (int, float)) else 10)
            fam = eff("font.family")
            self._font_fam.setCurrentText(fam[0] if isinstance(fam, list) else str(fam))
            self._font_wt.setCurrentText(str(eff("font.weight")))

            self._leg_sz.setValue(self._size_eff("legend.fontsize", delta))
            self._leg_sz_auto.setChecked("legend.fontsize" not in delta)
            self._leg_frame.setChecked(bool(eff("legend.frameon")))
            self._leg_alpha.setValue(eff("legend.framealpha") or 0.8)

            # color cycle — delta stores a plain list; default is a Cycler
            cyc = delta.get("axes.prop_cycle")
            self._cycle_set_colors(list(cyc)
                                   if isinstance(cyc, (list, tuple)) else [])

            self._adv_refresh_values(delta)

        except Exception:
            pass
        finally:
            self._loading = False
            self._snapshot_loaded()

    def _snapshot_loaded(self) -> None:
        """Record current widget values — _apply only writes changed fields."""
        self._loaded = dict(self._field_values())

    def _field_values(self) -> dict:
        """Current widget values keyed by logical field name."""
        return {
            "lw":         self._lw.value(),
            "ls":         self._ls.currentText(),
            "mk":         self._mk.currentText(),
            "mks":        self._mks.value(),
            "axes_lw":    self._axes_lw.value(),
            "title_sz":   (self._title_sz.value(), self._title_sz_auto.isChecked()),
            "label_sz":   (self._label_sz.value(), self._label_sz_auto.isChecked()),
            "grid":       self._grid_cb.isChecked(),
            "grid_ls":    self._grid_ls.currentText(),
            "grid_lw":    self._grid_lw.value(),
            "grid_alpha": self._grid_alpha.value(),
            "tick_dir":   self._tick_dir.currentText(),
            "major_sz":   self._major_sz.value(),
            "minor_sz":   self._minor_sz.value(),
            "tick_lw":    self._tick_lw.value(),
            "tick_lsz":   (self._tick_lsz.value(), self._tick_lsz_auto.isChecked()),
            "font_sz":    self._font_sz.value(),
            "font_fam":   self._font_fam.currentText(),
            "font_wt":    self._font_wt.currentText(),
            "leg_sz":     (self._leg_sz.value(), self._leg_sz_auto.isChecked()),
            "leg_frame":  self._leg_frame.isChecked(),
            "leg_alpha":  self._leg_alpha.value(),
            "cycle":      self._cycle_colors(),
        }

    # ── Apply → emit new delta ────────────────────────────────────────────

    _LS_MAP = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}

    def _apply(self) -> None:
        """Write ONLY user-edited fields into the delta.

        Untouched fields never enter the delta.  This matters for the font
        sizes: matplotlib defaults are RELATIVE ('large' = 1.2 × font.size),
        so pinning them to numbers would stop them from scaling with the
        Font-tab size.  A field left alone keeps that relative behavior.
        """
        delta   = self._delta()   # preserve keys this dialog doesn't manage
        current = self._field_values()
        curated_written: set[str] = set()   # rc keys written by curated tabs

        def put(key, value) -> None:
            """Store value in delta, or drop the key if it equals the default."""
            curated_written.add(key)
            if value == mpl.rcParamsDefault.get(key):
                delta.pop(key, None)
            else:
                delta[key] = value

        def setif(name, value, *keys) -> None:
            """put() into all *keys*, but only if the field was edited."""
            if current.get(name) == self._loaded.get(name):
                return
            for k in keys:
                put(k, value)

        def set_size(name, value, *keys) -> None:
            """Font-size field with an auto checkbox.

            auto on  → keys leave the delta (relative, follows font.size);
            auto off → pinned to the absolute spin value.
            """
            if current.get(name) == self._loaded.get(name):
                return
            _, is_auto = current[name]
            for k in keys:
                curated_written.add(k)
                if is_auto:
                    delta.pop(k, None)
                else:
                    delta[k] = int(value)

        try:
            setif("lw",  self._lw.value(),  "lines.linewidth")
            setif("ls",  self._LS_MAP.get(self._ls.currentText(),
                                          self._ls.currentText()),
                  "lines.linestyle")
            setif("mk",  self._mk.currentText(),  "lines.marker")
            setif("mks", self._mks.value(),       "lines.markersize")

            # axes — colors apply only when explicitly picked
            for key, picked in self._picked_colors.items():
                put(key, picked)
            setif("axes_lw",  self._axes_lw.value(),        "axes.linewidth")
            set_size("title_sz", self._title_sz.value(),  "axes.titlesize")
            set_size("label_sz", self._label_sz.value(),  "axes.labelsize")
            setif("grid",     self._grid_cb.isChecked(),    "axes.grid")
            setif("grid_ls",  self._grid_ls.currentText(),  "grid.linestyle")
            setif("grid_lw",  self._grid_lw.value(),        "grid.linewidth")
            setif("grid_alpha", self._grid_alpha.value(),   "grid.alpha")

            # ticks — one field drives both x and y (and major+minor width).
            # direction is stored UNCONDITIONALLY (no drop-at-default): the
            # widgets' house default is "in", so an absent key means "in",
            # and "out" must live in the delta to override it
            if current["tick_dir"] != self._loaded.get("tick_dir"):
                d = self._tick_dir.currentText()
                delta["xtick.direction"] = d
                delta["ytick.direction"] = d
                curated_written.update({"xtick.direction", "ytick.direction"})
            setif("major_sz", self._major_sz.value(),
                  "xtick.major.size", "ytick.major.size")
            setif("minor_sz", self._minor_sz.value(),
                  "xtick.minor.size", "ytick.minor.size")
            setif("tick_lw",  self._tick_lw.value(),
                  "xtick.major.width", "ytick.major.width",
                  "xtick.minor.width", "ytick.minor.width")
            set_size("tick_lsz", self._tick_lsz.value(),
                     "xtick.labelsize", "ytick.labelsize")

            # font
            setif("font_sz",  int(self._font_sz.value()),      "font.size")
            setif("font_fam", [self._font_fam.currentText()],  "font.family")
            setif("font_wt",  self._font_wt.currentText(),     "font.weight")

            # legend
            set_size("leg_sz", self._leg_sz.value(),          "legend.fontsize")
            setif("leg_frame", self._leg_frame.isChecked(),   "legend.frameon")
            setif("leg_alpha", self._leg_alpha.value(),       "legend.framealpha")

            # color cycle — stored JSON-safe as a list of color strings
            if current["cycle"] != self._loaded.get("cycle"):
                if current["cycle"]:
                    delta["axes.prop_cycle"] = current["cycle"]
                else:
                    delta.pop("axes.prop_cycle", None)

            # same key edited in a curated tab AND in the All-keys table?
            conflicts = sorted(curated_written & set(self._adv_edits))
            if conflicts:
                QtWidgets.QMessageBox.warning(
                    self, "Conflicting edits",
                    "These keys were edited both in a style tab and in the "
                    "All-keys table.\nThe All-keys table value wins:\n\n"
                    + "\n".join(f"  {k} = {self._adv_edits[k]}"
                                for k in conflicts))

            # "All keys" table edits — validated with mpl's own validators
            adv_errors = self._adv_collect(delta)
            if adv_errors:
                QtWidgets.QMessageBox.warning(
                    self, "Some values were rejected",
                    "These entries are invalid and were skipped:\n\n"
                    + "\n".join(adv_errors))

        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Apply failed", str(exc))
            return

        self._picked_colors.clear()
        self.delta_changed.emit(delta)   # owner updates the scene (direct call)
        self._load()   # re-resolve displayed sizes (auto fields follow font.size)

    def _reset(self) -> None:
        """Reset to matplotlib defaults: delta ← {}."""
        self.delta_changed.emit({})
        self._load()

    # ── Color button helpers ──────────────────────────────────────────────

    def _pick(self, rc_key: str, btn: QtWidgets.QPushButton) -> None:
        import matplotlib.colors as mcolors
        current = self._picked_colors.get(rc_key) or self._eff(rc_key)
        try:
            r, g, b, a = mcolors.to_rgba(current)
            initial = QtGui.QColor.fromRgbF(r, g, b, a)
        except Exception:
            initial = QtGui.QColor("white")
        color = QtWidgets.QColorDialog.getColor(initial, self, f"Pick color: {rc_key}")
        if not color.isValid():
            return
        # pending until Apply — like every other field in this dialog
        self._picked_colors[rc_key] = color.name()
        self._set_color_btn(btn, color.name())

    @staticmethod
    def _set_color_btn(btn: QtWidgets.QPushButton, color_str: str) -> None:
        import matplotlib.colors as mcolors
        try:
            r, g, b, _ = mcolors.to_rgba(color_str)
            qc = QtGui.QColor.fromRgbF(r, g, b)
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            fg = "#000000" if luma > 0.5 else "#ffffff"
            btn.setStyleSheet(
                f"background-color: {qc.name()}; color: {fg}; border: 1px solid #888;")
            btn.setText(qc.name())
        except Exception:
            btn.setStyleSheet("")
            btn.setText("?")
