"""The Data Browser wheel increment is configurable and folder-size independent."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from angstrompro.core.configs.defaults.modules.data_browser import DEFAULTS
from angstrompro.gui.modules.data_browser.data_browser_module import DataBrowserModule
from angstrompro.gui.modules.data_browser.gallery_widget import CardRow, GalleryView
from angstrompro.gui.widgets.preferences import PreferencesPanel
from angstrompro.utils.qt_compat import QtCore, QtGui, QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _wheel(view: GalleryView, angle_y: int) -> None:
    point = QtCore.QPointF(30, 30)
    event = QtGui.QWheelEvent(
        point, point, QtCore.QPoint(0, 0), QtCore.QPoint(0, angle_y),
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.Qt.ScrollPhase.ScrollUpdate, False,
    )
    QtWidgets.QApplication.sendEvent(view.viewport(), event)


def test_preference_is_exposed_with_a_slow_default():
    assert DEFAULTS["gallery"]["wheel_scroll_px"] == 80
    items = [item for section in DataBrowserModule.preferences_schema
             for item in section.items]
    pref = next(item for item in items
                if item.key == "gallery.wheel_scroll_px")
    assert pref.widget == "integer"
    assert pref.kwargs == {"min": 10, "max": 400}


def test_preference_panel_applies_the_selected_step(qapp):
    del qapp
    section = next(section for section in DataBrowserModule.preferences_schema
                   if section.title == "Gallery navigation")
    applied = []
    panel = PreferencesPanel(
        "Data Browser", [section], DEFAULTS,
        on_apply=lambda cfg: applied.append(cfg),
    )
    try:
        control = next(ctrl for key, ctrl in panel._controls
                       if key == "gallery.wheel_scroll_px")
        assert control.value() == 80
        control.setValue(140)
        panel._on_apply()
        assert applied[-1]["gallery"]["wheel_scroll_px"] == 140
    finally:
        panel.close()


@pytest.mark.parametrize("card_count", [50, 500])
def test_wheel_moves_selected_pixels_not_a_gallery_percentage(qapp, card_count):
    view = GalleryView(wheel_scroll_px=80)
    view.resize(700, 500)
    view.show()
    try:
        view.gallery_model().set_rows([
            CardRow((str(i), "Z"), str(i)) for i in range(card_count)
        ])
        qapp.processEvents()
        bar = view.verticalScrollBar()
        bar.setValue(1000)
        _wheel(view, -120)
        assert bar.value() == 1080

        view.set_wheel_scroll_px(160)
        _wheel(view, -120)
        assert bar.value() == 1240
        _wheel(view, 120)
        assert bar.value() == 1080
    finally:
        view.close()


def test_partial_wheel_deltas_accumulate(qapp):
    view = GalleryView(wheel_scroll_px=80)
    view.resize(700, 500)
    view.show()
    try:
        view.gallery_model().set_rows([
            CardRow((str(i), "Z"), str(i)) for i in range(50)
        ])
        qapp.processEvents()
        bar = view.verticalScrollBar()
        bar.setValue(1000)
        for _ in range(8):
            _wheel(view, -15)
        assert bar.value() == 1080
    finally:
        view.close()
