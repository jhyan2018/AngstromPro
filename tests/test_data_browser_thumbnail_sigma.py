"""Thumbnail image contrast follows the Image Stack Viewer sigma scale."""

from __future__ import annotations

import numpy as np
import pytest

from angstrompro.core.configs.defaults.modules.data_browser import DEFAULTS
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.gui.modules.data_browser.data_browser_module import (
    DataBrowserModule,
)
from angstrompro.gui.modules.data_browser.thumbnail_cache import ThumbnailCache
from angstrompro.gui.modules.data_browser.thumbnail_renderers import render_uds_3d


def test_thumbnail_sigma_preference_range_and_default():
    assert DEFAULTS["thumbnails"]["sigma"] == 5.0
    section = next(
        section for section in DataBrowserModule.preferences_schema
        if section.title == "Thumbnails"
    )
    item = next(item for item in section.items
                if item.key == "thumbnails.sigma")
    assert item.widget == "number"
    assert item.kwargs == {"min": 1.0, "max": 10.0}


def test_thumbnail_sigma_uses_image_stack_viewer_formula_and_finite_values():
    image = np.array([[0.0, 1.0], [2.0, np.nan]])
    source = UdsDataStru.from_array(image[None, :, :], "image")

    figure = render_uds_3d(source, options={"sigma": 4.0})
    try:
        finite = image[np.isfinite(image)]
        mean = float(np.mean(finite))
        half_width = 4.0 * float(np.std(finite)) / 2.0
        assert figure.axes[0].images[0].get_clim() == pytest.approx(
            (mean - half_width, mean + half_width)
        )
    finally:
        figure.clear()


def test_thumbnail_sigma_is_applied_after_background_subtraction():
    y, x = np.mgrid[:5, :6]
    image = 4.0 * y + 2.0 * x
    image[2, 3] += 10.0
    source = UdsDataStru.from_array(image[None, :, :], "Z")

    figure = render_uds_3d(source, options={
        "channel_id": "Z",
        "z_background_method": "Polynomial surface",
        "sigma": 2.0,
    })
    try:
        displayed = np.asarray(figure.axes[0].images[0].get_array())
        expected = (
            float(np.mean(displayed)) - float(np.std(displayed)),
            float(np.mean(displayed)) + float(np.std(displayed)),
        )
        assert figure.axes[0].images[0].get_clim() == pytest.approx(expected)
        np.testing.assert_array_equal(source.data[0], image)
    finally:
        figure.clear()


def test_render_signature_invalidates_thumbnails_but_preserves_ratings(tmp_path):
    cache = ThumbnailCache(tmp_path)
    try:
        assert cache.ensure_render_signature("uds3d-sigma-v1:5")
        png = cache.thumb_dir / "old.png"
        png.write_bytes(b"old thumbnail")
        cache.upsert_file("sample.sxm", 1.0, "sxm", ["Z"])
        cache.upsert_thumbnail("sample.sxm", "Z", str(png))
        cache.set_stars("sample.sxm", "Z", 4)

        assert not cache.ensure_render_signature("uds3d-sigma-v1:5")
        assert cache.get_file("sample.sxm") is not None
        assert png.exists()

        assert cache.ensure_render_signature("uds3d-sigma-v1:3")
        assert cache.get_file("sample.sxm") is None
        assert cache.get_thumbnails("sample.sxm") == []
        assert not png.exists()
        assert cache.get_stars("sample.sxm", "Z") == 4
    finally:
        cache.close()
