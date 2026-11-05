# I/O handlers

The central I/O dispatcher maps data `type_id` values to readers, writers, and
user-facing `FormatInfo` records. Modern native files are detected as HDF5 and
dispatched using the root type metadata; raw instrument formats are dispatched
by extension.

## Reading, writing, and previewing are separate responsibilities

On-disk files describe acquisition or storage formats; `WorkspaceData` objects
describe data used inside the application. A reader should convert file-specific
arrays, coordinates, and metadata into that runtime representation. Modules
and algorithms then use the resulting payload without parsing the instrument
header again. A multichannel reader may return a list of payloads so that
independent channels remain separate workspace items.

The current dispatcher first detects HDF5 content and reads its root `type_id`
to select a typed reader. Non-HDF5 input uses the built-in raw-format dispatch
or a plugin extension loader. Writing selects a handler using the payload's
`type_id`; changing a filename suffix does not convert the payload to another
type or reconstruct the original acquisition format.

For a new instrument format that can be represented by UDS, start with
`examples/example_plugin/src/angstrompro_example/io.py`. Its `.apdemo` loader
returns normal UDS image-stack data, so existing viewers, processes, and UDS
thumbnail renderers can be reused. A new payload type needs its own consumers
and persistence support only when the existing data model is insufficient.

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

The functions above are placeholders for the format implementation. For a
native HDF5 format, the writer must store the registered `type_id` as a root
attribute so `load()` can dispatch to its reader. Keep the format version,
array contents, axes, metadata, and other required state in an explicitly
documented schema. `register_io()` connects those functions to the application;
it does not generate a serializer. Use `register_ext_loader()` below for a raw
non-HDF5 format instead of expecting a declared native extension to parse it.

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
same payload in **File → Save Workspace…**, also provide reader and writer functions
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

**Current Data Browser limitation:** its watched-format list is built from
`registered_formats()` and does not yet include entries registered only with
`register_ext_loader()`. Such a loader works through **File → Open…**, but
its raw extension is not automatically available in the gallery. For the
`.apdemo` example, open the file in a viewer and save the loaded UDS item as
`.uds` if you want to browse it by thumbnail. The resulting UDS payload already
has a suitable renderer; registering another renderer does not change this
format-list limitation.

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

Adding a raw extension loader alone does not automatically create a new
Channel Manager section or an interactive channel picker. The built-in
multichannel formats have coordinated interactive and headless loading paths.
An additional multichannel format needs corresponding integration; keep
selection separate from parsing so background thumbnail jobs never open a
dialog or modify learned aliases.

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
zero-valued measurements. If no complete record exists, a linear sweep may be
reconstructed from unambiguous textual header keys such as
`Bias Spectroscopy>Sweep Start (V)` and `Sweep End (V)`; record this fallback as
`sweep_axis_source="header_parameters"`.

## Thumbnail renderers

A renderer converts a loaded payload into a preview, not into processed
scientific data. Renderers are registered by `(type_id, ndim)`, independently
of file extensions, through
`angstrompro.core.data.thumbnail_registry.register_thumbnail_renderer`.
The registry tries an exact dimensional match first, then `(type_id, None)`
for a dimension-independent renderer. Several readers returning UDS therefore
share the built-in UDS renderers.

To support a new payload:

1. Implement a callback with the signature
   `render(payload, *, rcparams_delta, options, figsize)` that returns a
   `matplotlib.figure.Figure` suitable for the Agg backend. Do not create Qt
   widgets, require a viewer window, or modify the payload while rendering.
2. Register it during plugin import. For the collection in the
   [payload example](workspaces.md#adding-a-payload-type), call
   `register_thumbnail_renderer("example.dataset_collection", None, render)`
   after defining or importing your rendering callback.
3. Accept the supplied figure size and rendering options; keep preview styling
   separate from the stored scientific data. The Data Browser caller writes
   the returned figure to its PNG cache.
4. Ensure the payload also has a readable file handler and its format appears
   in Data Browser's watched-format list. Note the raw-extension limitation
   above. Enable the format in the browser preferences and re-render an
   existing cached card after changing the renderer.

Use `src/angstrompro/gui/modules/data_browser/thumbnail_renderers.py` as a
reference for the current callback implementations and supported options.
The supplied example plugin reuses UDS preview support; it does not contain a
custom renderer. Without a suitable renderer, a readable payload can have an
icon-only card rather than a scientific preview. Missing preview support does
not by itself make the file unreadable.

## Persistence rules

- Preserve axes, metadata, annotations, and processing records when the format
  supports them.
- Reject unsupported data explicitly rather than silently dropping fields.
- Use atomic or recoverable writes where practical.
- Keep legacy readers separate from current writers.
- Add the import to the plugin or built-in format package so registration runs.
