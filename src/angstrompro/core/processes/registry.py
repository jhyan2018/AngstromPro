# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 2026

@author: jiahaoYan

ProcessRegistry — central store for all registered data processes.

Registration
------------
Built-in processes use the @register_process decorator at module level.
Importing angstrompro.algorithms triggers all decorators via its __init__.
User processes are loaded dynamically via load_user_processes().

Process function signature
--------------------------
Every process function must follow this uniform signature:

    def my_process(inputs: dict, params: dict) -> WorkspaceData:
        data = inputs["data"]        # WorkspaceData from workspace
        x    = params["x"]          # scalar config value from dialog
        ...
        return UdsDataStru(...)      # new object — never mutate inputs

proc_history
------------
The registry automatically appends a ProcRecord to the returned
UdsDataStru after each call. Process functions do not need to touch it.

Usage
-----
    # Synchronous (batch / tests / headless)
    result = registry.run("spatial.crop",
                          inputs={"data": uds},
                          params={"x": 10, "width": 200})

    # Async via TaskManager (GUI)
    handle = registry.submit("spatial.crop",
                             inputs={"data": uds},
                             params={"width": 200},
                             source_id="image2u3_1",
                             task_manager=context.tasks)

    # Pipeline — chain of steps in one background task
    handle = registry.submit_pipeline(
        steps=[
            ("spectral.normalize_2d", {"data": uds}, {"method": "minmax"}),
            ("spectral.fft",       {},            {"shift": True}),
        ],
        source_id="image2u3_1",
        task_manager=context.tasks,
    )
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from .param_schema import ProcessSchema
from .process_entry import ProcessEntry

log = logging.getLogger(__name__)

_PENDING: list[ProcessEntry] = []


# ---------------------------------------------------------------------------
# @register_process decorator
# ---------------------------------------------------------------------------

def register_process(
    name:        str,
    label:       str,
    category:    str,
    schema:      ProcessSchema,
    description: str = "",
    kind:        str = "process",
):
    """
    Decorator that registers a process function into the registry.

    The function is returned unchanged so it remains directly callable.

    Example
    -------
        @register_process(
            name        = "spatial.crop",
            label       = "Crop",
            category    = "Spatial",
            schema      = ProcessSchema(
                inputs = [InputSpec("data", "uds")],
                params = [ParameterSpec("x_min", float, 0.0),
                          ParameterSpec("x_max", float, 1.0)],
            ),
            description = "Crop 1D data along the first axis.",
        )
        def crop(inputs: dict, params: dict) -> UdsDataStru:
            data  = inputs["data"]
            x_min = params["x_min"]
            ...
    """
    def decorator(func):
        _PENDING.append(ProcessEntry(
            name        = name,
            label       = label,
            category    = category,
            func        = func,
            schema      = schema,
            description = description,
            kind        = kind,
        ))
        return func
    return decorator


def register_simulation(
    name:        str,
    label:       str,
    category:    str,
    schema:      ProcessSchema,
    description: str = "",
):
    """Convenience alias for register_process with kind='simulation'.

    Simulations may have zero or more inputs — they generate synthetic data.
    They appear in the Simulate menu rather than the Process menu.
    """
    return register_process(
        name        = name,
        label       = label,
        category    = category,
        schema      = schema,
        description = description,
        kind        = "simulation",
    )


# ---------------------------------------------------------------------------
# proc_history helper
# ---------------------------------------------------------------------------

def _record_history(
    result:       Any,
    process_name: str,
    params:       dict,
    inputs:       dict,
    annotations:  dict | None = None,
) -> Any:
    """Append a ProcRecord to the result if it is a UdsDataStru."""
    from angstrompro.core.data.uds_data import UdsDataStru, ProcRecord
    from angstrompro.core.data.annotation_data import serialize_annotation
    if isinstance(result, UdsDataStru):
        input_item_names = [
            getattr(v, "name", "")
            for v in inputs.values()
            if hasattr(v, "name")
        ]
        serialized_annotations: dict = {}
        for role, ann in (annotations or {}).items():
            if ann is not None:
                try:
                    serialized_annotations[role] = serialize_annotation(ann)
                except TypeError:
                    pass   # unknown type — skip rather than crash
        result.proc_history.append(ProcRecord(
            step             = process_name,
            params           = dict(params),
            input_item_names = input_item_names,
            annotations      = serialized_annotations,
        ))
    return result


