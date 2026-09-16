# Processes

A process is a pure or mostly pure callable registered with metadata and a
`ProcessSchema`. Registration supplies the information needed for discovery,
compatibility checks, parameter dialogs, background execution, and the Process
Browser. Process-menu submenu names and ordering are user-defined rather than
derived from registration categories.

## Example

```python
from copy import deepcopy

from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)


@register_process(
    name="example.scale_2D",
    label="Scale",
    category="Example",
    description="Multiply an image stack by a scalar.",
    schema=ProcessSchema(
        inputs=[InputSpec("data", "uds", ndim=3)],
        outputs=[OutputSpec("uds", ndim=3)],
        params=[ParameterSpec("factor", float, 1.0)],
    ),
)
def scale(inputs: dict, params: dict, annotations=None):
    source = inputs["data"]
    result = deepcopy(source)
    result.data = source.data * params["factor"]
    return result
```

Confirm the concrete data class supports the copying operation used by your
process. Never mutate the input merely to avoid allocating a result.

## Schema fields

- `InputSpec` declares name, type, dimensionality, optionality, and axis hints.
- `OutputSpec` declares result compatibility, especially for simulations.
- `ParameterSpec` declares scalar type, default, range, step, choices, units,
  and description.
- `AnnotationSpec` resolves a named annotation role from the primary input.

Axis hints inform users and can produce warnings; they do not replace explicit
validation required by a scientific algorithm.

For a numeric parameter whose valid range comes from an input axis, set
`axis_input`, `axis_index`, and `axis_default` (`"min"` or `"max"`). The
parameter dialog creates a per-dialog copy of that specification, derives its
bounds, initial value, units, and step from the staged input, and leaves the
registered schema unchanged. `decimals` controls the precision of float
spinboxes. The process backend must still support the schema's static default,
because headless callers do not open the parameter dialog.

## Registration and discovery

Decorators append entries during module import. Built-in algorithms are
imported by `angstrompro.algorithms`. Plugin processes must be imported by the
plugin entry module before `ProcessRegistry` is created.

Use globally unique, stable process IDs. A namespace such as
`example.scale_2D` avoids collisions and allows saved menu configuration to
survive label changes. Process callables accept `inputs`, `params`, and the
optional `annotations` keyword used by the runner.

## Execution

GUI callers should use `ProcessRunner` or registry submission rather than call
expensive functions on the Qt thread. The runner resolves inputs and
annotations, validates parameters, submits a task, and routes successful
results back to the source module. The registry adds processing history to
supported results. A process may return one workspace-data object or a nested
list/tuple of workspace-data objects; source propagation and the new history
record are applied to every returned object.

Use `register_simulation` for generators. Simulations may have no inputs and
appear under **Simulate**, not **Process**.
