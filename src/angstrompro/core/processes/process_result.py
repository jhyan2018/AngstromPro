# -*- coding: utf-8 -*-
"""Structured process results with full legacy-return compatibility."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class ProcessResult:
    """Optional structured result returned by a registered process.

    ``data`` accepts the same values that processes historically returned: one
    workspace payload, a nested list/tuple of payloads, or a mapping of named
    outputs. ``annotations`` maps workspace annotation roles to annotation
    values. Normal process execution applies them to the primary input;
    workflows explicitly bind their destinations. ``values`` contains named
    numerical outputs (scalars or arrays), with optional ``value_units``.
    ``metrics`` is the older scalar interface and is included in ``values``.

    Existing processes do not need to return this type.
    """

    data: Any = None
    annotations: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, int | float | bool] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    value_units: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Legacy metric producers participate in the same result namespace.
        self.values = {**self.metrics, **self.values}


def normalize_process_result(value: Any) -> ProcessResult:
    """Return *value* as a :class:`ProcessResult` without copying payloads."""
    if isinstance(value, ProcessResult):
        return value
    return ProcessResult(data=value)


def iter_process_data(value: Any) -> Iterator[Any]:
    """Yield data outputs from legacy or structured process return values."""
    if isinstance(value, ProcessResult):
        yield from iter_process_data(value.data)
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_process_data(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from iter_process_data(child)
    elif value is not None:
        yield value


def primary_process_data(value: Any, default: Any = None) -> Any:
    """Return the first data output, or *default* when none was produced."""
    return next(iter_process_data(value), default)


def named_process_data(value: Any, name: str = "data") -> Any:
    """Resolve one named data output from a legacy or structured result."""
    result = normalize_process_result(value)
    data = result.data
    if isinstance(data, dict):
        if name not in data:
            raise KeyError(f"Process result has no data output {name!r}")
        return data[name]
    if name == "data":
        return primary_process_data(data)
    if isinstance(data, (list, tuple)) and name.isdigit():
        return data[int(name)]
    raise KeyError(f"Process result has no data output {name!r}")
