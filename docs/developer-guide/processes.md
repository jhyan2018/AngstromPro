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

## From a scientific function to a reusable process

Start with `scale_image_stack()` in
`examples/example_plugin/src/angstrompro_example/processes.py`:

1. Keep numerical work in a function that accepts payloads and parameter values,
   not Qt widgets, selected rows, or acquisition-file paths.
2. Declare named inputs and exact dimensions in `ProcessSchema`. The supplied
   scaling example requires one `uds` image stack with `ndim=3`.
3. Expose user-adjustable choices through `ParameterSpec`, and describe the
   meaning and units of parameters. Check scientific preconditions inside the
   function, including axis compatibility for multi-input operations.
4. Return a new payload with an informative name and correct axes. Do not
   insert it into a workspace or write a file from inside the algorithm.
5. Import the registration module from the plugin's `__init__.py`, restart
   AngstromPro, and inspect it in **Process → Process Browser…**. Add it to
   a compatible module through **Process → Configure Process Menu…**.

The callable's `inputs` dictionary is keyed by `InputSpec.name` and contains
payloads, not `WorkspaceItem` objects. A module instead passes an ordered list
of `WorkspaceItem` objects to `submit_process()`; the runner performs the
conversion. This boundary lets the same algorithm be used from different
modules and in tests without depending on their display state.

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

Registration takes effect only when the decorated function's Python module is
imported. If AngstromPro startup already imports it, no extra plugin-path
configuration is needed. Otherwise, load it using one of the
[plugin mechanisms](plugins.md). Once registered, inspect it through
**Process → Process Browser…** and add it to a compatible module's menu through
**Process → Configure Process Menu…**; registration does not create a custom
submenu automatically. The repository includes a working
[example plugin](../../examples/example_plugin/README.md), whose
`src/angstrompro_example/processes.py` implements a scaling process and simulation.

Use globally unique, stable process IDs. A namespace such as
`example.scale_2D` avoids collisions and allows saved menu configuration to
survive label changes. Process callables accept `inputs`, `params`, and the
optional `annotations` keyword used by the runner.

## Execution

GUI modules should use `AGuiModule.submit_process()` rather than call expensive
functions on the Qt thread. The runner resolves inputs and annotations, merges
parameter defaults, and submits a task through the registry. The module's
result handler adds successful outputs to the workspace. The registry appends
history to outputs with a `proc_history` list and propagates source information
for UDS results. A process may return one workspace-data object or a nested
list/tuple of workspace-data objects.

The GUI input checks and parameter widgets are not a substitute for validation
inside the algorithm. In particular, synchronous registry calls do not perform
all GUI type, dimensionality, or parameter-range checks. Raise a clear
exception for unsupported inputs; do not open a GUI dialog from the worker.

Annotation roles are resolved from the first input item's `annotations`
dictionary. `AnnotationSpec.role` selects the stored role, while
`AnnotationSpec.name` becomes the key passed to the callable. A selected point
visible on a canvas is not automatically an annotation; the module must save
the required role before submission.

Processes that need to produce annotations or scalar quality measurements may
return `ProcessResult(data=..., annotations=..., metrics=...)`. Existing return
values remain fully supported and are normalized as data-only results by
workflow-aware callers. Annotation keys are workspace roles such as
`"bragg_peaks"`; metrics are named scalar values. Declare these optional ports
with `AnnotationOutputSpec` and `MetricOutputSpec` so workflow editors can
discover them before execution.

Use `register_simulation` for generators. Simulations may have no inputs and
appear under **Simulate**, not **Process**.

## Test the registered execution path

After installing the example plugin, run this Python code to exercise its
simulation and scaling process without opening a module window:

```python
import numpy as np
import angstrompro_example  # Import registrations before constructing the registry.
from angstrompro.core.processes import ProcessRegistry

registry = ProcessRegistry()
source = registry.run(
    "angstrompro_example.gaussian_stack", {}, {"size": 32, "sigma": 5.0}
)
original = source.data.copy()
result = registry.run(
    "angstrompro_example.scale_2D", {"data": source}, {"factor": 2.0}
)
np.testing.assert_allclose(result.data, original * 2.0)
np.testing.assert_array_equal(source.data, original)
assert result is not source
assert result.proc_history[-1].step == "angstrompro_example.scale_2D"
```

`ProcessRegistry.run()` is synchronous and suitable for tests or batch callers,
not for long-running GUI callbacks. It applies schema defaults and records
history, but it does not create a workspace item. Also test invalid inputs,
axes and units, any required annotations, and the GUI submission path before
distributing a scientific process.