# ---------------------------------------------------------------------------
# Axis-type warning check
# ---------------------------------------------------------------------------

def _check_axis_types(entry: "ProcessEntry", inputs: dict) -> None:
    """Log warnings if input UDS axes don't match InputSpec.axis_types declarations."""
    from angstrompro.core.data.uds_data import UdsDataStru
    for spec in entry.schema.inputs:
        if not spec.axis_types:
            continue
        uds = inputs.get(spec.name)
        if not isinstance(uds, UdsDataStru):
            continue
        ndim = uds.data.ndim
        for idx, required_type in spec.axis_types.items():
            # resolve negative index
            resolved = idx if idx >= 0 else ndim + idx
            if resolved < 0 or resolved >= ndim or resolved >= len(uds.axes):
                log.warning(
                    "Process %r: input %r — axis[%d] out of range for ndim=%d",
                    entry.name, spec.name, idx, ndim,
                )
                continue
            actual_type = uds.axes[resolved].axis_type
            if actual_type != required_type:
                log.warning(
                    "Process %r: input %r — axis[%d] expected %s but got %s "
                    "(label: %r). Check axis orientation in the inspector.",
                    entry.name, spec.name, idx,
                    required_type.value, actual_type.value,
                    uds.axes[resolved].label,
                )


# ---------------------------------------------------------------------------
# ProcessRegistry
# ---------------------------------------------------------------------------

