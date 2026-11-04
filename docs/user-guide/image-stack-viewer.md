# Image Stack Viewer

The Image Stack Viewer is intended for three-dimensional data such as
energy-resolved maps. It presents the **Primary** image beside a persistent
right-hand area that switches between **Reference Image** and **Curve Preview**
without clearing either view. It also maintains a workspace for source data
and results.

Two-dimensional topographic images and single-energy dI/dV maps are treated
as single-layer stacks: three-dimensional data with a stack dimension of size
one, normally shaped `(1, rows, columns)`.

## Locate the image controls

Open this module from Main Workbench with **+ New Module → Basic → Image Stack
Viewer**, or click **Show** on its existing card. Open **View → Workspace** to
see data items and **View → Inspector** to inspect a single-clicked item.
If these docks overlap, switch using the **Workspace** / **Inspector** tabs.

The **Primary** panel and the right-hand **Reference Image** tab each contain
their own **Select Variable** button, **Name**, **Type**, **Layer**, **Palette**,
and **Picked Points** controls. Single-click a Workspace item, then click
**Select Variable** in the panel you want to assign; double-clicking a
Workspace item activates Primary. A panel's **Type** dropdown and **Layer**
spinbox affect that panel.

Right-click the actual image to add a picked point. To remove one, single-click
its row in that panel's **Picked Points** list and click **Remove Point**.
Drag an existing marker with the left mouse button to reposition it.
The **Points** menu stores these visual selections as process annotations;
moving a marker afterward requires repeating the appropriate **Points → Set…**
action. Right-clicking a Workspace row instead opens its item context menu.

To the right of each canvas, **Picked Points** has a colour dropdown for
markers and a display-mode dropdown with **Points**, **Lines**, **Circle**,
and **Region**. With two points selected, these show the points alone, a
connecting line, a circle (first point at its centre), or a rectangular region.
The list below shows point coordinates; select a row before clicking
**Remove Point**. Selecting a display mode does not assign a process annotation.

Click **Curve Preview** in the right-hand tab area to access its **Preview**
and **X axis** dropdowns and sampling controls. Click **Reference Image** to
return to the second image. Synchronisation controls are under this viewer's
**File → Preferences… → Sync**; colour editors are under **View →
RT-ColorMap (Primary)** and **View → RT-ColorMap (Reference)**.

## Tutorial: inspect images and their Fourier transforms

**Goal:** inspect a measurement in real and reciprocal space before processing.

