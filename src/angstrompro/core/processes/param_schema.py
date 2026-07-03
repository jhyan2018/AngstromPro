# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 2026

@author: jiahaoYan
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnnotationSpec:
    """Describes one annotation input required by a process.

    name    — key used in the annotations dict passed to the process function
    role    — annotation role: "bragg_peaks" | "interest_region" | "line_cut"
    type_id — data type: "point_set" | "region" | "line"
    required — if True, raises ValueError when annotation is missing at run time
    Always resolves from process_inputs[0].annotations[role].
    """
    name:     str
    role:     str       # "bragg_peaks" | "interest_region" | "line_cut"
    type_id:  str       # "point_set" | "region" | "line"
    required: bool = True


@dataclass
class InputSpec:
    """Describes one named data input of a process function."""
    name:        str
    type_id:     str        # workspace data type: "uds" | "scene" | … (empty = any)
    label:       str        = ""
    description: str        = ""
    ndim:        int | None = None  # required array dimensionality; None = any
    required:    bool       = True  # False = optional input; process receives None if absent

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.name.replace("_", " ").title()


@dataclass
class ParameterSpec:
    """Describes one scalar configuration parameter of a process function."""
    name:        str
    type:        type               # int | float | bool | str
    default:     Any
    label:       str        = ""
    units:       str        = ""
    min:         Any        = None  # lower bound for numeric spinboxes
    max:         Any        = None  # upper bound for numeric spinboxes
    step:        Any        = None  # spinbox step; None = auto
    choices:     list       = field(default_factory=list)  # non-empty → combo-box
    description: str        = ""

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.name.replace("_", " ").title()


class ProcessSchema:
    """
    Declares both the data inputs and the scalar parameters of a process.

    inputs : list[InputSpec]      — named data objects fed from the workspace
    params : list[ParameterSpec]  — scalar config values shown in the param dialog
    """

    def __init__(
        self,
        inputs:      list[InputSpec]      | None = None,
        params:      list[ParameterSpec]  | None = None,
        annotations: list[AnnotationSpec] | None = None,
    ) -> None:
        self._inputs:      list[InputSpec]      = inputs or []
        self._params:      list[ParameterSpec]  = params or []
        self._annotations: list[AnnotationSpec] = annotations or []
        self._params_by_name = {p.name: p for p in self._params}

    @property
    def inputs(self) -> list[InputSpec]:
        return self._inputs

    @property
    def params(self) -> list[ParameterSpec]:
        return self._params

    def get_param(self, name: str) -> ParameterSpec | None:
        return self._params_by_name.get(name)

    def defaults(self) -> dict[str, Any]:
        """Return {name: default} for all parameters."""
        return {p.name: p.default for p in self._params}

    @property
    def annotations(self) -> list[AnnotationSpec]:
        return self._annotations

    def input_type_ids(self) -> list[str]:
        """Return the type_id of every input port."""
        return [i.type_id for i in self._inputs]
