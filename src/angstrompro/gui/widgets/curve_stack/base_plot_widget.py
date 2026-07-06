# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Abstract base for all CurveStackViewer plot widgets.
Each concrete subclass owns its own Figure, Axes, and mode-specific controls.
"""
from __future__ import annotations

from abc import abstractmethod

from angstrompro.utils.qt_compat import QtWidgets


class BasePlotWidget(QtWidgets.QWidget):
    """
    Contract every plot mode widget must fulfil.

    The container (CurveStackViewerWidget) calls these methods when the
    dataset list or config changes.  Each subclass decides how to render.

    Entry dict shape (produced by prepare_entry)::

        {
            "uds":     UdsDataStru,
            "x":       np.ndarray  (n_pts,)
            "x_label": str
            "y":       np.ndarray  (n_curves, n_pts)
            "y_label": str
        }
    """

    def __init__(self, config: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self._config: dict = config or {}

    @abstractmethod
    def refresh(self, datasets: dict[str, dict],
                checked: dict[str, list[bool]]) -> None:
        """Redraw from the current datasets and visibility flags."""

    @abstractmethod
    def clear(self) -> None:
        """Wipe the canvas."""

    def apply_config(self, config: dict) -> None:
        self._config = config
