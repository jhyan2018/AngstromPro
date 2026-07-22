# Plugins

Plugins extend AngstromPro by importing code that registers processes, modules,
or file-format handlers. They load before the process registry is constructed.

A plugin may also define new `WorkspaceData` payload types. Doing so lets its
modules participate in the standard workspace, sending, compatibility, and
Inspector infrastructure. See [Runtime data and workspaces](workspaces.md).

## Local source plugin

During development, add an entry under **Preferences → Plugins** containing:

- The absolute path to the plugin's `src/` directory
- Its importable top-level module name

On the next launch, AngstromPro adds the path to `sys.path` and imports the
module. The module's imports must trigger every required registration.

When testing from Spyder, closing the Main Workbench only hides the hosted
AngstromPro session so it can be reopened without rebuilding Qt. Restart the
Spyder kernel after changing plugin source; reopening the existing session does
not reload already imported plugin modules or replace their live widget
classes. A standalone AngstromPro process can instead be closed and launched
again normally.

## Installed plugin

An installable package should expose an entry point in `pyproject.toml`:

```toml
[project.entry-points."angstrompro.plugins"]
example = "angstrompro_example"
```

The referenced object or module is loaded at startup. Keep its top-level import
focused on registration; avoid opening windows or starting independent event
loops during import.

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

## Configuration

Call `context.get_plugin_config("example")` for isolated settings. Namespaced
GUI module IDs such as `example.viewer` automatically select the corresponding
plugin configuration. Files are stored under
`<UserDataFolder>/config/plugins/`.

Register defaults before reading configuration, validate user values, and
store only settings owned by the plugin. Do not edit the core `config.json`
directly.

## Failure handling

A failing plugin import is logged and startup continues. Test imports in a
clean environment and inspect `angstrompro.log` when registrations do not
appear. Duplicate loading by path and entry point is skipped when AngstromPro
can identify the same top-level module.

Plugin authors must review license compatibility for AngstromPro, the plugin,
and all dependencies before distribution.

## Complete example

The repository includes an installable
[example plugin](../../examples/example_plugin/README.md) that registers a GUI
module, process, simulation, and raw file loader. It uses synthetic data and
executes its operations through the normal task-backed process path. Its README
also gives the exact **Preferences → Plugins** values for loading the example
directly from its `src/` folder during development.
