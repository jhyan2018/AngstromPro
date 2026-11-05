# File I/O

## Tutorial: open and verify a measurement

**Goal:** load the channels you need and confirm their meaning before analysis.

**Input:** an existing supported measurement file. Typical choices are
`.sxm` topography, `.3ds` spectroscopy grids, and `.dat` point spectra.

1. In Main Workbench, click **+ New Module → Basic → Image Stack Viewer**
   for topography or spatial spectroscopy maps, or **+ New Module → Basic →
   Curve Stack Viewer** for spectra or line-scan curves. For an existing
   instance, click **Show** on its module card.
2. In that viewer, choose **File → Open…** and select the measurement file.
3. If a channel-selection dialog appears, check the required channels and
   confirm. For `.3ds`, distinguish swept **Channels** from **Experiment
   parameters**: a conductance channel contains an energy stack, whereas a
   per-pixel Z parameter produces a single spatial image.
4. If the dialog is skipped because auto-loading is enabled, check the loaded
   item names. To choose channels explicitly next time, open **File →
   Preferences…** in the Main Workbench, select the format in **Channels**,
   turn off **Auto-load defaults for this format**, and apply the change.
5. Show **View → Workspace**. Each selected channel appears as its own item.
   Single-click one item and inspect its name, source, data shape, axes, and
   units in **View → Inspector**. If Workspace and Inspector occupy the same
   dock, click their bottom tabs to switch. These panels can also float.
6. Double-click the intended item to load it into the viewer. In Image Stack
   Viewer it becomes **Primary**; in Curve Stack Viewer it starts a new plot.
7. Right-click the workspace row and choose **Set alias…** if a shorter label
   such as `topography_raw` or `conductance_map` will help identify it.

**Expected result:** the viewer displays the chosen channel and the Inspector
shows physical axes consistent with your acquisition.

| Data in the Inspector | Suitable viewer |
| --- | --- |
| `(1, rows, columns)` | Image Stack Viewer, one-layer topography |
| `(layers, rows, columns)` | Image Stack Viewer, for example energy-resolved maps |
| `(curves, points)` | Curve Stack Viewer, one or more spectra |
| `(points,)` | Curve Stack Viewer, a single spectrum |

A two-dimensional array is treated as curve-stack data, not automatically as a
single image. For generic array files, confirm the dimensionality and coordinate
metadata before interpreting the result. Use the instrument reader when it
provides the physical axes you need. A one-dimensional spectrum can be plotted
directly, but an algorithm that declares a two-dimensional curve-stack input
still requires data shaped `(curves, points)`.

