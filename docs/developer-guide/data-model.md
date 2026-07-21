# Data model

All payloads placed in a workspace derive from `WorkspaceData`. The base class
defines type, display, summary, and inspection contracts; concrete payloads own
their domain-specific metadata and content. `WorkspaceItem` supplies runtime
identity, source information, and annotations around the payload.

For the complete container hierarchy and extension contract, see
[Runtime data and workspaces](workspaces.md).

## Scientific arrays

`UdsDataStru` is the primary scientific-data container. It combines a NumPy
array with one `Axis` per array dimension. Axes carry physical coordinates,
units, labels, and semantic axis types where known.

Dimensional conventions used by the current viewers are:

- `ndim=2`: curve stacks for the Curve Stack Viewer
- `ndim=3`: image stacks for the Image Stack Viewer

These names describe the visualised signal rather than the total number of
physical coordinates. Processes should declare exact dimensional requirements
with `InputSpec.ndim` and may provide axis-type hints.

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
specifications can wrap `UdsDataStru` instances and other elementary plot data.
It uses the `scene_plot` type ID, and `.scplot` persistence is handled through
the normal I/O registry.

## Workspace ownership

Each live module has its own workspace. Sending an item coordinates a transfer
between module workspaces; algorithms should operate on the payload rather than
on GUI widgets.

## Mutation

Process functions should return a new data object and avoid mutating their
inputs. The process registry can then append a reproducible processing record
to the returned result without changing the source dataset.
