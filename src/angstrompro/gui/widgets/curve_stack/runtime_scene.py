# -*- coding: utf-8 -*-
"""
Created on 2026-07-13

@author: jiahaoYan

RuntimeScene — single source of truth for the CurveStackViewer at runtime.

ScenePlot holds everything that is saved to disk.  RuntimeScene wraps it with
the two flags that are runtime-only and meaningless outside the live session:
  dirty           — unsaved changes (shown as asterisk in title bar)
  active_axes_idx — which AxesSpec is currently focused in the UI

All GUI widgets read from and write to _scene.scene only.
Save scene  → copy.deepcopy(_scene.scene) → workspace item.
Save template → extract _scene.scene.rcparams_delta → write .scet file.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from angstrompro.core.data.scene_plot import ScenePlot, FigureConfig


@dataclass
class RuntimeScene:
    """Live wrapper around ScenePlot — the only authoritative state in the viewer."""
    scene:           ScenePlot = field(default_factory=ScenePlot)
    dirty:           bool      = False
    active_axes_idx: int       = 0

    # ── convenience accessors ────────────────────────────────────────────────

    @property
    def active_axes(self):
        axes = self.scene.figure.axes_list
        if not axes:
            return None
        idx = min(self.active_axes_idx, len(axes) - 1)
        return axes[idx]

    def mark_dirty(self) -> None:
        self.dirty = True

    def mark_clean(self) -> None:
        self.dirty = False

    # ── scene replacement ────────────────────────────────────────────────────

    def replace(self, new_scene: ScenePlot) -> None:
        """Replace scene entirely (on ScenePlot load). Resets runtime flags."""
        self.scene           = new_scene
        self.dirty           = False
        self.active_axes_idx = 0

    # ── save helpers ─────────────────────────────────────────────────────────

    def snapshot(self) -> ScenePlot:
        """Deep-copy of current scene — safe to hand to workspace / IO."""
        return copy.deepcopy(self.scene)

    def rcparams_delta(self) -> dict:
        """Current rcParams delta — used when saving a template."""
        return dict(self.scene.rcparams_delta)

    # ── reset ────────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Wipe to a blank scene."""
        self.scene           = ScenePlot(figure=FigureConfig())
        self.dirty           = False
        self.active_axes_idx = 0
