"""
AHeadlessModule — headless base for all AngstromPro modules.

No Qt dependency — usable in batch/scripting contexts.

Subclass contract
-----------------
    class Image2U3Module(AHeadlessModule):
        module_id      = "image2u3"
        display_name   = "Image 2U3"
        description    = "STM image analysis."
        accepted_types = {"uds"}

        def run(self, ...): ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .module_mixin import ModuleMixin

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext


class AHeadlessModule(ModuleMixin):
    """Headless module — workspace and identity via ModuleMixin."""

    def __init__(self, context: "AppContext") -> None:
        super().__init__()
        self._init_module(context)
