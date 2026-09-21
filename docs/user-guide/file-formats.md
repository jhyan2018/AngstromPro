# File I/O

## Built-in formats

| Format | Read | Write | Purpose |
| --- | :---: | :---: | --- |
| `.uds` | Yes | Yes | Native HDF5 scientific data |
| `.scplot` | Yes | Yes | Curve Stack Viewer scene |
| `.apws` | Yes | Yes | HDF5 archive of one module workspace |
| `.npy` | Yes | Yes | NumPy array |
| `.sxm` | Yes | No | Nanonis map |
| `.3ds` | Yes | No | Nanonis grid spectroscopy |
| `.dat` | Yes | No | Nanonis point spectroscopy |
| `.1fl` | Yes | No | LF dI/dV map |
| `.tfr` | Yes | No | LF topography map |
| `.mat` | Yes | No | MATLAB data |
| `.txt` | Yes | No | Whitespace-delimited numeric data |

Open **Help → Supported Formats…** for the runtime registry. This view also
includes formats supplied by installed plugins.

## Native data

Current `.uds` files use HDF5 and retain AngstromPro data, axes, metadata,
annotations, and processing history. Legacy binary `.uds` files are imported
read-only; save the imported result as `.uds` to upgrade it to the current
format.

When saved from **File → Save…**, a native HDF5 item file also retains its
workspace alias, item identity, and named annotations. This applies to
installed plugin formats that write HDF5 files, without changing their usual
extensions or payload versions. Older files without workspace-item metadata
still open; their alias and annotations start empty, and they receive a new
item identity. Reopening an item whose name or identity is already in the
workspace keeps the existing item and gives the imported one a distinct name
or identity. Plain `.npy` exports do not store workspace-item metadata.

`.scplot` is also HDF5-based and stores complete `ScenePlot` data. Style-only
`.scet` templates are created and managed by the Curve Stack Viewer and can be
selected by both the Curve Stack Viewer and Data Browser when rendering fresh
raw UDS data. They contain no scientific dataset and are not general workspace
data files.

Nanonis `.3ds` headers list swept **Channels** separately from per-pixel
**Experiment parameters**. The file-open picker shows the source of each
candidate. A selected experiment parameter, such as **Z (m)** or
**Scan:Z (m)**, becomes a one-layer spatial UDS image; it does not acquire the
bias-sweep axis. The loader locates it after the fixed parameters in each
pixel's parameter block and checks that the listed fixed and experiment
parameters agree with **# Parameters (4 byte)** before extraction. If fixed
parameter names are absent, their count is inferred from that total and the
experiment-parameter list.

An interrupted `.3ds` grid remains loadable when it contains at least one
complete pixel record. AngstromPro derives the sweep axis from completed data,
keeps unrecorded spatial pixels at zero so the partial map can still be plotted,
and records the completed and expected pixel counts in the UDS information.
For a header-only acquisition stopped before its first pixel, the reader can
instead reconstruct a linear axis from textual **Sweep Start** and **Sweep
End** header settings. Any incomplete trailing pixel record is discarded rather
than interpreted as measurement data. The missing spectra were never stored in
the source file and cannot be recovered by the loader.

`.apws` is an HDF5 workspace archive. It stores all supported items from the
current module workspace in their displayed order, together with item names,
identities, aliases, and annotations. Core UDS and ScenePlot
payloads are supported, and installed plugins can register their own archive
payloads. Unsupported payload types are listed before saving and are skipped
after confirmation. When opening an archive, payloads belonging to unavailable
plugins are skipped with a warning while the remaining supported items load.

## Channel mappings for multichannel formats

Some instrument formats contain multiple named channels. For those formats,
channel mappings associate varying instrument labels with stable AngstromPro
channel roles. The built-in `.3ds`, `.sxm`, and `.dat` loaders use these
mappings; single-channel formats do not require them.

Each file format has two independent levels of configuration:

- A channel row marked **Load by default** is preselected in the normal
  file-open dialog and is rendered by the Data Browser when an exact alias
  matches.
- **Auto-load defaults for this format** skips the normal selection dialog and
  loads the matched default rows immediately. If a default alias does not
  match, an **Unmatched channels** dialog still appears.

Aliases are exact and case-sensitive, not partial searches. Configure them in
Main Workbench or Data Browser Preferences; both locations edit the same
application-wide Channel Manager. See
[Preferences](preferences.md#channel-mappings) for the full behavior table.

## Saving and exporting

Saving writes structured data through a registered format handler. Exporting
creates a presentation artifact such as an image, video, or figure. Use saving
when the result must be reloaded and processed later; use exporting for
publication or presentation.
