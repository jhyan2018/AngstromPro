from __future__ import annotations

import pytest

from angstrompro.core.processes import (
    ProcessEntry,
    ProcessRegistry,
    ProcessRequirement,
    ProcessSchema,
    ProcessUnavailableError,
)


def _entry(requirement, called):
    def process(inputs, params, *, annotations=None):
        called.append((inputs, params, annotations))
        return None

    return ProcessEntry(
        name="test.optional",
        label="Optional Process",
        category="Test",
        func=process,
        schema=ProcessSchema(),
        requirements=(requirement,),
    )


def test_requirement_receives_resolved_parameters_and_blocks_execution():
    seen = []
    requirement = ProcessRequirement(
        "resource",
        lambda params: (
            params.get("resource") == "ready",
            "select an available resource",
        ),
        label="External resource",
    )
    entry = _entry(requirement, seen)
    registry = ProcessRegistry()
    registry._entries[entry.name] = entry

    with pytest.raises(ProcessUnavailableError, match="select an available resource"):
        registry.run(entry.name, {}, {"resource": "missing"})
    assert seen == []

    registry.run(entry.name, {}, {"resource": "ready"})
    assert seen[0][1]["resource"] == "ready"


def test_requirement_check_failures_are_reported_as_unavailable():
    def broken(_params):
        raise OSError("backend failed to load")

    requirement = ProcessRequirement("backend", broken, label="Backend")
    entry = _entry(requirement, [])

    assert entry.requirement_issues({}) == [
        "Backend: check failed: backend failed to load"
    ]
