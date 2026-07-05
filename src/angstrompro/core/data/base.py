# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:30:33 2026

@author: jiahaoYan

WorkspaceData — base class for all runtime data types held in a WorkspaceItem.

Every concrete type must:
  1. Set a unique  type_id  class variable (str, lowercase, no spaces).
  2. Override  display_type()  with a human-readable name.
  3. Override  summary()  with key facts for the workspace inspector / browser.

IO (save / load) is kept entirely separate in the angstrom_io registry.
Data classes are pure data containers — no IO code lives here.
"""

from __future__ import annotations

from typing import ClassVar


class WorkspaceData:
    """Base class for all runtime data types held in a WorkspaceItem."""

    type_id: ClassVar[str] = ""

    # ------------------------------------------------------------------
    # Display interface — override in every concrete subclass
    # ------------------------------------------------------------------

    def display_type(self) -> str:
        """Human-readable type name shown in the workspace UI.

        Examples: 'Spectroscopy Stack', 'Plot Scene', 'Lattice Structure'
        Default falls back to type_id.
        """
        return self.type_id or "Unknown"

    def summary(self) -> dict[str, str]:
        """Key facts about this object for the workspace inspector / quick browser.

        Returns an ordered dict of label → value strings.
        Keep values short (one line each) — they are displayed in a table.

        Example (UdsDataStru):
            {"Shape": "10 × 128 × 128", "dtype": "float32", "Axes": "E, x, y"}
        """
        return {"Type": self.display_type()}

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        s = self.summary()
        parts = ", ".join(f"{k}={v}" for k, v in s.items())
        return f"{self.__class__.__name__}({parts})"
