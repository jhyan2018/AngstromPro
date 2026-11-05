# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 2026

@author: jiahaoYan
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .param_schema import ProcessSchema


class ProcessUnavailableError(RuntimeError):
    """Raised when an optional dependency or resource is unavailable."""


@dataclass(frozen=True)
class ProcessRequirement:
    """A lazily evaluated prerequisite for a registered process.

    ``check`` receives the resolved process parameters and returns either a
    boolean or ``(available, detail)``. The callable must remain diagnostic:
    it should not perform the process itself or eagerly load a heavy backend.
    """

    name: str
    check: Callable[[dict[str, Any]], bool | tuple[bool, str]]
    label: str = ""
    install_hint: str = ""

    def status(self, params: dict[str, Any] | None = None) -> tuple[bool, str]:
        try:
            result = self.check(dict(params or {}))
        except Exception as exc:
            return False, f"check failed: {exc}"
        if isinstance(result, tuple):
            available, detail = result
        else:
            available, detail = bool(result), ""
        if not available and not detail:
            detail = self.install_hint or f"{self.label or self.name} is unavailable"
        return bool(available), str(detail)


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
    - requirements : optional dependencies/resources checked before execution
    """
    name:        str               # unique dotted ID  e.g. "spatial.crop"
    label:       str               # display name      e.g. "Crop"
    category:    str               # menu group        e.g. "Spatial"
    func:        Callable          # func(inputs: dict, params: dict) -> WorkspaceData
    schema:      ProcessSchema
    description: str = ""
    kind:        str = "process"   # "process" | "simulation"
    requirements: tuple[ProcessRequirement, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.requirements = tuple(self.requirements)

    def requirement_statuses(
        self, params: dict[str, Any] | None = None,
    ) -> list[tuple[ProcessRequirement, bool, str]]:
        return [
            (requirement, *requirement.status(params))
            for requirement in self.requirements
        ]

    def requirement_issues(
        self, params: dict[str, Any] | None = None,
    ) -> list[str]:
        issues = []
        for requirement, available, detail in self.requirement_statuses(params):
            if not available:
                label = requirement.label or requirement.name
                issues.append(f"{label}: {detail}")
        return issues

    def ensure_available(self, params: dict[str, Any] | None = None) -> None:
        issues = self.requirement_issues(params)
        if issues:
            raise ProcessUnavailableError(
                f"Process {self.label!r} is unavailable: {'; '.join(issues)}"
            )

    def run(self, inputs: dict, params: dict) -> Any:
        """Synchronous direct call — no threading, no progress."""
        self.ensure_available(params)
        return self.func(inputs, params)
