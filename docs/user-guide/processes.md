# Processes

Processes are registered analysis operations. A process declares the data it
accepts, any annotations it needs, its parameters, and the result it produces.
AngstromPro uses this information to present the correct dialog and to avoid
offering incompatible operations where possible.

## Tutorial: configure a process menu

**Goal:** make the operations needed for your analysis available in the viewer.

**Input:** an open Image Stack Viewer or Curve Stack Viewer. These instructions
use Image Stack Viewer as the example.

1. Choose **Process → Process Browser…** to inspect an operation's description,
   inputs, and parameters. Search by the displayed label or process ID.
   This browser is informational; it does not run the selected process.
2. Close the browser and choose **Process → Configure Process Menu…**.
3. In the configuration dialog, set the **Module** dropdown to **Image Stack Viewer**.
4. Click the **Add submenu…** button, enter `Basic analysis`, and select that submenu
   in **Process menu layout**.
5. Search **Available processes** for **Background Subtract 2D**, single-click it,
   and click **→** to add it to the selected submenu.
6. Add **FFT 2D**, **Crop Square 2D**, **Line Cut 2D**, and **Average Spectrum
   2D** in the same way if you need them.
7. Click **Save** in the configuration dialog, then open **Process → Basic analysis** to check the entries.

**Expected result:** your new submenu is available for that module type. You
can choose a different submenu name; all subsequent tutorials mean the submenu
you configured, not a built-in category.

**If an operation is unavailable:** load a compatible item and check its shape.
Image-stack operations expect `ndim=3`, including a single image stored as
`(1, rows, columns)`. Curve-stack operations normally expect `ndim=2`, even
though the Curve Stack Viewer can also display a one-dimensional spectrum.
Search the Process Browser to distinguish an unregistered operation from a missing menu
shortcut. Compatibility settings can hide or disable unsuitable operations.

## Tutorial: run background subtraction

**Goal:** remove a fitted background from a topographic image while retaining
the raw data for comparison.

