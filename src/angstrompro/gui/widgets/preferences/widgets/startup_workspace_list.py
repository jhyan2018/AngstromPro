"""Draft startup workspaces, linked to the module counts in the same panel."""

from angstrompro.core.modules.startup_setup import build_startup_plan
from angstrompro.utils.qt_compat import QtWidgets


def _replace_options(combo, choices, current, missing_label):
    """Retain invalid selections visibly; never clamp or silently retarget."""
    blocked = combo.blockSignals(True)
    combo.clear()
    for label, value in choices:
        combo.addItem(label, value)
    index = combo.findData(current)
    if index < 0:
        combo.addItem(missing_label, current)
        index = combo.count() - 1
        combo.model().item(index).setEnabled(False)
    combo.setCurrentIndex(index)
    combo.blockSignals(blocked)


class _AttachmentRow(QtWidgets.QWidget):
    def __init__(self, owner, group, value):
        super().__init__(group)
        self.owner = owner
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.module = QtWidgets.QComboBox()
        self.instance = QtWidgets.QComboBox()
        self.destination = QtWidgets.QComboBox()
        self.module.setToolTip("Module configured in the startup module list above")
        self.instance.setToolTip(
            "Startup instance number, from 1 to the module's startup count"
        )
        self.destination.setToolTip("Active destination after attaching this instance")
        self.destination.addItem("Shared", "shared")
        self.destination.addItem("Private", "private")
        destination = value.get("active_destination", "shared")
        _replace_options(
            self.destination,
            [("Shared", "shared"), ("Private", "private")],
            destination,
            f"{destination} (invalid)",
        )
        self.module.addItem("", value.get("module_id", ""))
        self.instance.addItem("", value.get("instance", 1))
        remove = QtWidgets.QToolButton()
        remove.setText("×")
        remove.setToolTip("Remove attachment")
        remove.clicked.connect(lambda: group.remove_attachment(self))
        layout.addWidget(self.module, 3)
        layout.addWidget(self.instance, 1)
        layout.addWidget(self.destination, 1)
        layout.addWidget(remove)
        for combo in (self.module, self.instance, self.destination):
            combo.currentIndexChanged.connect(owner.refresh)

    def refresh_options(self, modules, registered):
        current = self.module.currentData()
        choices = [
            (getattr(registered.get(mid), "display_name", mid) or mid, mid)
            for mid in modules
        ]
        _replace_options(
            self.module,
            choices,
            current,
            f"{current or 'Select module'} (not available in startup)",
        )
        count = modules.get(current, 0) if isinstance(current, str) else 0
        numbers = [(str(i), i) for i in range(1, count + 1)]
        number = self.instance.currentData()
        _replace_options(self.instance, numbers, number, f"{number} (invalid)")
        self.instance.setToolTip(
            f"Choose a startup instance from 1 to {count}. "
            "Invalid saved selections are preserved until corrected or removed."
        )

    def get_value(self):
        return {
            "module_id": self.module.currentData(),
            "instance": self.instance.currentData(),
            "active_destination": self.destination.currentData(),
        }


