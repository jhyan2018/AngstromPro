# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 2026

@author: jiahaoYan

LiveModulesPanel — central panel of the MainWorkbench showing all live
module instances as cards.

Features
--------
  - One LiveModuleCard per live instance, grouped by category
  - Search/filter by name, instance_id, or category
  - "New Module" dropdown listing all registered module types (by category)
  - Rebuilds automatically on module_added / module_removed signals
  - Workspace item count refreshes on item_added / item_removed signals
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets
from angstrompro.gui.widgets.live_module_card import LiveModuleCard

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext


class LiveModulesPanel(QtWidgets.QWidget):

    def __init__(self, context: "AppContext", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._cards:   dict[str, LiveModuleCard] = {}   # instance_id → card
        self._headers: dict[str, QtWidgets.QLabel] = {}  # category → header label
        self._setup_ui()
        self._connect_signals()
        self._rebuild()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # --- toolbar ---
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_new = QtWidgets.QPushButton("+ New Module")
        self._btn_new.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._btn_new.clicked.connect(self._show_new_module_menu)
        toolbar.addWidget(self._btn_new)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search modules…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_filter)
        toolbar.addWidget(self._search)

        root.addLayout(toolbar)

        # --- scroll area for cards ---
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        self._card_container = QtWidgets.QWidget()
        self._card_layout    = QtWidgets.QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(0, 0, 4, 0)
        self._card_layout.setSpacing(4)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._card_container)
        root.addWidget(self._scroll)

        # --- summary label ---
        self._summary = QtWidgets.QLabel("")
        self._summary.setObjectName("panel_summary_label")
        root.addWidget(self._summary)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        mm = self._context.module_manager
        mm.module_added.connect(self._on_module_added)
        mm.module_removed.connect(self._on_module_removed)

        wm = self._context.workspace_manager
        wm.item_added.connect(self._on_workspace_changed)
        wm.item_removed.connect(self._on_workspace_changed)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not getattr(self, "_startup_done", False):
            self._startup_done = True
            self._launch_startup_modules()

    def _launch_startup_modules(self) -> None:
        startup_modules = self._context.config.get("app", "startup_modules") or []
        for entry in startup_modules:
            module_id = entry.get("module_id", "")
            count     = int(entry.get("count", 1))
            if not module_id:
                continue
            for _ in range(count):
                try:
                    self._context.module_manager.create(module_id, self._context)
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Failed to auto-create startup module %r: %s", module_id, exc
                    )

    def _on_workspace_changed(self, *_args) -> None:
        for card in self._cards.values():
            card.refresh()

    # ------------------------------------------------------------------
    # Card management
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        """Full rebuild — only called on first load."""
        while self._card_layout.count() > 1:
            item = self._card_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        self._headers.clear()

        instances = [
            inst for inst in self._context.module_manager.list_instances()
            if inst.module_id != "main_workbench"
        ]
        for inst in instances:
            self._insert_card(inst)
        self._update_summary()
        self._on_filter(self._search.text())

    def _insert_card(self, inst) -> None:
        category = inst.category or "Uncategorized"

        # Ensure category header exists
        if category not in self._headers:
            header = QtWidgets.QLabel(category.upper())
            header.setObjectName("card_category_header")
            header.setStyleSheet("color: grey; padding: 2px 0px 0px 2px;")
            # Insert before stretch, in sorted category order
            insert_at = self._category_insert_pos(category)
            self._card_layout.insertWidget(insert_at, header)
            self._headers[category] = header

        card = LiveModuleCard(inst, self._context, parent=self._card_container)
        card.sig_show.connect(self._on_show)
        card.sig_remove.connect(self._on_remove)

        # Insert after the last card in the same category (before next header or stretch)
        insert_at = self._card_insert_pos(category, inst.instance_id)
        self._card_layout.insertWidget(insert_at, card)
        self._cards[inst.instance_id] = card

    def _category_insert_pos(self, category: str) -> int:
        """Index to insert a new category header, keeping categories sorted."""
        sorted_cats = sorted(list(self._headers.keys()) + [category])
        pos_in_order = sorted_cats.index(category)
        # Walk layout to find where this category slot falls
        idx = 0
        cat_count = 0
        n = self._card_layout.count()
        while idx < n - 1:  # skip trailing stretch
            w = self._card_layout.itemAt(idx).widget()
            if w and w.objectName() == "card_category_header":
                if cat_count == pos_in_order:
                    return idx
                cat_count += 1
            idx += 1
        return self._card_layout.count() - 1  # before stretch

    def _card_insert_pos(self, category: str, instance_id: str) -> int:
        """Index to insert a card within its category group, sorted by instance_id."""
        header_widget = self._headers[category]
        header_idx = self._card_layout.indexOf(header_widget)
        # Collect existing cards in this category
        same_cat_ids = sorted(
            [iid for iid, card in self._cards.items()
             if self._instance_by_id(iid) is not None
             and (self._instance_by_id(iid).category or "Uncategorized") == category]
            + [instance_id]
        )
        pos_in_group = same_cat_ids.index(instance_id)
        return header_idx + 1 + pos_in_group

    def _on_module_added(self, module_id: str) -> None:
        # Find the newly added instance (last one for this module_id not yet in cards)
        for inst in self._context.module_manager.list_instances(module_id):
            if inst.module_id == "main_workbench":
                continue
            if inst.instance_id not in self._cards:
                self._insert_card(inst)
                self._update_summary()
                self._on_filter(self._search.text())
                return

    def _on_module_removed(self, module_id: str) -> None:
        # Find which card no longer has a live instance
        live_ids = {i.instance_id for i in self._context.module_manager.list_instances()}
        for iid in list(self._cards.keys()):
            if iid not in live_ids:
                card = self._cards.pop(iid)
                self._card_layout.removeWidget(card)
                card.deleteLater()
        # Remove empty category headers
        for category, header in list(self._headers.items()):
            has_cards = any(
                (self._instance_by_id(iid) or type("", (), {"category": None})()).category
                == category
                for iid in self._cards
            )
            if not has_cards:
                self._card_layout.removeWidget(header)
                header.deleteLater()
                del self._headers[category]
        self._update_summary()
        self._on_filter(self._search.text())

    def _update_summary(self) -> None:
        total = len(self._cards)
        self._summary.setText(
            f"{total} module instance{'s' if total != 1 else ''} running")

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _on_filter(self, text: str) -> None:
        text = text.strip().lower()
        for instance_id, card in self._cards.items():
            inst = self._instance_by_id(instance_id)
            if inst is None:
                card.setVisible(True)
                continue
            visible = (
                not text or
                text in inst.instance_id.lower() or
                text in (inst.display_name or "").lower() or
                text in (inst.category or "").lower() or
                text in inst.module_id.lower()
            )
            card.setVisible(visible)

    # ------------------------------------------------------------------
    # New module menu
    # ------------------------------------------------------------------

    def _show_new_module_menu(self) -> None:
        menu = QtWidgets.QMenu(self)

        mm = self._context.module_manager
        all_types = [
            cls for cls in mm.list_all()
            if cls.module_id != "main_workbench"
        ]

        if not all_types:
            menu.addAction("(no modules registered)").setEnabled(False)
        else:
            by_cat: dict[str, list] = {}
            for cls in all_types:
                by_cat.setdefault(cls.category or "Uncategorized", []).append(cls)

            for category in sorted(by_cat.keys()):
                submenu = menu.addMenu(category)
                for cls in sorted(by_cat[category],
                                  key=lambda c: c.display_name or c.module_id):
                    label = cls.display_name or cls.module_id
                    action = submenu.addAction(label)
                    action.triggered.connect(
                        lambda checked=False, mid=cls.module_id: self._create_module(mid))

        pos = self._btn_new.mapToGlobal(self._btn_new.rect().bottomLeft())
        menu.exec(pos)

    def _create_module(self, module_id: str) -> None:
        self._context.module_manager.create(module_id, self._context)

    # ------------------------------------------------------------------
    # Card actions
    # ------------------------------------------------------------------

    def _on_show(self, instance_id: str) -> None:
        inst = self._instance_by_id(instance_id)
        if inst and isinstance(inst, QtWidgets.QWidget):
            inst.show()
            inst.raise_()

    def _on_remove(self, instance_id: str) -> None:
        inst = self._instance_by_id(instance_id)
        if inst is None:
            return
        confirm = QtWidgets.QMessageBox.question(
            self, "Remove Module",
            f"Remove '{inst.display_name or inst.module_id}' ({instance_id})?",
            QtWidgets.QMessageBox.StandardButton.Yes |
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            self._context.module_manager.remove(inst)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _instance_by_id(self, instance_id: str):
        for inst in self._context.module_manager.list_instances():
            if inst.instance_id == instance_id:
                return inst
        return None
