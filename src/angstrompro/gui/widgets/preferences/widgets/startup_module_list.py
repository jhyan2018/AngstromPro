# -*- coding: utf-8 -*-
"""
Created on Wed Jul 09 2026

@author: jiahaoYan

StartupModuleListWidget — editable list of {module_id, count} startup module
entries for the Preferences → Startup panel.

Module IDs are selected from a dropdown of all registered modules — the user
cannot type arbitrary IDs.  Default entries (from built-in DEFAULTS) show a
lock icon; their count is editable but they cannot be removed.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets


class _StartupModuleRow(QtWidgets.QWidget):
    """One row: [module dropdown] [count spinbox] [remove / lock]"""

    remove_requested = QtCore.Signal()

    def __init__(self, module_choices: list[tuple[str, str]],
                 module_id: str = "", count: int = 1,
                 removable: bool = True, parent=None):
        """
        module_choices : list of (module_id, display_name) from the registry
        """
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._combo = QtWidgets.QComboBox()
        self._combo.setEnabled(removable)   # lock dropdown for default rows
        for mid, dname in module_choices:
            self._combo.addItem(f"{dname}  [{mid}]", userData=mid)
        # select current module_id
        idx = next((i for i in range(self._combo.count())
                    if self._combo.itemData(i) == module_id), 0)
        self._combo.setCurrentIndex(idx)

        self._count_spin = QtWidgets.QSpinBox()
        self._count_spin.setRange(1, 16)
        self._count_spin.setValue(max(1, int(count)))
        self._count_spin.setFixedWidth(56)
        self._count_spin.setToolTip("Number of instances to open at startup")

        if removable:
            btn = QtWidgets.QToolButton()
            btn.setText("✕")
            btn.setToolTip("Remove this entry")
            btn.clicked.connect(self.remove_requested)
        else:
            btn = QtWidgets.QLabel("🔒")
            btn.setToolTip("Built-in default — cannot be removed")
            btn.setFixedWidth(24)

        layout.addWidget(self._combo, stretch=1)
        layout.addWidget(self._count_spin)
        layout.addWidget(btn)

    def get_value(self) -> dict:
        return {
            "module_id": self._combo.currentData() or "",
            "count":     self._count_spin.value(),
        }


class StartupModuleListWidget(QtWidgets.QWidget):
    """
    Full-width widget for the Startup preferences section.

    Populated from the module registry (context.modules.list_all()).
    Default entries cannot be removed; user-added entries can be freely managed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._context        = None
        self._module_choices: list[tuple[str, str]] = []   # (module_id, display_name)
        self._rows:           list[_StartupModuleRow] = []

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(4)

        # column headers
        header   = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(8, 0, 8, 0)
        lbl_mod   = QtWidgets.QLabel("Module")
        lbl_mod.setObjectName("pref_row_desc")
        lbl_count = QtWidgets.QLabel("Count")
        lbl_count.setObjectName("pref_row_desc")
        lbl_count.setFixedWidth(56)
        h_layout.addWidget(lbl_mod, stretch=1)
        h_layout.addWidget(lbl_count)
        h_layout.addSpacing(28)
        root.addWidget(header)

        self._rows_container = QtWidgets.QWidget()
        self._rows_layout    = QtWidgets.QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(2)
        root.addWidget(self._rows_container)

        self._add_btn = QtWidgets.QPushButton("+ Add module")
        self._add_btn.setFixedWidth(130)
        self._add_btn.clicked.connect(self._on_add_clicked)
        AlignLeft = (QtCore.Qt.AlignmentFlag.AlignLeft
                     if hasattr(QtCore.Qt, "AlignmentFlag")
                     else QtCore.Qt.AlignLeft)
        root.addWidget(self._add_btn, alignment=AlignLeft)

    # ── context injection (called by PreferencesPanel if context= is set) ──

    def set_context(self, context) -> None:
        self._context = context
        self._refresh_choices()

    def _refresh_choices(self) -> None:
        if self._context is None:
            return
        self._module_choices = sorted(
            [(cls.module_id, getattr(cls, "display_name", cls.module_id))
             for cls in self._context.module_manager.list_all()],
            key=lambda x: x[1].lower(),
        )

    # ── row management ─────────────────────────────────────────────────────

    _EXCLUDED_IDS = {"main_workbench"}

    def _available_choices(self) -> list[tuple[str, str]]:
        """Module choices excluding main_workbench and already-listed modules."""
        used = {r.get_value()["module_id"] for r in self._rows}
        return [
            (mid, dname) for mid, dname in self._module_choices
            if mid not in self._EXCLUDED_IDS and mid not in used
        ] or [("", "(no more modules available)")]

    def _on_add_clicked(self) -> None:
        choices = self._available_choices()
        if choices and choices[0][0]:   # guard: at least one real choice
            self._add_row(removable=True, choices_override=choices)

    def _add_row(self, module_id: str = "", count: int = 1,
                 removable: bool = True,
                 choices_override: list[tuple[str, str]] | None = None) -> None:
        choices = choices_override if choices_override is not None \
                  else self._module_choices or [("", "(no modules registered)")]
        # for default (locked) rows always use the full list so the selection renders
        if not removable:
            choices = [c for c in self._module_choices if c[0] not in self._EXCLUDED_IDS] \
                      or [("", "(no modules registered)")]
        row = _StartupModuleRow(choices, module_id, count, removable,
                                self._rows_container)
        if removable:
            row.remove_requested.connect(lambda r=row: self._remove_row(r))
        self._rows_layout.addWidget(row)
        self._rows.append(row)

    def _remove_row(self, row: _StartupModuleRow) -> None:
        self._rows_layout.removeWidget(row)
        self._rows.remove(row)
        row.deleteLater()

    # ── PreferencesPanel interface ─────────────────────────────────────────

    def get_value(self) -> list[dict]:
        return [r.get_value() for r in self._rows if r.get_value()["module_id"]]

    def set_value(self, entries: list[dict]) -> None:
        self._refresh_choices()

        from angstrompro.core.configs.defaults import DEFAULTS
        default_ids = {e["module_id"]
                       for e in DEFAULTS.get("app", {}).get("startup_modules", [])}

        for row in list(self._rows):
            self._rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        seen: set[str] = set()
        # defaults first (locked), then user-added
        for entry in (entries or []):
            mid = entry.get("module_id", "")
            if not mid:
                continue
            is_default = mid in default_ids
            self._add_row(mid, entry.get("count", 1), removable=not is_default)
            seen.add(mid)

        # ensure every default appears even if missing from saved config
        for entry in DEFAULTS.get("app", {}).get("startup_modules", []):
            if entry["module_id"] not in seen:
                self._add_row(entry["module_id"], entry.get("count", 1), removable=False)
