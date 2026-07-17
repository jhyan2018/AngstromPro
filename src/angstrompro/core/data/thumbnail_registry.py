# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 2026

@author: jiahaoYan

ThumbnailRegistry — pluggable registry of headless thumbnail renderers,
used by the Data Browser to decide which payloads are previewable and to
render their thumbnail PNGs.

Renderers key on the PAYLOAD TYPE the IO layer produces, not on the file
format: many formats yield the same payload type (sxm/3ds/saved .uds all
give uds objects) and one renderer serves them all.

Key
---
    (type_id, ndim)   e.g. ("uds", 2), ("uds", 3)
    (type_id, None)   ndim-independent payloads, e.g. ("scene_plot", None)

Renderer signature
------------------
    func(payload, *, rcparams_delta: dict, options: dict,
         figsize: tuple[float, float]) -> matplotlib.figure.Figure

The function must be headless (Agg-compatible, no Qt) and return a fully
drawn Figure; the caller saves it to PNG and closes it.

Registration
------------
angstrompro registers its built-in renderers at gui.modules.data_browser
import; plugins register their own payload types at their import time via::

    from angstrompro.core.data.thumbnail_registry import register_thumbnail_renderer
    register_thumbnail_renderer("my_type", None, my_render_func)
"""
from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)

_REGISTRY: dict[tuple[str, int | None], Callable] = {}


def register_thumbnail_renderer(type_id: str, ndim: int | None,
                                func: Callable) -> None:
    """Register *func* as the thumbnail renderer for (type_id, ndim)."""
    key = (type_id, ndim)
    if key in _REGISTRY:
        log.warning("Thumbnail renderer for %s overwritten", key)
    _REGISTRY[key] = func


def get_thumbnail_renderer(type_id: str, ndim: int | None) -> Callable | None:
    """Exact (type_id, ndim) match first, then ndim-independent fallback."""
    return _REGISTRY.get((type_id, ndim)) or _REGISTRY.get((type_id, None))


def is_previewable(type_id: str, ndim: int | None = None) -> bool:
    """True when a renderer exists for this payload type (any ndim if None)."""
    if ndim is not None:
        return get_thumbnail_renderer(type_id, ndim) is not None
    return any(t == type_id for t, _ in _REGISTRY)


def registered_keys() -> list[tuple[str, int | None]]:
    return list(_REGISTRY.keys())
