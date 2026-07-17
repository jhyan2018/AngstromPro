# -*- coding: utf-8 -*-
"""
Created on 2026-07-14

@author: jiahaoYan

SceneBus — mutation notifications for the CurveStackViewer scene model.

Complements ViewerContext (identity: "what is active") with the other half:
"what data just changed".  Whoever mutates the RuntimeScene emits here;
subscribers react with the cheapest matching update.

Signals are granular so the plot widget can map each one to the cheapest
matplotlib operation instead of a full rebuild.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore


class SceneBus(QtCore.QObject):
    """Scene-mutation notifications. Emit AFTER writing the RuntimeScene."""

    axes_config_changed = QtCore.pyqtSignal()       # AxesSpec.config edited
    line_style_changed  = QtCore.pyqtSignal(tuple)  # per-line pin (ds_name, row)
    artists_changed     = QtCore.pyqtSignal()       # dataset added / removed
    scene_replaced      = QtCore.pyqtSignal()       # whole scene loaded / cleared
