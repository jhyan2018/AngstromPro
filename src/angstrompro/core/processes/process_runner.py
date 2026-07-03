# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 2026

@author: jiahaoYan
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from angstrompro.core.tasks.task_handle import TaskHandle

if TYPE_CHECKING:
    from angstrompro.core.tasks.task_manager import TaskManager
    from angstrompro.core.workspaces.workspace_item import WorkspaceItem
    from .registry import ProcessRegistry

log = logging.getLogger(__name__)


class ProcessRunner:
    """
    Convenience bridge between ProcessRegistry and TaskManager.

    Resolves WorkspaceItems to named inputs dicts, merges param defaults,
    and submits via the registry's submit / submit_pipeline methods.

    Modules use this via AGuiModule.submit_process() rather than
    calling ProcessRunner directly.
    """

    def __init__(self, task_manager: TaskManager, registry: ProcessRegistry) -> None:
        self._task_manager = task_manager
        self._registry     = registry

    # ------------------------------------------------------------------
    # Single process
    # ------------------------------------------------------------------

    def run(
        self,
        process_name: str,
        input_items:  list[WorkspaceItem],
        params:       dict[str, Any] | None = None,
        *,
        source_id:    str = "",
        group_id:     str = "",
    ) -> TaskHandle:
        """
        Submit a registered process as a background task.

        Parameters
        ----------
        process_name:
            Dotted process id, e.g. "spatial.crop".
        input_items:
            Ordered list of WorkspaceItems matched to schema.inputs by order.
        params:
            Override values for scalar parameters. Missing keys fall back
            to ProcessSchema defaults.
        """
        entry  = self._registry.get(process_name)
        inputs = self._build_inputs(entry, input_items)
        merged = {**entry.schema.defaults(), **(params or {})}

        # Resolve annotations from the primary input item
        resolved_annotations = self._build_annotations(entry, input_items)

        log.debug(
            "ProcessRunner.run: %s  inputs=[%s]  params=%s",
            process_name,
            ", ".join(item.name for item in input_items if item is not None),
            list(merged.keys()),
        )

        return self._registry.submit(
            process_name = process_name,
            inputs       = inputs,
            params       = merged,
            task_manager = self._task_manager,
            source_id    = source_id,
            group_id     = group_id,
            annotations  = resolved_annotations,
        )

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        steps:     list[tuple[str, list[WorkspaceItem], dict[str, Any]]],
        *,
        source_id: str = "",
        group_id:  str = "",
    ) -> TaskHandle:
        """
        Submit a pipeline of processes as one background task.

        steps = [
            ("spectral.normalize", [item],  {"method": "minmax"}),
            ("spectral.fft",       [],      {"shift": True}),
            ("spatial.register",   [item],  {"ratio": 2.0}),
        ]

        Steps with an empty item list receive the previous result as
        inputs["data"] automatically.  Annotations are resolved automatically
        from the first item in each step's item list (same rule as run()).
        """
        resolved_steps = []
        for process_name, items, params in steps:
            entry       = self._registry.get(process_name)
            inputs      = self._build_inputs(entry, items) if items else {}
            annotations = self._build_annotations(entry, items) if items else {}
            resolved_steps.append((process_name, inputs, params, annotations))

        return self._registry.submit_pipeline(
            steps        = resolved_steps,
            task_manager = self._task_manager,
            source_id    = source_id,
            group_id     = group_id,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _build_inputs(entry, items: list[WorkspaceItem]) -> dict:
        """Map WorkspaceItems to a named inputs dict by schema order.

        Required inputs must be present; optional inputs (spec.required=False)
        that have no staged item are mapped to None.
        """
        input_specs = entry.schema.inputs
        n_required  = sum(1 for s in input_specs if s.required)
        if len(items) < n_required:
            raise ValueError(
                f"Process '{entry.name}' requires {n_required} input(s) "
                f"({[s.name for s in input_specs if s.required]}), got {len(items)}."
            )
        result = {}
        for i, spec in enumerate(input_specs):
            if i < len(items):
                result[spec.name] = items[i].payload
            else:
                result[spec.name] = None   # optional input not staged
        return result

    @staticmethod
    def _build_annotations(entry, items: list[WorkspaceItem]) -> dict:
        """Resolve annotation inputs from the primary WorkspaceItem."""
        ann_specs = getattr(entry.schema, 'annotations', [])
        if not ann_specs or not items:
            return {}
        primary_item = items[0]
        resolved: dict = {}
        for spec in ann_specs:
            ann = primary_item.annotations.get(spec.role)
            if ann is None and spec.required:
                raise ValueError(
                    f"Process '{entry.name}' requires annotation '{spec.role}' "
                    f"on item '{primary_item.name}' but none is set."
                )
            resolved[spec.name] = ann
        return resolved
