# I/O handlers

The central I/O dispatcher maps data `type_id` values to readers, writers, and
user-facing `FormatInfo` records. Modern native files are detected as HDF5 and
dispatched using the root type metadata; raw instrument formats are dispatched
by extension.

## Register a typed format

```python
from angstrompro.io.angstrom_io import register_io


def load_example(path):
    ...


def save_example(path, data):
    ...


register_io(
    "example_data",
    load_example,
    save_example,
    extension=".example",
    display_name="Example data",
    description="Example scientific data.",
)
```

A reader accepts a `pathlib.Path` and returns `WorkspaceData`. A writer accepts
the destination path and compatible data. Set `writable=False` for a read-only
format; its writer may raise `NotImplementedError`.

The payload-only `load(path)` and `save(path, data)` APIs remain unchanged.
The module's single-item File menu uses `load_item(path)` and
`save_item(path, workspace_item)` instead. For a registered writable HDF5
format, those functions place a separately versioned `workspace_item` group
at the file root containing the alias, item ID, and serialized annotations.
The payload's own format version and extension remain unchanged. This shared
step also covers plugin HDF5 formats registered with `register_io`; plugin
readers and writers need not handle the group themselves. An older file
without the group loads with default item fields. Non-HDF5 formats such as
`.npy` do not support this item-metadata step.

## Make a payload workspace-archive compatible

The standalone reader and writer above operate on complete files. To embed the
same payload in **Save Workspace…**, also provide reader and writer functions
that operate on an already-open HDF5 group:

```python
def read_example_group(group):
    return ExampleData(value=int(group.attrs["value"]))


def write_example_group(group, data):
    group.attrs["value"] = data.value


register_io(
    "example_data",
    load_example,
    save_example,
    extension=".example",
    display_name="Example data",
    description="Example scientific data.",
    workspace_reader=read_example_group,
    workspace_writer=write_example_group,
    workspace_provider="example_plugin",
    workspace_version=1,
)
```

The plugin must import this registration module during startup. AngstromPro
then saves the payload alongside built-in workspace types. Archives record the
provider and codec version, but never import a class named by the archive and
never pickle a payload. When an archive is opened without the required plugin,
that payload is skipped and included in the warning; all supported payloads are
still loaded.

Use a stable, unique `type_id` and provider name. Increment
`workspace_version` when the embedded group format changes, and keep the group
reader compatible with older versions or provide an explicit migration path.

## Register a raw extension loader

Plugins that only need to load a raw format can register a direct extension
loader:

```python
from angstrompro.io.angstrom_io import register_ext_loader

register_ext_loader(".example", load_example)
```

Extensions are normalized to lowercase. Raw loaders appear in the runtime
Supported Formats dialog as plugin-provided, read-only formats.

## Multichannel instruments

Only formats that contain multiple named channels should integrate with
`ChannelManager`, so loading and thumbnail rendering use the same aliases and
default selections. Single-channel formats should return their data directly.
Keep the low-level parser independent of GUI dialogs.

Channel aliases are matched exactly and in configured order. A channel's
`load_by_default` flag has two consumers: it preselects rows in the interactive
channel picker and selects Data Browser thumbnail channels. The enclosing
format's `auto_load` flag is independent: it suppresses the normal picker while
still invoking unmatched-channel resolution when a default alias cannot be
resolved. Do not use `auto_load` to decide which thumbnails to render.

The `.3ds` reader uses a typed `GridField` selection: `source="channel"`
addresses a full sweep spectrum, while `source="experiment_parameter"`
addresses one scalar in the per-pixel parameter block. Its zero-based
experiment-parameter offset is the number of listed fixed parameters plus the
index in `Experiment parameters`. The reader verifies the fixed-plus-experiment
count against `# Parameters (4 byte)` when fixed names are present; otherwise
it infers the fixed count from that total. Channel Manager
records a `.3ds` mapping's source, and both the interactive picker and the
headless Data Browser renderer pass this typed selection to the reader.
For a short binary payload, only whole pixel records count as acquired data.
The reader derives the sweep axis from a completed record before applying the
display-axis flip, discards a partial trailing record, and zero-fills wholly
missing pixels so interrupted grids remain plottable. Completion counts belong
in the UDS metadata so callers can distinguish partial acquisition from real
zero-valued measurements.

## Persistence rules

- Preserve axes, metadata, annotations, and processing records when the format
  supports them.
- Reject unsupported data explicitly rather than silently dropping fields.
- Use atomic or recoverable writes where practical.
- Keep legacy readers separate from current writers.
- Add the import to the plugin or built-in format package so registration runs.
