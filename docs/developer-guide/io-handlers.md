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

## Persistence rules

- Preserve axes, metadata, annotations, and processing records when the format
  supports them.
- Reject unsupported data explicitly rather than silently dropping fields.
- Use atomic or recoverable writes where practical.
- Keep legacy readers separate from current writers.
- Add the import to the plugin or built-in format package so registration runs.
