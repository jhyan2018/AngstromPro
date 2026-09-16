# Processes

Processes are registered analysis operations. A process declares the data it
accepts, any annotations it needs, its parameters, and the result it produces.
AngstromPro uses this information to present the correct dialog and to avoid
offering incompatible operations where possible.

## Run a process

1. Load or select the required workspace data.
2. Choose an operation from the module's **Process** menu.
3. Supply any additional inputs and parameters requested by the dialog.
4. Start the process.

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