**Input:** a real-valued topography loaded into Image Stack Viewer. First
[add Background Subtract 2D to the menu](#tutorial-configure-a-process-menu).

1. Double-click the raw topography in the Workspace. Verify its name under
   **Primary** and in **Active Processing Slots**.
2. Choose **Process → Basic analysis → Background Subtract 2D** (or the submenu
   name you created).
3. Check **3D Stack** in the **Inputs** section. The first input is locked to
   the module's staged primary item. If it is wrong, cancel, activate the
   intended workspace item, and reopen the process.
4. For a tilted surface, start with **Method = 2DPlane** and **Polynomial
   order = 1**. To remove line-dependent backgrounds instead, select
   **PerLine** and the appropriate **Per-line direction**:
   **Y** fits down each image column; **X** fits across each image row.
5. Review the settings even if you ran this process earlier: parameters can
   be remembered. Use **Reset to defaults** when you want a fresh starting
   point, then select your intended values.
6. Click **Run**. Wait for the result to appear in the workspace; the normal
   result suffix is `_bg` (aliases or duplicate names can affect the label).
7. Double-click the result to display it. Inspect its processing history and
   compare it with the raw image using the
   [Primary/Reference procedure](image-stack-viewer.md#tutorial-compare-raw-and-processed-images).
8. Single-click the result and choose **File → Save…** to save a native
   `.uds` copy.

**Expected result:** a new dataset has reduced fitted background. The operation
preserves each layer's overall mean, so the result need not have a mean of zero.
The source file and original workspace dataset remain available.

**Interpretation:** a flatter-looking image is not sufficient evidence of a
better scientific result. Check that genuine long-wavelength structure, steps,
or features of interest have not been removed. Use the lowest suitable order
and record the selected method and direction.

**If no result appears:** check the process input and any reported task error.
The operation acts on every layer in the input stack, not only the layer
currently displayed.

## Tutorial: crop a region for further analysis

**Goal:** create an even-sized square image stack from an area of interest.

1. Activate the source in Image Stack Viewer. Remove unwanted entries from
   **Picked Points** using **Remove Point**, leaving the list empty.
2. Right-click two opposite corners of the desired region in **Primary**.
   Optionally select **Region** in Primary's point-display dropdown beside
   **Picked Points** to see the box.
3. Choose **Points → Set Interest Region from Primary**. Expand the workspace
   item and confirm that an `interest_region` annotation exists.
4. Run **Crop Square 2D** from your configured Process menu.
5. Inspect the new `_cp` item and its axes, then save it if needed.

**Expected result:** all layers are cropped together. The output is square
with an even side length; it is not an arbitrary rectangular crop. The process
can shorten the selected region to satisfy these constraints.

If you move the picked corners, use **Points → Set Interest Region from Primary** again
before rerunning the process. Moving the visual markers alone does not update
the saved annotation.

## Where process controls are located

In the viewer, open **View → Workspace** and double-click the intended input
item. Check **Active Processing Slots** below the Workspace list. Open the
operation using **Process → your configured submenu → operation**.
The operation's dialog shows **Inputs**, required **Annotations**, and its
parameter fields. Change dropdowns or numeric fields there, not in Process
Browser. Click **Reset to defaults** at the bottom to reset the fields, or
**Run** to submit the operation. If the first input is wrong, click **Cancel**,
double-click the correct workspace item, and reopen the operation.

To inspect the result, single-click its Workspace row and open **View →
Inspector**. Expand the data/history nodes using their disclosure arrows.
Double-click the row in Workspace when you want to display the result.

## Run a process

1. Double-click the intended workspace item to activate the primary input.
   For a two-input operation, also assign its reference. In Image Stack
   Viewer, single-click the reference item and click **Select Variable** in
   **Reference Image**. In Curve Stack Viewer, right-click the reference
   item and choose **Set as Reference**.
2. Check **Active Processing Slots**, then choose an operation from the
   module's configured **Process** submenu. Required inputs must already be
   assigned and have compatible types and dimensions for its dialog to open.
3. In the dialog, review **Inputs** and **Annotations**, choose any editable
   additional inputs, and set the parameters. The first input is fixed to
   the staged primary item.
4. Click **Run** and wait for the new result item or items in **Workspace**.

Long-running operations execute through the task system so the interface can
remain responsive. Successful results are added to the module workspace and
record their processing history. Parameter values are remembered for later
runs.

Some operations need annotations such as picked points, a region, or reference
points. In the Image Stack Viewer, create these from the **Points** menu before
running the process.

For **Background Subtract 2D → PerLine**, choose **Per-line direction**: `Y`
fits down each image column, while `X` fits across each row. The default is `Y`;
select whichever direction follows the unwanted line background in your image.

**Gap Map 2D** returns two items. The `_gm` item contains the fitted peak
energy, and `_R2` is the R² fit-quality map: values near 1 indicate that the
selected polynomial describes the spectrum well. Empty, non-finite, or
constant spectra have no defined peak or R² and are written as zero in both
outputs. The fit is normalized internally, so the result does not depend on
whether the signal is stored in A, nA, or pA. **Energy minimum** and **Energy
maximum** use the physical values and units of the input layer axis; each bound
is mapped to the nearest recorded layer. The full input range is selected when
the dialog first opens, including for descending energy axes.

**Coherence Peak Width 2D** measures the FWHM of one coherence peak inside a
physical energy window. Its **Width method** choices are:

- **Half-prominence** (default): model-free interpolated width after removing a
  linear edge baseline.
- **Gaussian**, **Lorentzian**, or **Voigt**: fit a linear baseline plus the
  selected phenomenological line shape.

The process returns `_peak_width` and `_peak_quality` items. Quality is a
prominence-to-noise score for Half-prominence and clipped R² for the three fit
methods; all quality values range from 0 to 1. A width and quality of zero mark
a missing, constant, non-finite, edge-truncated, or failed peak. The fitted
line shape is an estimator and does not by itself identify the physical
broadening mechanism.

## Process Browser

Open **Process → Process Browser…** or press `Ctrl+B` to inspect every
registered process. The browser can filter by name, label, or category and
shows:

- Process ID and description
- Required input ports and dimensionality
- Output types
- Parameters, defaults, ranges, and units

The naming convention uses `_1D` for operations on curve stacks (`ndim=2`) and
`_2D` for operations on image stacks (`ndim=3`). Verify axis orientation in the
item inspector before processing unfamiliar data.

## Process categories

Each registered process has a developer-provided category used for searching
and browsing. Categories do not determine the submenus shown under
**Process**. Those submenu names and contents are entirely user-defined.

## Configure a module menu

Use **Process → Configure Process Menu…** to build the Process submenus for a
particular module. A new layout starts empty; until a submenu is created, the
Process menu contains only **Process Browser…** and
**Configure Process Menu…**.

1. Select the target module type.
2. Create and name one or more submenus.
3. Add compatible processes to the selected submenu.
4. Rename, delete, or reorder submenus and processes as needed.
5. Use **Move to…** to move selected processes between submenus.
6. Save the configuration.

Removing a process from this tree only removes its shortcut from the module
menu. The process remains registered and available through Process Browser.

## Simulations

Registered simulations appear in the **Simulate** menu. Unlike normal
processes, a simulation may generate data without an input dataset.
