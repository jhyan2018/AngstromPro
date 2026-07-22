"""Semantic typography roles shared by AngstromPro widgets."""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtWidgets

BODY = "body"
SECONDARY = "secondary"
HEADING = "heading"
SECTION = "section"
NOTIFICATION = "notification"
HINT = "hint"
MONOSPACE = "monospace"


def set_typography_role(widget: QtWidgets.QWidget, role: str) -> None:
    """Assign a role consumed by ThemeManager's central stylesheet."""
    widget.setProperty("typographyRole", role)
    # Property changes after construction (for example, empty/filled runtime
    # slots) need an explicit repolish for Qt's attribute selector to update.
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
