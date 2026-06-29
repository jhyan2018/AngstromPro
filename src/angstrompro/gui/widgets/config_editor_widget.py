# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:21:05 2026

@author: jiahaoYan
"""

"""
ConfigEditorWidget  tree view for viewing and editing all app config.

Columns:  Key | Value (editable) | Default
Bottom bar: status label | Reset to Defaults | Reload Saved | Save

Save behaviour:
  Only values that differ from built-in defaults are written to the config
  file (via ConfigManager.save_defaults). On next startup those values are
  merged back onto the defaults, so everything else keeps its built-in value.
"""
import json

from angstrompro.utils.qt_compat import QtCore, QtGui, QtWidgets, IS_QT6

# ItemDataRole
if IS_QT6:
    _UserRole   = QtCore.Qt.ItemDataRole.UserRole
    _UserRole1  = QtCore.Qt.ItemDataRole.UserRole + 1
    _ItemIsEditable = QtCore.Qt.ItemFlag.ItemIsEditable
    _ResizeToContents = QtWidgets.QHeaderView.ResizeMode.ResizeToContents
    _Stretch          = QtWidgets.QHeaderView.ResizeMode.Stretch
else:
    _UserRole   = QtCore.Qt.UserRole
    _UserRole1  = QtCore.Qt.UserRole + 1
    _ItemIsEditable = QtCore.Qt.ItemIsEditable
    _ResizeToContents = QtWidgets.QHeaderView.ResizeToContents
    _Stretch          = QtWidgets.QHeaderView.Stretch

_ROLE_ORIG_TYPE = _UserRole       # stores the Python type of the original value
_ROLE_DEFAULT   = _UserRole1      # stores the built-in default value (for highlight)


class ConfigEditorWidget(QtWidgets.QWidget):
    def __init__(self, context, parent=None, sections=None):
        super().__init__(parent)
        self._context  = context
        self._sections = sections
        self._local_config: dict = {}   # working copy  not applied until Save
        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(["Key", "Value", "Default"])
        self._tree.header().setSectionResizeMode(0, _ResizeToContents)
        self._tree.header().setSectionResizeMode(1, _Stretch)
        self._tree.header().setSectionResizeMode(2, _ResizeToContents)
        self._tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._tree)

        bar = QtWidgets.QHBoxLayout()
        self._status_label = QtWidgets.QLabel()
        bar.addWidget(self._status_label)
        bar.addStretch()

        btn_reset  = QtWidgets.QPushButton("Reset to Defaults")
        btn_reload = QtWidgets.QPushButton("Reload Saved")
        btn_save   = QtWidgets.QPushButton("Save")
        btn_save.setDefault(True)

        btn_reset.clicked.connect(self._on_reset)
        btn_reload.clicked.connect(self._on_reload)
        btn_save.clicked.connect(self._on_save)

        bar.addWidget(btn_reset)
        bar.addWidget(btn_reload)
        bar.addWidget(btn_save)
        layout.addLayout(bar)

    # ------------------------------------------------------------------
    # Populate tree from config
    # ------------------------------------------------------------------

    def _populate(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        full_config = self._context.config.get_all()

        from angstrompro.core.configs.defaults import DEFAULTS
        if self._sections is not None:
            config   = {k: v for k, v in full_config.items() if k in self._sections}
            defaults = {k: v for k, v in DEFAULTS.items()     if k in self._sections}
        else:
            config   = full_config
            defaults = DEFAULTS

        self._local_config = config
        self._build_subtree(self._tree.invisibleRootItem(), config, defaults)
        self._tree.expandAll()
        self._tree.blockSignals(False)
        self._update_status()

    def _build_subtree(
        self,
        parent: QtWidgets.QTreeWidgetItem,
        config: dict,
        defaults: dict,
    ) -> None:
        for key, value in config.items():
            default_val = defaults.get(key) if isinstance(defaults, dict) else None

            if isinstance(value, dict):
                group_item = QtWidgets.QTreeWidgetItem(parent, [key, "", ""])
                flags = group_item.flags()
                if IS_QT6:
                    group_item.setFlags(flags & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                else:
                    group_item.setFlags(flags & ~QtCore.Qt.ItemIsEditable)
                font = group_item.font(0)
                font.setBold(True)
                group_item.setFont(0, font)
                self._build_subtree(
                    group_item,
                    value,
                    default_val if isinstance(default_val, dict) else {},
                )
            else:
                display_val = self._to_display(value)
                display_def = self._to_display(default_val) if default_val is not None else ""
                item = QtWidgets.QTreeWidgetItem(parent, [key, display_val, display_def])
                item.setFlags(item.flags() | _ItemIsEditable)
                item.setData(0, _ROLE_ORIG_TYPE, type(value))
                item.setData(0, _ROLE_DEFAULT,   default_val)
                self._highlight_item(item, value, default_val)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._read_tree_into(self._tree.invisibleRootItem(), self._local_config)
        self._context.config.apply_all(self._local_config)
        self._context.config.save_defaults()
        self._update_status()

    def _read_tree_into(self, parent: QtWidgets.QTreeWidgetItem, config: dict) -> None:
        for i in range(parent.childCount()):
            item = parent.child(i)
            key  = item.text(0)
            if key not in config:
                continue
            if isinstance(config[key], dict):
                self._read_tree_into(item, config[key])
            else:
                orig_type  = item.data(0, _ROLE_ORIG_TYPE)
                config[key] = self._from_display(item.text(1), orig_type)

    # ------------------------------------------------------------------
    # Reset / Reload
    # ------------------------------------------------------------------

    def _on_reset(self) -> None:
        self._context.config.reset_to_defaults()
        self._populate()

    def _on_reload(self) -> None:
        self._context.config.reload_saved()
        self._populate()

    # ------------------------------------------------------------------
    # Live highlight when user edits a cell
    # ------------------------------------------------------------------

    def _on_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        if column != 1:
            return
        orig_type   = item.data(0, _ROLE_ORIG_TYPE)
        default_val = item.data(0, _ROLE_DEFAULT)
        if orig_type is None:
            return
        current_val = self._from_display(item.text(1), orig_type)
        self._highlight_item(item, current_val, default_val)
        self._update_status()

    def _highlight_item(self, item: QtWidgets.QTreeWidgetItem, value, default_val) -> None:
        changed = (default_val is not None) and (value != default_val)
        color = QtGui.QColor("#c8a000") if changed else QtGui.QColor()
        for col in range(3):
            item.setForeground(col, color)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _update_status(self) -> None:
        n = self._context.config.diff_count()
        if n == 0:
            self._status_label.setText("All values match defaults.")
        else:
            self._status_label.setText(f"{n} value(s) differ from defaults.")

    # ------------------------------------------------------------------
    # Type coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_display(value) -> str:
        if isinstance(value, list):
            return json.dumps(value)
        return str(value)

    @staticmethod
    def _from_display(text: str, orig_type: type):
        try:
            if orig_type is bool:
                return text.strip().lower() in ("true", "1", "yes")
            if orig_type is int:
                return int(text.strip())
            if orig_type is float:
                return float(text.strip())
            if orig_type is list:
                return json.loads(text.strip())
            return text
        except (ValueError, json.JSONDecodeError):
            return text
