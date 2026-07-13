# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

NavToolbar — trimmed matplotlib NavigationToolbar2QT.

Keeps only: Home, Back, Forward, Pan, Zoom, Save.
Removes: Edit curves (replaced by ArtistStylePanel + AxesConfigPanel),
         Subplots adjust (replaced by figure layout controls when needed).
"""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT


class NavToolbar(NavigationToolbar2QT):
    """Navigation toolbar with style/edit tools removed."""

    toolitems = [
        t for t in NavigationToolbar2QT.toolitems
        if t[0] in ("Home", "Back", "Forward", None, "Pan", "Zoom", "Save")
    ]
