# Runtime data and workspaces

The workspace subsystem is AngstromPro's common runtime data bus. It is
designed to hold more than the built-in UDS array type, allowing new modules and
plugins to introduce new payloads without creating parallel storage, transfer,
or inspection mechanisms.

## Object model

```text
WorkspaceManager
└── Workspace                         one per live module instance
    └── WorkspaceItem                 runtime identity and annotations
        └── payload: WorkspaceData     arbitrary extensible data type
```

`WorkspaceManager` registers live workspaces and forwards lifecycle signals.
`Workspace` owns an ordered collection of items and emits add, remove, rename,
and change signals. `WorkspaceItem` wraps a payload with an item ID, optional
alias, source path, and named annotations.

## WorkspaceData contract

A runtime payload subclasses `WorkspaceData` and defines:

- A unique, stable `type_id`
- `display_type()` for a human-readable name
- `summary()` for compact facts
- `inspect_fields()` for structured inspection

The base contract deliberately contains no file I/O. Persistence is registered
separately with the I/O subsystem. A useful runtime type therefore does not
need to be directly saveable, although production types should normally offer
a persistence or export path when their state is valuable.

Processes declare payload compatibility through `InputSpec.type_id` and
modules can declare accepted types. This keeps the workspace generic while
allowing each consumer to reject unsupported data cleanly.

## Elementary and composite payloads

`UdsDataStru` is an elementary array payload: it owns numerical data, axes,
metadata, landmarks, and processing history. Runtime annotations belong to the
surrounding `WorkspaceItem`.

Runtime types may also compose other `WorkspaceData` objects. `ScenePlot` is
the main built-in example. It owns a figure hierarchy of axes and artists;
artist specifications may contain UDS datasets, while error-bar styles may
refer to additional UDS data. The scene remains one workspace payload even
though it wraps several elementary datasets and presentation settings.

This composition model is preferred when a module needs to preserve a coherent
domain object rather than expose every internal dataset as an unrelated
workspace row.

## Adding and transferring items

Add a payload through the owning workspace:

```python
item = self.workspace.add_item(payload=result, source_path=source_path)
```

The workspace resolves duplicate display names and returns the new
`WorkspaceItem`. Cross-module sending creates a destination item through
`WorkspaceManager`. The application preference determines whether the source
row is then removed, producing move-like behavior, or retained.

Treat workspace payloads as live runtime objects. Consumers that require
independent mutation should make an explicit copy rather than assuming that a
send operation creates an independent payload.

## Generic inspection

`WorkspaceItemInspector` renders the list returned by
`WorkspaceData.inspect_fields()`. Supported node kinds are:

```text
value   label and printable value
array   NumPy array, with optional children
group   nested group of inspection nodes
axis    group associated with an editable scientific Axis
```

The base implementation reflects public attributes. Concrete types should
override it to provide a stable, curated hierarchy, especially for composite
objects. `UdsDataStru` exposes data, axes, metadata, and processing history;
`ScenePlot` exposes its figure, axes, and artist hierarchy.

The Inspector can edit array contents and axis semantic types. After an
in-place change, the owning workspace should emit `item_changed` when other
views need to refresh.
