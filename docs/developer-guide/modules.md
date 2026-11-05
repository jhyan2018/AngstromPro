# Modules

GUI modules subclass `AGuiModule` and register at import time. The base class
provides File, View, and Process menus; workspace and inspector docks; sending;
preferences; and task-result routing. The Simulate menu appears only when the
module declares a non-empty `default_simulate_menu`. The Help menu appears only
when the subclass adds actions through `_populate_help_menu()`; neither menu
is shown automatically for every module.

See [Tasks and background execution](tasks.md) before adding long-running work
or directly submitting infrastructure tasks from a module.

Modules share the same generic workspace contract even when they operate on
different payload types. A new module can introduce a new `WorkspaceData` type,
wrap it in `WorkspaceItem`, and use the existing Inspector and send workflow.
Composite module state should normally be represented as one coherent payload,
as `ScenePlot` does for plot structure and its embedded UDS data.

## Minimal module

```python
from angstrompro.core.modules import AGuiModule, register_module
from angstrompro.utils.qt_compat import QtWidgets


@register_module
class MyModule(AGuiModule):
    module_id = "example.my_module"
    display_name = "My Module"
    category = "Analysis"
    description = "An example plugin module."
    accepted_types = {"uds"}
    accepted_ndim = 2

    def build_ui(self) -> None:
        self.setCentralWidget(QtWidgets.QLabel("Ready"))

    def on_item_loaded(self, item) -> None:
        self.process_inputs = [item]
```

Import the module before `AppContext` finishes construction. Built-in imports
are collected in `angstrompro.gui.modules`; external packages normally import
their modules from a plugin entry point.

`AGuiModule` is the shared GUI base class; `register_module` is the decorator
that registers a subclass when its Python module is imported. Merely writing
the decorator in a file does not make that file discoverable. If startup
already imports the registration code, no additional plugin configuration is
required. Otherwise, use a [plugin-loading method](plugins.md) to import it;
plugin loading is not a second registration step.

After registration, the example above appears under **+ New Module → Analysis
→ My Module**. The repository's
[example plugin](../../examples/example_plugin/README.md) includes installation
instructions and `src/angstrompro_example/module.py`, which shows input staging
and `submit_process()` calls for task-backed operations.

## Identity and compatibility

- `module_id` must be stable because configuration and startup lists store it.
- `instance_id` identifies one live window. Store active datasets and display
  state on the instance rather than in class attributes or module globals.
- Plugin module IDs should begin with the plugin namespace and a dot, such as
  `example.my_module`.
- `display_name`, `category`, and `description` are user-facing.
- `accepted_ndim` provides basic compatibility filtering.
- `max_instances` can limit singleton-style modules.

Namespaced plugin modules receive isolated plugin configuration automatically.

`accepted_types` and `accepted_ndim` describe the module's capabilities; they
do not validate every scientific assumption. In `on_item_loaded()`, check the
payload and any required axes before staging it or updating the display.
The bundled example performs this check before accepting a three-dimensional
image stack. The minimal module above only stages data; it does not draw it.

## Process and simulation menus

Process submenus are user-owned and stored in the versioned
`algorithms.process_menu_layouts` configuration. A module with no explicit
layout shows only Process Browser and Configure Process Menu. The legacy
`default_process_menu`, `algorithms.process_menus`, and
`algorithms.user_process_menus` declarations are ignored. Existing JSON files
containing the retired configuration keys still load without migration errors.

Set `default_simulate_menu` for registered simulations. Simulation grouping
continues to use process registration categories and is independent of the
user-defined Process menu layout.

## Input roles

`process_inputs` contains the workspace items staged for the next operation.
Modules with several roles can set `staged_labels` and `clearable_slots` to make
those assignments visible in the workspace dock.

Keep these inputs separate from the Workspace's highlighted row and from any
collection of displayed datasets. Assign a new list such as
`self.process_inputs = [primary_item, reference_item]` when the user changes
roles; the property setter updates the visible input slots. The order must
match the process's `InputSpec` declarations. Pass `WorkspaceItem` objects
here, not their NumPy arrays or payloads.

## Follow the example module

In `examples/example_plugin/src/angstrompro_example/module.py`:

1. `build_ui()` creates controls in the central widget. Standard menus,
   Workspace, and Inspector remain the base class's responsibility.
2. **Generate synthetic data** submits the registered simulation with an empty
   input list. The normal result handler adds its output to the workspace.
3. Double-clicking a workspace item calls `on_item_loaded()`, which checks its
   dimensionality and assigns `self.process_inputs = [item]`.
4. **Scale active data** reads the factor control and calls `submit_process()`
   with the registered process ID, staged item, and parameter dictionary.
5. The task result becomes a new workspace item and can be inspected, saved,
   or sent through the common controls.

Custom action buttons should follow this submission path rather than call the
algorithm on the Qt thread or manually add its result a second time. Use
`self.workspace` for new outputs, and `notify_workspace_item_changed(item)`
when changing an existing item's annotations so its owning workspace is
notified even if the module is attached to a shared workspace.

## Preferences

A module may expose a `preferences_schema` made of `PrefSection` and `PrefItem`
objects. Keep defaults in `core/configs/defaults/modules/` for built-ins. Plugin
modules should register their own defaults with the plugin configuration before
reading values.
