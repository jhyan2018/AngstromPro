# Architecture

AngstromPro uses a `src`-layout Python package. The console command calls
`angstrompro.app.main:main`, which creates Qt, obtains the user-data folder,
loads configuration and appearance resources, constructs the application
context, registers built-in modules, and opens the main workbench.

## Shared context

`AppContext` owns the managers shared by module instances:

| Resource | Responsibility |
| --- | --- |
| `ConfigManager` | Merged defaults and persisted user overrides |
| `ThemeManager` and `IconManager` | Application appearance |
| `AppSignals` | Cross-component Qt signals |
| `TaskManager` | Threaded and persistent work |
| `WorkspaceManager` | Per-module workspaces |
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
2. A module wraps it in a `WorkspaceItem` inside its workspace.
3. The user stages workspace items as process inputs.
4. `ProcessRunner` validates the schema and submits work to `TaskManager`.
5. The registry records processing history on supported results.
6. The result returns to the source module's workspace.

See [Runtime data and workspaces](workspaces.md) for the platform-level payload
contract, composite data types, transfer behavior, and generic inspection.

GUI components should not perform expensive scientific work directly on the
Qt thread. Express reusable operations as registered processes and submit them
through the task infrastructure.