class ProcessRegistry:
    """
    Central registry for all data processing functions.

    Populated automatically when angstrompro.algorithms is imported,
    which triggers all @register_process decorators.
    """

    def __init__(self) -> None:
        import angstrompro.algorithms  # noqa: F401 — triggers @register_process decorators
        self._entries: dict[str, ProcessEntry] = {e.name: e for e in _PENDING}
        log.debug("ProcessRegistry loaded %d built-in process(es)", len(self._entries))

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> ProcessEntry:
        if name not in self._entries:
            raise KeyError(f"Unknown process: {name!r}")
        return self._entries[name]

    def has(self, name: str) -> bool:
        return name in self._entries

    def all_entries(self) -> list[ProcessEntry]:
        return list(self._entries.values())

    def by_category(self, kind: str | None = None) -> dict[str, list[ProcessEntry]]:
        """Return entries grouped by category, optionally filtered by kind."""
        result: dict[str, list[ProcessEntry]] = {}
        for entry in self._entries.values():
            if kind is not None and entry.kind != kind:
                continue
            result.setdefault(entry.category, []).append(entry)
        return result

    def by_kind(self, kind: str) -> list[ProcessEntry]:
        """Return all entries with the given kind ('process' or 'simulation')."""
        return [e for e in self._entries.values() if e.kind == kind]

    def by_input_type(self, type_id: str) -> list[ProcessEntry]:
        """Return all processes that accept the given workspace data type_id."""
        return [
            entry for entry in self._entries.values()
            if any(i.type_id == type_id or i.type_id == ""
                   for i in entry.schema.inputs)
        ]

    def compatible_with(self, type_id: str, ndim: int | None) -> list[ProcessEntry]:
        """
        Return all processes compatible with the given type_id and ndim.

        A process is compatible when every InputSpec satisfies both:
          - type_id matches (or either side is empty/None = wildcard)
          - ndim matches (or either side is None = wildcard)
        """
        result = []
        for entry in self._entries.values():
            if not entry.schema.inputs:
                continue
            if all(
                (not spec.type_id or not type_id or spec.type_id == type_id) and
                (spec.ndim is None or ndim is None or spec.ndim == ndim)
                for spec in entry.schema.inputs
            ):
                result.append(entry)
        return result

    # ------------------------------------------------------------------
    # Synchronous execution — batch / headless / tests
    # ------------------------------------------------------------------

    def run(self, name: str, inputs: dict, params: dict,
            annotations: dict | None = None) -> Any:
        """Direct synchronous call — no threading, no progress."""
        entry       = self.get(name)
        _check_axis_types(entry, inputs)
        full_params = {**entry.schema.defaults(), **params}
        result      = entry.func(inputs, full_params, annotations=annotations or {})
        return _record_history(result, name, full_params, inputs, annotations)

    # ------------------------------------------------------------------
    # Async execution — GUI / background batch
    # ------------------------------------------------------------------

    def submit(
        self,
        process_name: str,
        inputs:       dict,
        params:       dict,
        task_manager: Any,
        *,
        source_id:    str  = "",
        group_id:     str  = "",
        annotations:  dict | None = None,
    ) -> Any:
        """Run a single process on a background thread via TaskManager."""
        from angstrompro.core.tasks.task_request import TaskRequest

        entry       = self.get(process_name)
        full_params = {**entry.schema.defaults(), **params}
        resolved_annotations = annotations or {}

        def _task_func():
            _check_axis_types(entry, inputs)
            result = entry.func(inputs, full_params, annotations=resolved_annotations)
            return _record_history(result, process_name, full_params, inputs, resolved_annotations)

        return task_manager.submit(TaskRequest(
            task_func = _task_func,
            source_id = source_id,
            task_type = process_name,
            group_id  = group_id,
        ))

    def submit_pipeline(
        self,
        steps:        list[tuple[str, dict, dict, dict | None]],
        task_manager: Any,
        *,
        source_id:    str  = "",
        group_id:     str  = "",
        return_all:   bool = False,
    ) -> Any:
        """
        Run a sequence of processes as one background task.

        steps = [
            ("spectral.normalize_2d", {"data": uds}, {"method": "minmax"}, None),
            ("spectral.fft",       {},            {"shift": True},       None),
            ("spatial.register_2d",   {},            {"ratio": 2.0},        {"register_points": ann}),
        ]

        Each step is a 4-tuple: (process_name, inputs, params, annotations).
        annotations may be None or omitted (treated as {}).

        The first step must supply all its inputs explicitly.
        Subsequent steps receive the previous result as inputs["data"]
        unless they supply their own non-empty inputs dict.

        return_all : bool, default False
            False → return only the final step's result (default behaviour).
            True  → return a list of every step's result so all intermediate
                    outputs are added to the workspace.
        """
        from angstrompro.core.tasks.task_request import TaskRequest

        resolved: list[tuple[ProcessEntry, dict, dict, dict]] = []
        for step in steps:
            # accept both 3-tuple (legacy) and 4-tuple (with annotations)
            if len(step) == 4:
                name, step_inputs, step_params, step_annotations = step
            else:
                name, step_inputs, step_params = step
                step_annotations = {}
            entry = self.get(name)
            resolved.append((
                entry,
                step_inputs,
                {**entry.schema.defaults(), **step_params},
                step_annotations or {},
            ))

        _PREV = "__prev__"

        def _task_func():
            result  = None
            results = []
            for entry, step_inputs, full_params, step_ann in resolved:
                if step_inputs:
                    effective_inputs = {
                        k: (result if v == _PREV else v)
                        for k, v in step_inputs.items()
                    }
                else:
                    effective_inputs = {"data": result}
                result = entry.func(effective_inputs, full_params, annotations=step_ann)
                result = _record_history(result, entry.name, full_params,
                                         effective_inputs, step_ann)
                results.append(result)
            return results if return_all else result

        return task_manager.submit(TaskRequest(
            task_func = _task_func,
            source_id = source_id,
            task_type = "pipeline",
            group_id  = group_id,
        ))

    # ------------------------------------------------------------------
    # User plugin loading
    # ------------------------------------------------------------------

    def load_user_processes(self, directory: Path) -> None:
        """Dynamically load user .py process files from a directory."""
        if not directory.exists():
            return

        before = set(self._entries.keys())

        for path in sorted(directory.glob("*.py")):
            if path.stem.startswith("_"):
                continue
            module_name = f"angstrompro_user_process.{path.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod
                spec.loader.exec_module(mod)
                log.info("Loaded user process file: %s", path.name)
            except Exception as exc:
                log.error("Failed to load %s: %s", path.name, exc)

        for entry in _PENDING:
            if entry.name not in before:
                self._entries[entry.name] = entry

        new_count = len(self._entries) - len(before)
        if new_count:
            log.info("Registered %d user process(es) from %s", new_count, directory)