class _WorkspaceCard(QtWidgets.QGroupBox):
    def __init__(self, owner, value):
        super().__init__("Shared workspace", owner)
        self.owner = owner
        self.rows = []
        layout = QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QHBoxLayout()
        self.name = QtWidgets.QLineEdit(str(value.get("name", "")))
        self.name.setPlaceholderText("Workspace name")
        self.name.setAccessibleName("Startup shared workspace name")
        self.name.textChanged.connect(owner.refresh)
        remove = QtWidgets.QPushButton("Remove workspace")
        remove.clicked.connect(lambda: owner.remove_workspace(self))
        header.addWidget(self.name, 1)
        header.addWidget(remove)
        layout.addLayout(header)
        labels = QtWidgets.QHBoxLayout()
        for title, stretch in (
            ("Attached module", 3),
            ("Instance", 1),
            ("Destination", 1),
        ):
            labels.addWidget(QtWidgets.QLabel(title), stretch)
        labels.addSpacing(24)
        layout.addLayout(labels)
        self.row_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.row_layout)
        add = QtWidgets.QPushButton("+ Add attachment")
        add.clicked.connect(lambda: self.add_attachment())
        layout.addWidget(add)
        attachments = value.get("attachments", [])
        for binding in attachments if isinstance(attachments, list) else [{}]:
            self.add_attachment(binding if isinstance(binding, dict) else {})

    def add_attachment(self, value=None):
        if value is None:
            entries = self.owner.module_entries()
            mid = entries[0]["module_id"] if entries else ""
            value = {"module_id": mid, "instance": 1, "active_destination": "shared"}
        row = _AttachmentRow(self.owner, self, value)
        self.rows.append(row)
        self.row_layout.addWidget(row)
        self.owner.refresh()

    def remove_attachment(self, row):
        self.rows.remove(row)
        self.row_layout.removeWidget(row)
        row.deleteLater()
        self.owner.refresh()

    def get_value(self):
        return {
            "name": self.name.text().strip(),
            "attachments": [row.get_value() for row in self.rows],
        }


class StartupWorkspaceListWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._context = None
        self._module_editor = None
        self._cards = []
        self._updating = False
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel(
            "Create empty shared workspaces and attach startup module instances. "
            "Instance numbers refer to the counts above, not runtime IDs. "
            "Save as default to use this setup next launch. Runtime changes stay separate."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self._warning = QtWidgets.QLabel()
        self._warning.setWordWrap(True)
        self._warning.setStyleSheet("font-weight: bold; color: palette(link);")
        layout.addWidget(self._warning)
        self._card_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self._card_layout)
        self._add = QtWidgets.QPushButton("+ Add shared workspace")
        self._add.clicked.connect(lambda: self.add_workspace())
        layout.addWidget(self._add)

    def set_context(self, context):
        self._context = context

    def bind_preferences_controls(self, controls):
        self._module_editor = controls.get("app.startup_modules")
        if self._module_editor is not None:
            self._module_editor.value_changed.connect(self.refresh)
        self.refresh()

    def module_entries(self):
        if self._module_editor is not None:
            return self._module_editor.get_value()
        return (
            self._context.config.get("app", "startup_modules", [])
            if self._context
            else []
        )

    def registered(self):
        return (
            {cls.module_id: cls for cls in self._context.module_manager.list_all()}
            if self._context
            else {}
        )

    def add_workspace(self, value=None):
        if value is None:
            used = {card.name.text().strip().casefold() for card in self._cards}
            name, number = "Analysis", 2
            while name.casefold() in used:
                name, number = f"Analysis {number}", number + 1
            value = {"name": name, "attachments": []}
        card = _WorkspaceCard(self, value)
        self._cards.append(card)
        self._card_layout.addWidget(card)
        self.refresh()
        return card

    def remove_workspace(self, card):
        self._cards.remove(card)
        self._card_layout.removeWidget(card)
        card.deleteLater()
        self.refresh()

    def get_value(self):
        return [card.get_value() for card in self._cards]

    def set_value(self, value):
        self._updating = True
        try:
            for card in self._cards:
                self._card_layout.removeWidget(card)
                card.deleteLater()
            self._cards = []
            for entry in value if isinstance(value, list) else []:
                self.add_workspace(entry if isinstance(entry, dict) else {})
        finally:
            self._updating = False
        self.refresh()

    def validation_errors(self):
        return build_startup_plan(
            self.module_entries(), self.get_value(), self.registered()
        ).errors

    def refresh(self, *_args):
        if self._updating:
            return
        self._updating = True
        try:
            entries = self.module_entries()
            modules = {e["module_id"]: e["count"] for e in entries}
            registered = self.registered()
            for card in self._cards:
                for row in card.rows:
                    row.refresh_options(modules, registered)
            errors = build_startup_plan(entries, self.get_value(), registered).errors
            self._warning.setText(
                "Fix before Apply / Save:\n" + "\n".join(errors) if errors else ""
            )
            self._warning.setVisible(bool(errors))
        finally:
            self._updating = False
