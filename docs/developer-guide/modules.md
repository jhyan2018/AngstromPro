# Modules

GUI modules subclass `AGuiModule` and register at import time. The base class
provides File, View, Process, Simulate, and Help menus; workspace and inspector
docks; sending; preferences; and task-result routing.

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
    accepted_ndim = 2

    def build_ui(self) -> None:
        self.setCentralWidget(QtWidgets.QLabel("Ready"))

    def on_item_loaded(self, item) -> None:
        pass
```

Import the module before `AppContext` finishes construction. Built-in imports
are collected in `angstrompro.gui.modules`; external packages normally import
their modules from a plugin entry point.

## Identity and compatibility

- `module_id` must be stable because configuration and startup lists store it.
- Plugin module IDs should begin with the plugin namespace and a dot, such as
  `example.my_module`.
- `display_name`, `category`, and `description` are user-facing.
- `accepted_ndim` provides basic compatibility filtering.
- `max_instances` can limit singleton-style modules.

Namespaced plugin modules receive isolated plugin configuration automatically.

## Process and simulation menus

Set `default_process_menu` to registered process IDs that should always appear
for the module. Set `default_simulate_menu` for registered simulations. The
runtime menu merges class defaults, developer configuration, and user-added
entries without allowing users to remove developer defaults.

## Input roles

`process_inputs` contains the workspace items staged for the next operation.
Modules with several roles can set `staged_labels` and `clearable_slots` to make
those assignments visible in the workspace dock.

## Preferences

A module may expose a `preferences_schema` made of `PrefSection` and `PrefItem`
objects. Keep defaults in `core/configs/defaults/modules/` for built-ins. Plugin
modules should register their own defaults with the plugin configuration before
reading values.
