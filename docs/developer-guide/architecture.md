# Architecture

Working examples are provided in `AngstromPro/examples/`. The
[example plugin](../../examples/example_plugin/README.md) connects a GUI module,
process, simulation, and file loader through the same interfaces used by
built-in components. Use it alongside this guide; an extension does not have
to implement all of these components.

The design described in Section 2 and Figures 1–4 of the accompanying
[software paper](https://arxiv.org/abs/2604.18962v2) separates data management,
visualisation, scientific processing, and
on-disk storage. This guide maps those concepts to the current implementation.

## Separation of responsibilities

A module is an independent interaction context, not the owner of a private
algorithm library. Its central widget defines how users view or manipulate
data; its Workspace provides the common item-management interface. Multiple
instances of the same module type can coexist with independent display state
and process inputs. An optional shared workspace shares data, not those
module-local controls.

Scientific algorithms operate on data payloads rather than viewer widgets or
instrument files. They are registered once and can be exposed in any module
whose declared input requirements are compatible. File readers translate
instrument-specific structures into these payloads before visualisation or
processing; writers handle persistence separately.

Keep three kinds of state distinct: the selected Workspace row, the datasets
currently displayed, and the items staged in `process_inputs`. For example,
Curve Stack Viewer's **Add to plot** changes the displayed set without changing
the processing inputs. Image Stack Viewer deliberately maps its Primary and
Reference panels to those inputs, but that mapping is not a general rule for
new modules.

## Startup

AngstromPro uses a `src`-layout Python package. The console command calls
`angstrompro.app.main:main`, which creates Qt, obtains the user-data folder,
loads configuration and appearance resources, constructs the application
context, registers built-in modules, and opens the main workbench.

## Shared context

`AppContext` owns the managers shared by module instances:

| Resource | Responsibility |
| --- | --- |
| `ConfigManager` | Merged defaults and persisted user overrides |
| `ThemeManager` and `IconManager` | Bundled application theme, fonts, palette, and icons |
| `AppSignals` | Cross-component Qt signals |
| [`TaskManager`](tasks.md) | Threaded and persistent work |
| `WorkspaceManager` | Private and shared workspaces, attachments, and transfers |
| `AModuleManager` | Module registration and instances |
| `ProcessRegistry` | Registered processes and simulations |
| `ParamHistoryManager` | Previously used process parameters |

File loading and saving form the broader **I/O subsystem** in
`angstrompro.io`. Its central registry dispatches readers and writers. The
context-owned `ChannelManager` is an optional supporting service for formats
that contain multiple named channels; single-channel formats do not use it.

Plugins load before `ProcessRegistry` is constructed. This ordering lets plugin
imports run registration decorators before the registry snapshots pending
entries.

`ThemeManager` applies AngstromPro's owned light or dark palette and stylesheet
on top of Qt's Fusion style. It replaces the complete application stylesheet
when preferences change, preventing rules from accumulating. Component-specific
styles should use stable Qt object names so they can be maintained alongside
the global compact control rules. The application does not depend on a
third-party Qt theme package.

Application typography uses shared semantic roles: body, secondary, heading,
section, notification, hint, and monospace. New widgets should use
`set_typography_role` rather than introducing local font families, fixed sizes,
or muted-text colors. Scientific plot annotations and Matplotlib figure styles
remain separate because they describe exported data graphics rather than the
desktop interface.

## Package responsibilities

```text
angstrompro.app             startup, paths, shared context
angstrompro.core.configs    defaults, validation, persistence
angstrompro.core.data       workspace data and annotations
angstrompro.core.modules    module contracts and manager
angstrompro.core.processes  schemas, registry, runner, history
angstrompro.core.tasks      task requests, handles, and executors
angstrompro.core.workspaces workspace ownership and items
angstrompro.gui             modules, dialogs, widgets, appearance
angstrompro.io              central I/O registry and built-in formats
angstrompro.algorithms      built-in registered processes
```

## Runtime flow

1. A loader or simulation creates an extensible `WorkspaceData` payload.
2. A module adds it as a `WorkspaceItem` to its current output workspace.
3. The user stages workspace items as process inputs; the GUI checks the
   required input count, types, and dimensions before opening the process dialog.
4. `ProcessRunner` maps the ordered items to named payload inputs, resolves
   annotations from the primary item, merges parameter defaults, and submits
   the operation through the registry to `TaskManager`.
5. The worker calls the algorithm without accessing GUI widgets. The registry
   records processing history on results that support it.
6. The module's result handler adds the returned payloads to its current output
   workspace: private by default, or shared while attached.

The file-preview path uses the same loaded payloads but sends them to a
headless thumbnail renderer instead of a viewer. A cached thumbnail is only a
presentation image; Data Browser reloads the scientific data when sending a
file to a module. See [I/O handlers](io-handlers.md) for the reading, writing,
and preview boundaries.

See [Runtime data and workspaces](workspaces.md) for the platform-level payload
contract, composite data types, transfer behavior, and generic inspection.

GUI components should not perform expensive scientific work directly on the
Qt thread. Express reusable operations as registered processes and submit them
through the [task infrastructure](tasks.md).
