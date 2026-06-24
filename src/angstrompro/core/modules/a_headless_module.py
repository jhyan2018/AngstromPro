# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:46:45 2026

@author: jiahaoYan

AHeadlessModule — pure Python base for all AngstromPro modules.

Holds the workspace and module identity. No Qt dependency — usable in
headless/batch contexts and independently testable.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .module_mixin import ModuleMixin

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext


class AHeadlessModule(ModuleMixin):
    """Headless module — workspace and identity via ModuleMixin."""

    def __init__(self, context: "AppContext") -> None:
        self._init_module(context)
