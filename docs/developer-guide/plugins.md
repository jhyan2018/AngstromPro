# Plugins

Start with the working plugin in `AngstromPro/examples/example_plugin/`.
Its [README](../../examples/example_plugin/README.md) provides installation
instructions and a workflow for checking that the registered components load.

Plugins extend AngstromPro by importing code that registers processes, modules,
or file-format handlers. They load before the process registry is constructed.

Modules and processes describe what an extension provides; a plugin describes
how those components are organised, distributed, and loaded. A plugin may
provide a single algorithm or several modules, processes, and file handlers.
Loading imports the registration code, rather than registering it a second
time. If that code is already imported during AngstromPro startup, no
additional plugin configuration is required.

A plugin may also define new `WorkspaceData` payload types. Doing so lets its
modules participate in the standard workspace, sending, compatibility, and
Inspector infrastructure. See [Runtime data and workspaces](workspaces.md).

## Choose the extension points you need

The extension points are independent; a plugin can provide any subset.

| Requirement | Extension | Integration |
| --- | --- | --- |
| A new interaction or visualisation model | `AGuiModule` with `register_module` | Main Workbench's **+ New Module** menu |
| A new numerical algorithm or generator | `register_process` or `register_simulation` | Process Browser and compatible Process menus, or Simulate menus |
| A new acquisition or native file format | `register_ext_loader` or `register_io` | File loading and, where implemented, saving |
| A richer analysis object | A `WorkspaceData` subclass with its own `type_id` | Workspace storage, transfer, and inspection; compatible consumers are still required |
| A preview for a new payload | `register_thumbnail_renderer` | Headless Data Browser thumbnail rendering |

For example, an algorithm acting on ordinary UDS data needs a process but not
a new viewer. A new instrument reader can reuse UDS viewers and renderers.
A composite object can retain several UDS datasets and additional state, but
its class definition alone supplies neither a viewer nor file persistence.
See [I/O handlers](io-handlers.md) for file and preview integration.

## Local source plugin

During development, open the Main Workbench's **File → Preferences… → Plugins**
(on macOS, open **Preferences…** from the application menu). Add an entry containing:

- The absolute path to the plugin's `src/` directory
- Its importable top-level module name

On the next launch, AngstromPro adds the path to `sys.path` and imports the
module. The module's imports must trigger every required registration. This
source-folder mechanism does not install the plugin package or any of its
dependencies; install those into the same Python environment first.

Click **Add plugin** and, for the supplied example, enter
`<repository>/examples/example_plugin/src` as the path and
`angstrompro_example` as the module name. Replace `<repository>` with the
absolute path to your checkout. Click **Save as default** and restart AngstromPro.

After changing plugin source, fully exit and restart AngstromPro so the
revised modules and widget classes are imported.

## Installed plugin

An installable package should expose an entry point in `pyproject.toml`:

```toml
[project.entry-points."angstrompro.plugins"]
example = "angstrompro_example"
```

The referenced object or module is loaded at startup. Installing the package
also installs the dependencies declared by that package, so this is the
recommended route for normal users. Do not also configure the same plugin as a
local source plugin. Keep its top-level import focused on registration; avoid
opening windows or starting independent event loops during import.

Install the package in the same Python environment as AngstromPro. With
AngstromPro already installed, run this from the repository root:

```bash
python -m pip install -e "examples/example_plugin"
```

Restart AngstromPro and open **+ New Module → Examples → Example Workflow**.
An installed entry-point plugin needs no source-path preference. Choose either
this installation method or local source loading; configuring both is unnecessary.

## Suggested layout

```text
angstrompro-example/
  pyproject.toml
  src/
    angstrompro_example/
      __init__.py
      modules.py
      processes.py
      io.py
```

`__init__.py` can import the three registration modules. Use a consistent
namespace for module and process IDs.

For the supplied example, the actual filename is `module.py` (singular).
Its `__init__.py` imports `io`, `processes`, and `module`, so all registrations
run when `angstrompro_example` is imported. Import any additional renderer or
I/O registration files in the same way. The entry-point loader imports the
target; it does not automatically call a separate setup function returned by
that import, or discover every Python file in the package.

## Configuration

Call `context.get_plugin_config("example")` for isolated settings. Namespaced
GUI module IDs such as `example.viewer` automatically select the corresponding
plugin configuration. Files are stored under
`<UserDataFolder>/config/plugins/`.

Register defaults before reading configuration, validate user values, and
store only settings owned by the plugin. Do not edit the core `config.json`
directly.

## Failure handling

A failing plugin import is logged and startup continues. The Main Workbench
automatically shows its **Log** dock with the full import traceback, and
**Preferences → Plugins** shows the result of every plugin load attempt from
the current startup. The same traceback is retained in `angstrompro.log`.
Plugin configuration changes require an application restart; a Spyder-hosted
session also requires a kernel restart. Duplicate loading by path and entry
point is skipped when AngstromPro can identify the same top-level module.

Plugin authors must review license compatibility for AngstromPro, the plugin,
and all dependencies before distribution.

## Complete example

The repository includes an installable
[example plugin](../../examples/example_plugin/README.md) that registers a GUI
module, process, simulation, and raw file loader. It uses synthetic data and
executes its operations through the normal task-backed process path. Its README
also gives the exact **File → Preferences… → Plugins** values for loading the example
directly from its `src/` folder during development.

Read the example in this order; paths below are relative to
`examples/example_plugin/`:

| File | What it demonstrates |
| --- | --- |
| `pyproject.toml` and `src/angstrompro_example/__init__.py` | Package discovery and registration imports |
| `src/angstrompro_example/io.py` and `sample.apdemo` | Raw JSON parsing, input validation, and UDS axes |
| `src/angstrompro_example/processes.py` | A no-input simulation and an input-preserving scaling process |
| `src/angstrompro_example/module.py` | Central controls, input staging, and task-backed submission |

The example does not define a new payload type or custom thumbnail renderer;
those optional interfaces are described in the
[workspace](workspaces.md#adding-a-payload-type) and
[I/O](io-handlers.md#thumbnail-renderers) guides.