**If the expected channel is absent:** inspect the raw name/source shown by the
loader and follow [channel mapping](preferences.md#tutorial-configure-a-measurement-channel).
For unmatched channels, select the correct raw channel in the resolution dialog;
do not substitute a differently measured signal merely because it is available.

**Next:** [inspect image layers](image-stack-viewer.md#tutorial-inspect-images-and-their-fourier-transforms)
or [compare spectra](curve-stack-viewer.md#tutorial-compare-and-style-spectra).

## Built-in formats

| Format | Read | Write | Purpose |
| --- | :---: | :---: | --- |
| `.uds` | Yes | Yes | Native HDF5 scientific data |
| `.scplot` | Yes | Yes | Curve Stack Viewer scene |
| `.apws` | Yes | Yes | HDF5 archive of one module workspace |
| `.npy` | Yes | Low-level API only | NumPy array |
| `.sxm` | Yes | No | Nanonis map |
| `.3ds` | Yes | No | Nanonis grid spectroscopy |
| `.dat` | Yes | No | Nanonis point spectroscopy |
| `.1fl` | Yes | No | LF dI/dV map |
| `.tfr` | Yes | No | LF topography map |
| `.mat` | Yes | No | MATLAB data |
| `.txt` | Yes | No | Whitespace-delimited numeric data |

NumPy writing is available through the low-level
`angstrompro.io.formats.npy_io.save(path, uds)` function, not through the
viewer's **File → Save…** command. That command saves UDS datasets in their
native `.uds` format. Changing the filename suffix to `.npy` does not convert
the file to NumPy format. The low-level NumPy writer stores only the numerical
array, without axes, metadata, annotations, or processing history.

In the **Main Workbench**, open **Help → Supported Formats…** for the runtime
registry. This view also includes formats supplied by installed plugins.

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
or identity. Arrays written through the low-level `.npy` writer do not store
workspace-item metadata.

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

Open **File → Preferences… → Channels** in Main Workbench or Data Browser.
Expand **Channel mappings** if collapsed, then single-click the **File format**
entry before editing its table. Use **Apply** or **Save as default** in the
Preferences dialog to commit the changes.

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

You can check **Load by default** for several channels of the same format.
They load as separate workspace items, not as merged signals.

Aliases are exact and case-sensitive, not partial searches. Configure them in
Main Workbench or Data Browser Preferences; both locations edit the same
application-wide Channel Manager. See
[Preferences](preferences.md#channel-mappings) for the full behavior table.

## Tutorial: save data and export results

**Goal:** choose the correct output for continuing analysis or presenting it.

| You need | Action | Output |
| --- | --- | --- |
| One numerical dataset with axes and history | Select its workspace row; **File → Save…** | `.uds` |
| An editable curve figure | **Scene → Save as Scene…**, then select the scene and **File → Save…** | `.scplot` |
| A collection of workspace items | **File → Save Workspace…** | `.apws` |
| Reusable curve styling without data | **Scene → Save Template…** | `.scet` |
| A displayed image | **File → Export Image…** in Image Stack Viewer | PNG, TIFF, or JPEG |
| A curve figure for presentation | **File → Export Figure…** in Curve Stack Viewer | PNG, PDF, SVG, or TIFF |
| A sequence through image layers | **File → Export Video…** in Image Stack Viewer | MP4, GIF, or AVI |

### Export the displayed image

1. In Image Stack Viewer, load the intended dataset in Primary or Reference.
   Choose its layer, Type, colour map, and colour limits.
2. Choose **File → Export Image…**.
3. In the Export Image dialog, set **Panel** to **Primary** or **Reference**, then decide whether to include
   **annotations / overlays**. This controls whether visible markers and other
   overlays are part of the exported view.
4. Set **Destination = File**, choose PNG, TIFF, or JPEG, confirm, and choose
   the output filename. Alternatively, choose **Destination = Clipboard**
   and confirm to copy the image for pasting into another application.
5. Inspect the saved image. Retain a separate `.uds` if numerical values,
   axes, and processing history must remain available.

**Expected result:** an image of the selected panel, not a numerical data
archive. Check that you exported the measurement rather than its FFT reference.

### Export an image-stack sequence

Each selected layer becomes one video frame. For example, exporting a dI/dV
stack acquired at different energies produces a sequence showing the map at
each energy; the frame rate controls playback speed, not the acquisition axis.

1. Activate the intended stack and establish the display settings.
2. Choose **File → Export Video…** and select the correct **Panel**.
3. In the Export Video dialog, choose the **Format**, **Frame rate**, and inclusive **First / Last** layer
   indices. Check the physical layer values separately; layer indices are
   not the same as bias or energy values.
4. Choose whether to include annotations/overlays and set quality where the
   chosen format provides it.
5. Confirm, choose the destination, and inspect the first and last frames of
   the saved sequence.

**Expected result:** a presentation sequence through the selected layers.
It does not replace saving the underlying stack. If MP4 or AVI export fails,
check the reported video-backend error; GIF is another available format.

For curve figures, follow
[save an editable plot and export a figure](curve-stack-viewer.md#tutorial-save-an-editable-plot-and-export-a-figure).

## Saving and exporting

Saving writes structured data through a registered format handler. Exporting
creates a presentation artifact such as an image, video, or figure. Use saving
when the result must be reloaded and processed later; use exporting for
publication or presentation.
