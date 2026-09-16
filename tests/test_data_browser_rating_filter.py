"""The Data Browser can hide exactly one-star cards without hiding unrated cards."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from angstrompro.core.configs.defaults.modules.data_browser import DEFAULTS
from angstrompro.gui.modules.data_browser.data_browser_module import (
    DataBrowserModule,
    _filter_one_star_rows,
)
from angstrompro.gui.modules.data_browser.gallery_widget import CardRow


def test_one_star_filter_preference_is_exposed_and_backward_compatible() -> None:
    assert DEFAULTS["gallery"]["hide_one_star_cards"] is False

    items = [
        item
        for section in DataBrowserModule.preferences_schema
        for item in section.items
    ]
    preference = next(
        item for item in items
        if item.key == "gallery.hide_one_star_cards"
    )
    assert preference.widget == "checkbox"
    assert "exactly one star" in preference.desc.lower()


def test_filter_hides_only_cards_rated_exactly_one_star() -> None:
    rows = [
        CardRow((f"file-{stars}", "Z"), f"file-{stars}", stars=stars)
        for stars in range(6)
    ]

    assert _filter_one_star_rows(rows, False) is rows
    visible = _filter_one_star_rows(rows, True)

    assert [row.stars for row in visible] == [0, 2, 3, 4, 5]
