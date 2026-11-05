# Data model

All payloads placed in a workspace derive from `WorkspaceData`. The base class
defines type, display, summary, and inspection contracts; concrete payloads own
their domain-specific metadata and content. `WorkspaceItem` supplies runtime
identity, an alias, and annotations around the payload. UDS source information
is kept in the payload's `info` dictionary.

For the complete container hierarchy and extension contract, see
[Runtime data and workspaces](workspaces.md).

## Scientific arrays

`UdsDataStru` is the primary scientific-data container. It combines a NumPy
array with one `Axis` per array dimension. Axes carry physical coordinates,
units, labels, and semantic axis types where known.

Dimensional conventions used by the current viewers are:

- `ndim=1`: a single curve, accepted directly by the Curve Stack Viewer
- `ndim=2`: curve stacks shaped `(curves, points)` for the Curve Stack Viewer
- `ndim=3`: image stacks shaped `(layers, rows, columns)` for the Image Stack Viewer

These names describe the visualised signal rather than the total number of
physical coordinates. Display support does not imply process compatibility:
plotting a one-dimensional array does not convert its stored shape to
`(1, points)`. Processes should declare exact dimensional requirements with
`InputSpec.ndim` and may provide axis-type hints.

## Coordinates, channels, and metadata

UDS means Uniform Data Structure. One UDS object represents one numerical
dataset with a coherent set of physical coordinates; an acquisition file can
produce several objects, one for each independently usable channel. Do not
combine different channels merely because they were acquired in one file.

Before combining datasets or doing pointwise arithmetic, compare the axes as
well as the array shapes: their values, ordering, labels, and units must be
consistent. Two equally sized images can cover different spatial grids, and
two equally long spectra can have different bias values. Keep such datasets
separate, or perform an explicit, scientifically justified alignment or
resampling step. The generic workspace and process schema do not automatically
align physical coordinates.

When constructing a result, preserve axes for unchanged dimensions and update
them for cropped, transposed, resampled, or transformed dimensions. The
`gaussian_stack()` function in `examples/example_plugin/src/angstrompro_example/processes.py`
shows how the order of the Layer, Y, and X axes follows the array dimensions.
The example loader in `io.py` demonstrates the same convention for imported data.

Use `info` for additional experimental metadata, not as a replacement for
physical axes or named annotations. For an imported UDS object, the
`file_source(path)` helper supplies a canonical source path. Processing history
and source propagation are handled by the registered execution path; a direct
call to an algorithm function bypasses that bookkeeping.

## Annotations

Annotations attach structured selections to data without modifying the array.
Built-in types include point sets, regions, and lines. Named roles such as
`bragg_peaks`, `interest_region`, and `line_cut` allow a `ProcessSchema` to
request the correct selection.

Do not encode annotations as undocumented metadata keys. Add or use a typed
annotation class and declare it through `AnnotationSpec`.

## Scenes

`ScenePlot` represents an editable curve-plot scene, including artists and
style state. It is a composite `WorkspaceData` payload: its artist
specifications may contain one or more UDS datasets (`UdsDataStru` instances)
and other elementary plot data.
It uses the `scene_plot` type ID, and `.scplot` persistence is handled through
the normal I/O registry.

Prefer composition when extra structure belongs to a complete analysis object:
retain its UDS datasets with their own axes and store the additional
relationships or presentation settings in a separate `WorkspaceData` type.
Do not enlarge every UDS object with fields needed by only one specialised
module. See [Adding a payload type](workspaces.md#adding-a-payload-type) for
the runtime contract; saving and preview rendering are separate extensions.

## Workspace ownership

Each live module has its own workspace. Sending an item coordinates a transfer
between module workspaces; algorithms should operate on the payload rather than
on GUI widgets.

## Mutation

Process functions should return a new data object and avoid mutating their
inputs. The process registry can then append a reproducible processing record
to the returned result without changing the source dataset.
