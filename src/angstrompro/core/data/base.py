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

from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class ProcRecord:
    """One processing step recorded in a WorkspaceData proc_history."""
    step:             str                = ""
    params:           dict               = field(default_factory=dict)
    input_item_names: list[str]          = field(default_factory=list)
    annotations:      dict               = field(default_factory=dict)


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

    def inspect_fields(self) -> list[dict[str, Any]]:
        """Return a structured description of this object's fields for the inspector.

        Each entry is a dict with a ``kind`` key:
          {"kind": "value",  "label": str, "value": str}
          {"kind": "array",  "label": str, "array": np.ndarray}
          {"kind": "group",  "label": str, "summary": str, "children": list}
          {"kind": "axis",   "label": str, "summary": str,
                             "axis": Axis, "children": list}

        The default implementation reflects all public non-callable attributes.
        Override in concrete subclasses to give a curated, ordered view.
        """
        import numpy as np
        nodes: list[dict[str, Any]] = []
        for attr in vars(self):
            if attr.startswith("_"):
                continue
            val = getattr(self, attr)
            if callable(val):
                continue
            if isinstance(val, np.ndarray):
                nodes.append({"kind": "array", "label": attr, "array": val})
            else:
                nodes.append({"kind": "value", "label": attr, "value": repr(val)})
        return nodes

    def __repr__(self) -> str:
        s = self.summary()
        parts = ", ".join(f"{k}={v}" for k, v in s.items())
        return f"{self.__class__.__name__}({parts})"
