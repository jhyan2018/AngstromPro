# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 2026

@author: jiahaoYan
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .param_schema import ProcessSchema


@dataclass
class ProcessEntry:
    """
    Full description of one registered data process.

    Process function contract
    -------------------------
    Every process function must follow this uniform signature:

        def my_process(inputs: dict, params: dict) -> WorkspaceData:
            data  = inputs["data"]    # WorkspaceData object from workspace
            x     = params["x"]      # scalar config value from dialog / caller
            ...
            return UdsDataStru(...)   # new object — never mutate inputs

    - inputs : named WorkspaceData objects declared in schema.inputs
    - params : scalar values declared in schema.params
    """
    name:        str               # unique dotted ID  e.g. "spatial.crop"
    label:       str               # display name      e.g. "Crop"
    category:    str               # menu group        e.g. "Spatial"
    func:        Callable          # func(inputs: dict, params: dict) -> WorkspaceData
    schema:      ProcessSchema
    description: str = ""
    kind:        str = "process"   # "process" | "simulation"

    def run(self, inputs: dict, params: dict) -> Any:
        """Synchronous direct call — no threading, no progress."""
        return self.func(inputs, params)