**Input:** a topographic image or energy-resolved image stack already
[loaded into the workspace](file-formats.md#tutorial-open-and-verify-a-measurement).

1. Double-click the measurement item. Check the **Name** shown under
   **Primary**; this is also the first process input.
2. For input not already identified as FFT data, wait for the automatic FFT.
   A name ending in `_fft` is recognised as FFT data; internal FFT metadata
   also identifies transformed data. Open **Reference Image**
   on the right and check the reference name. The computed `_fft` item is
   also added to the workspace.
3. Use **Layer** under Primary to move through an image stack. Read the adjacent
   physical layer value and unit, when available. A single-layer topography
   has only one image; its layer axis is not an energy scan.
4. Use **Type = Real** for signed real-space measurements and **Type = Abs**
   to view FFT magnitude. **Angle** shows phase; **Imag** shows the imaginary
   component. Displaying `Abs` on signed data hides its sign.
5. Adjust the colour-range controls to reveal the features of interest.
   Choose **View → RT-ColorMap (Primary)** or **RT-ColorMap (Reference)** to
   edit the palette. These settings change the display, not the stored array.
6. If you want both panels to follow the same layer, open **File →
   Preferences… → Sync**, enable **Sync layer**, and choose **Apply**.
   Inspect both layer labels after the change.
7. To calculate an FFT with explicit settings, add **FFT 2D** to the Process
   menu, activate the real-space item, and run it with your chosen **Window**
   and **Normalize** settings. Select the new result explicitly for comparison.

**Expected result:** Primary shows your measurement and Reference shows its FFT,
with names, layer values, and display types that you have checked.

The automatic FFT is a convenience view and can reuse an existing associated
result. It is not a substitute for explicitly recomputing an FFT after editing
array values or when changing transform parameters. Reopening a real-space item
can replace a manually selected reference with its automatic FFT.

**If a panel looks blank or saturated:** check the item name, layer, Type, and
colour range before concluding that the data are empty. Use the Inspector to
check the actual array.

## Tutorial: compare raw and processed images

**Goal:** compare two datasets without confusing the second image with an FFT.

1. Keep both raw and processed items accessible in the viewer's workspace.
2. Double-click the processed item to put it in **Primary**. Wait for its
   automatic FFT to finish.
3. Single-click the raw item in the workspace. In the **Reference Image**
   panel, click **Select Variable**. Confirm the reference name is the raw
   measurement rather than the FFT.
4. Select corresponding physical layers in both panels. Enable **Sync layer**
   only when matching layer indices represent corresponding measurements.
5. Use the same **Type**, colormap, and numerical colour limits for a fair
   amplitude comparison. Independently auto-scaled images can conceal
   differences in signal range.
6. For datasets on matching grids, **File → Preferences… → Sync → Sync FOV
   zoom** can help
   inspect the same region. Keep **Sync pick points** off when independent
   landmark positions must be selected.

**Expected result:** Primary and Reference show the intended processed/raw
pair. Check **Active Processing Slots** as well: loading Reference also changes the
second staged input for two-input operations.

## Tutorial: preview point spectra

**Goal:** inspect how a spectral signal varies with position in a spectroscopy
map without immediately generating new workspace data.

**Input:** a stack whose first axis is the measured bias or energy. A one-layer
topography cannot provide a spectrum.

1. Activate the spectroscopy channel in **Primary** and choose **Type = Real**
   for a real-valued signal.
2. Right-click the image at one or more positions. The numbered markers and
   **Picked Points** list identify those spatial positions.
3. Select the **Curve Preview** tab on the right and choose **Preview =
   Point spectra**.
4. Compare the curves using the layer/energy axis. Drag a marker to a different
   position to update its curve.
5. To remove a position, select its entry in **Picked Points** and choose
   **Remove Point**.

**Expected result:** one temporary curve per picked position, evaluated through
all layers. Switching the Primary **Type** changes the represented signal in
the preview.

The preview does not create a workspace result or a processing-history entry.
For a persistent sequence of spectra along a path, use the line-cut tutorial
with **distance_vs_layer**. For a spatial mean, use
[Average Spectrum 2D](curve-stack-viewer.md#tutorial-plot-an-average-spectrum-with-error-bars).

## Tutorial: create a line cut

**Goal:** extract a spatial profile or spectra along a line and keep the result
for plotting and saving.

**Input:** a real-valued image stack in Primary. Add **Line Cut 2D** to the
Process menu using the [menu tutorial](processes.md#tutorial-configure-a-process-menu).

1. Remove previous entries from the Primary **Picked Points** list with
   **Remove Point**. Right-click the start and end of your path, in that order.
   These become points 0 and 1.
2. For a quick check, open **Curve Preview**, choose **Line cut**, and select
   **X axis = Distance** for spatial profiles or **Layer / energy** for spectra
   along the path. Keep the line and any averaging width inside the image.
3. Choose **Points → Cut → Set Line Cut from Primary**. Expand the source
   workspace item and confirm that `line_cut` appears. This saves a snapshot
   of the endpoints as a process annotation.
4. Run **Line Cut 2D**. Confirm the source input, then set:

    - **Orientation = layer_vs_distance** for one distance profile per layer;
    - **Orientation = distance_vs_layer** for one spectrum per sampled position;
    - **Sampling method = interpolated**, **Interpolation order = 1**,
      **Line width (px) = 1**, and **Number of points (0=auto) = 0** for an
      initial, unaveraged extraction.

5. Click **Run**. The resulting `_lc` item is curve-stack data; it cannot be
   displayed as an image stack in this viewer.
6. Open a **Curve Stack Viewer** from Main Workbench. Single-click the
   `_lc` row in Workspace, click the **Send…** button below the list, and select that viewer. If both modules use
   the same shared workspace, no send is necessary.
7. Double-click the result in Curve Stack Viewer. Check the X-axis label:
   distance for `layer_vs_distance`, or the source layer/energy axis for
   `distance_vs_layer`. Save it with **File → Save…**.

**Expected result:** a persistent curve stack with the chosen orientation and
a process-history record. One-layer topography produces one spatial profile
when `layer_vs_distance` is selected.

**Checks:** if **Run** is disabled, verify the saved `line_cut` annotation
on the actual primary item. If you drag the endpoints, choose **Points → Cut → Set Line Cut
from Primary** again. Preview settings are not automatically copied into the
process dialog. The preview follows the display Type, whereas the registered
process samples the stored data; use real-valued data for this first workflow.

For a circular profile, pick point 0 at the centre and point 1 on the circle,
choose **Points → Cut → Set Circle Cut from Primary**, and run **Circle Cut
2D**. Its orientations are `layer_vs_theta` (angle on X) and
`theta_vs_layer` (layer/energy on X). Keep the circle and its radial averaging
width within the measured field of view.

## Load data

Send a compatible item from the Planewave Synthesiser, Data Browser, or another module. Workspace items
can then be assigned to the viewer's input roles. The viewer validates that
image-stack data has three dimensions.

The layer control moves through the stack and displays the corresponding
physical-axis value when metadata is available. Complex data can be shown as
magnitude, phase, real, or imaginary values.

### Import an ordinary image

Use **File → Import → Image…** to import PNG, JPEG, TIFF, BMP, WebP, or GIF
files. The image is oriented using its EXIF metadata, converted to grayscale,
and added to the workspace as one-layer UDS data with shape
`(1, height, width)`. Transparent pixels are composited on white, native
grayscale and 16-bit intensity values are preserved, and only the first frame
of a multi-frame image is imported. Use **File → Save…** afterward to save the
workspace item as a native HDF5 `.uds` file.

## Display controls

Each panel provides colour-range and colormap controls. Use:

- **View → RT-ColorMap (Primary)** to edit the Primary colormap live.
- **View → RT-ColorMap (Reference)** to edit the Reference colormap live.

Preferences control whether layer, cursor, picked points, and field-of-view
zoom are synchronised between panels.

### Curve preview

Open the **Curve Preview** tab on the right for a temporary live view derived
from points picked in Primary. **Point spectra** plots every picked position
against the stack's layer or energy axis. **Line cut** uses points 0 and 1 and
can place either distance or layer/energy on the X axis. Its sampling method,
interpolation order, width, and number of samples can be adjusted above the
plot. **Circle cut** also uses points 0 and 1 as the centre and radius endpoint;
it can place either angle or layer/energy on the X axis and exposes
interpolation order, radial averaging width, and angular sample count.
All preview modes use the Primary panel's current **Type** representation, so
switching among Abs, Angle, Real, and Imag updates the plotted curves.

The preview updates after points are added, removed, or moved. It does not add
a workspace item or process-history entry; run the registered process when a
permanent result is required. Reference Image and Curve Preview retain their
own state when switching tabs.

### Preferences

Open **File → Preferences…** from this module to configure:

- **Color map:** choose and order the palette shown by both panels.
- **Sync:** independently synchronise layer, picked points, live cursor, and
  field-of-view pan/zoom from Primary to Reference.
- **Scale:** set histogram sigma scaling, FFT upper scaling, scale-button zoom,
  and canvas wheel sensitivity.
- **Canvas:** limit canvas size and configure the optional bias-value overlay.
- **Curve preview:** select a scene template created by Curve Stack Viewer.
  The template is loaded once when this Image Stack Viewer instance is created
  and is retained across primary-data changes. It is reloaded only when this
  preference changes.

Use **Apply** for the current viewer and **Save as default** for future Image
Stack Viewer instances.

## Annotations

Processing uses the data in **Primary** as the primary input. After selecting
points on that canvas, choose **Points → Cut → Set Line Cut from Primary**,
**Points → Set Mask Center from Primary**, or **Points → Set Interest Region
from Primary**, as appropriate. These commands save annotations beneath the
Primary data item in **Workspace**; expand that item to inspect them.

When **Reference Image** shows the FFT of the current Primary data, pick the
required peaks there and choose **Points → Set Bragg Peaks from Reference**,
**Points → Set Filter Points from Reference**, or **Points → Set Lock-in Peak
from Reference**. The saved peak information belongs to the original Primary
data item, not to its FFT item: the reciprocal-space coordinates guide
processing of the Primary data. Ensure Reference really is the corresponding
FFT before setting these annotations.

Setting the same annotation type again replaces its previous values. Moving
or removing canvas points does not update an existing annotation; repeat the
appropriate **Points** command to save the revised selection. Other processes,
such as registration, may also require a reference input: check **Active
Processing Slots** and the process dialog before running.

Right-click the image to pick points. The **Points** menu converts current
selections into named annotations used by processes, including:

- Interest region and mask centre
- Bragg peaks and filter points
- Lock-in peak
- Line and circle cuts
- Source and reference registration points

The same menu clears annotations when they are no longer required. Consult a
process in the Process Browser to determine which annotations it expects.

## Export

Use **File → Export Image…** (`Ctrl+E`) for a rendered image and
**File → Export Video…** (`Ctrl+Shift+E`) for a layer sequence. Use
**File → Save…** to save supported workspace data rather than a rendered view.

In the image export dialog, choose **Destination = File** to save the displayed
image or **Destination = Clipboard** to paste it into another application.
This differs from **File → Import → Image…**, which reads an existing image
from disk into the workspace.

For multilayer data such as energy-resolved dI/dV maps, video export creates
one frame for each layer in the selected range. Select the panel, layer range,
format, and frame rate. See the [step-by-step export instructions](file-formats.md#tutorial-save-data-and-export-results).
