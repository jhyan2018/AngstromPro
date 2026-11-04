# Curve Stack Viewer

The Curve Stack Viewer displays two-dimensional spectroscopy and line-scan data
as a matplotlib figure containing a stack of curves.

A one-dimensional single-point spectrum is treated as a single-curve stack:
conceptually a two-dimensional dataset with a stack dimension of size one.
The viewer supports comparison, styling, figure export, and editable scene
saving without requiring multiple curves.

## Locate the plot controls

Open this module from Main Workbench with **+ New Module → Basic → Curve Stack
Viewer**, or click **Show** on its existing card.

- **View → Workspace** shows the data-item list. Single-click a row to select
  it; double-click raw UDS data to start a new plot. Right-click a row for
  **Add to plot**, **Set as Reference**, or **Clear Reference** when available.
- **Datasets / Curves** is the tree at the left of the central plotting area,
  not the Workspace dock. Expand a dataset with its disclosure arrow;
  single-click a trace to select it and click its checkbox to show or hide it.
  Right-click a plotted dataset here for **Configure Error Bars…** or
  **Remove Error Bars**.
- **Extract to workspace** is a button below the **Datasets / Curves** tree.
  Select the desired entries in that tree before clicking the button.
- **Mode** is the dropdown above the plotting area. In **Stack** mode, the
  **Offset** field and **Y Auto** button are above the curve plot.
- **View → Curve Style** and **View → Axes** open the styling docks.
  If tabbed together, click the **Curve Style** / **Axes** tab to switch.
  **X factor** and **Y factor** are fields in the **Axes** dock.
- **Scene → Save as Scene…**, **Scene → Save Template…**, and **Scene → Load
  Template → template name** are menu commands. The default template is under
  this module's **File → Preferences…**, in **Default template**.

## Tutorial: compare and style spectra

**Goal:** compare measured spectra or extracted line cuts and prepare an editable
figure.

**Input:** one or more curve-stack items, such as loaded spectroscopy files or
a [line-cut result](image-stack-viewer.md#tutorial-create-a-line-cut).

1. Open **Curve Stack Viewer** from Main Workbench. Open your file with
   **File → Open…**, or send the curve-stack item to this module.
2. Double-click the first workspace item to make it the primary dataset and
   start a plot. Check the sweep-axis values and units in the Inspector.
3. To overlay another dataset, right-click its workspace row and choose
   **Add to plot**. Do not double-click it for this purpose: double-clicking a
   raw UDS starts a new primary plot and clears the previous displayed set.
4. Expand **Datasets / Curves** to select individual traces. Use **Mode =
   Stack** to view curves. Start with **Offset = 0** for a direct comparison;
   use a nonzero **Offset** when traces overlap, and record that presentation
   offset in the figure description. **Y Auto** fits the visible curves.
5. Select a trace and open **View → Curve Style** to adjust its line appearance.
   Open **View → Axes** to set the title, axis labels, limits, scales, grid,
   and legend.
   Click the triangle beside the dataset in **Datasets / Curves**, then
   single-click the required curve before changing its style. **Curve Style**
   controls that curve's appearance; **Axes** controls the plot's axes and
   affects curves sharing those axes, not just the selected curve. If the
   docks overlap, switch using their **Curve Style** and **Axes** tabs.
6. Check **X factor** and **Y factor** before finalising unit labels. For
   example, a factor of `1e3` applied to an axis stored in volts displays
   millivolts. These are display multipliers; do not also relabel the stored
   data as though it had been numerically converted.
7. Try **Mode = Colormap** when a dense stack is easier to inspect as a map,
   then return to Stack for individual-trace styling and error bars.
8. Save the editable plot and export a figure using the next tutorial.

**Expected result:** a labelled comparison plot with a deliberate choice of
limits, units, trace selection, and offsets.

**Process-input check:** **Add to plot** changes the display but not the
staged process inputs. For a two-input operation, activate the intended primary
dataset by double-clicking it, then right-click the other workspace item
and choose **Set as Reference**; verify
**Active Processing Slots** before running. A saved scene is not itself a numerical
curve-stack input. To process curves recovered from a scene, select them in
**Datasets / Curves**, click the **Extract to workspace** button below that
tree, review the names, and
activate the resulting UDS item.

## Tutorial: save an editable plot and export a figure

1. After styling, choose **Scene → Save as Scene…**, enter a scene name, and
   confirm. A new **scene_plot** item appears in the workspace.
   It captures the plotted datasets together with line styles, colours,
   axis settings, and other scene configuration; it does not yet save a file.
2. Single-click that scene item and choose **File → Save…**. Save it as
   `.scplot`. This is the step that writes the editable scene to disk.
3. Choose **File → Export Figure…** to create a presentation copy. Set
   **Destination = File**, choose **PNG**, **PDF**, **SVG**, or **TIFF**, and
   set **Resolution** when using a raster format. Review transparent-background
   and trim-whitespace options, confirm, and choose the output filename.
4. Open the exported file and check labels, units, legend, cropping, and
   readability at the intended final size.
5. To check the editable copy, open a second Curve Stack Viewer, choose
   **File → Open…**, select the `.scplot`, and double-click its workspace
   item. The datasets and scene styling should be restored.

**Expected result:** a `.scplot` for further editing and a separate exported
figure for presentation. Exporting alone does not save an editable scene.

**To reuse the appearance with other measurements:** choose **Scene → Save
Template…**. Apply it via **Scene → Load Template**, or select it as the
module's **File → Preferences… → Default template** setting. A `.scet` template contains
styling, not the scientific datasets.

**After further edits:** create a new scene snapshot and save that workspace
item again. A previously captured scene is an independent snapshot; subsequent
plot edits do not automatically update the file.

## Tutorial: plot an average spectrum with error bars

**Goal:** display the spatial mean of a spectroscopy map with a clearly
identified measure of variation or uncertainty.

**Input:** an Image Stack Viewer item shaped `(energy, rows, columns)`.
Confirm that the first axis really is bias/energy, not time or an image index.

1. In Image Stack Viewer, activate the spectroscopy map and run **Average
   Spectrum 2D** from your [configured Process menu](processes.md#tutorial-configure-a-process-menu).
2. Set **Error quantity** to **Standard deviation** to show the spatial spread
   of spectra, or **Standard error** for the implementation's estimate of the
   uncertainty of the spatial mean. Click **Run**.
3. Identify the two result items: the mean normally ends in `_avg`; the
   matching error ends in `_avg_std` or `_avg_sem`.
4. Send both items to the same Curve Stack Viewer, selecting and sending each
   workspace row in turn. Alternatively, make both accessible through a
   shared workspace.
5. Double-click the mean item. In **Datasets / Curves**, right-click its
   dataset entry and choose **Configure Error Bars…**.
6. Select the matching error UDS. Set the cap size, error-line appearance,
   and spacing between drawn bars, then confirm.
7. Use **Mode = Stack** to see the error bars. State which quantity is plotted
   in the axis label, legend, or accompanying figure caption.
8. Save a scene and write it to `.scplot` to preserve both the plotted data
   and the error-bar relationship. Save the two UDS outputs separately when
   the numerical results are also needed.

**Expected result:** one mean spectrum with symmetric Y error bars on a
matching sweep axis. The errors must have the same shape, sweep values, and
units as the mean and must be finite and non-negative.

The standard error calculation divides by the square root of the spatial
pixel count. Spatially correlated pixels are not independent measurements,
so interpret this value in the context of your acquisition; it is not a
general estimate of all experimental uncertainty. A one-layer topography
does not provide an energy-dependent average spectrum.

## Build a plot

- Double-click a workspace item to make it the primary dataset.
- Right-click an item in the Workspace list and choose **Add to plot** to overlay it.
- Right-click the intended Workspace item and choose **Set as Reference** when a two-input process needs that item.
- Right-click a Workspace item and choose **Clear Reference** to remove the current reference assignment.

Use the Curve Style dock to edit individual artists and the Axes dock to change
labels, limits, scales, and grid settings. Both docks can be shown or hidden
from the **View** menu.

### Error bars

Right-click a plotted dataset in the **Datasets / Curves** tree and choose
**Configure Error Bars…**. Select an accessible UDS containing symmetric
Y-error magnitudes, then set cap size, error-line width, color, and the spacing
between drawn bars. Choose **Remove Error Bars** from the same menu to detach
them.

For a 1D curve, the error UDS must also be 1D with the same number of points.
For a 2D curve stack, it must have the same `(curves, points)` shape. Sweep-axis
values and units must match, and error magnitudes must be finite and
non-negative. Curves and errors use the same axis-level display factor, so they
always remain in the same displayed unit.

The Axes dock shows editable **X factor** and **Y factor** fields. These are
discrete engineering multipliers such as `1e3`, `1`, and `1e−3`, chosen
automatically when the first dataset is added and then kept fixed. AngstromPro
uses the corresponding SI prefix in the generated label: multiplying volts by
`1e3` produces millivolts and `Bias (mV)`; multiplying amperes by `1e12`
produces picoamperes and `Current (pA)`. Automatic factors are bounded by the
named prefixes tera (`T`) and atto (`a`). Factors are stored with the scene,
including a separate Y factor for the right-hand axis.

The **Average Spectrum 2D** registered process creates an average spectrum and
a directly compatible error UDS. Its **Error quantity** option defaults to
standard deviation, which shows spatial variation. Choose standard error when
you instead want the uncertainty of the mean; it is smaller by the square root
of the number of spatial pixels.

Error bars are displayed in **Stack** mode. Colormap mode continues to show the
central values and retains the error association when switching back. Saving a
`ScenePlot` embeds the selected error UDS and its styling, so the saved scene
does not depend on the original workspace item. Saving the curve as an
individual UDS does not include this plot-only relationship.

## Scenes and templates

A scene and a template serve different purposes:

- A `ScenePlot` is AngstromPro's runtime plot object. It contains the figure
  and axes structure, artist descriptions, styling, and the UDS datasets used
  by those artists. Saving it as `.scplot` preserves the complete editable
  plot.
- A `.scet` scene template contains reusable presentation settings but no
  scientific dataset. It controls how fresh/raw UDS data is turned into a new
  plot.

Use **Scene → Save as Scene…** (`Ctrl+Shift+S`) to capture the complete scene
as a workspace item, then select that item and use **File → Save…** to write
it to a `.scplot` file. After styling a plot, use **Scene → Save Template…**
to reuse that appearance, or **Scene → Load Template** to apply a saved template.

Choose **File → Preferences… → Default template** in Curve Stack Viewer when every
fresh UDS dataset loaded as a new primary plot should begin with that style.
The template is applied before the raw UDS data is rendered. Loading a saved
`ScenePlot` instead restores the scene's own data, layout, and styling; it does
not replace them with the default template.

Saved templates are shared with the Data Browser, which can use the same style
when generating thumbnails for raw UDS data. Reopen a `.scplot` through the
normal file-loading workflow.

## Preferences

Open **File → Preferences…** from this module to configure:

- **Color map:** choose and order the colormaps available to fresh plots.
- **Default template:** select the `.scet` style applied when fresh raw UDS
  data becomes a new primary plot. Select `(none)` for Matplotlib defaults.

The default template does not override an existing plot or a loaded `.scplot`.
Use **Apply** for the current module and **Save as default** for future Curve
Stack Viewer instances.

## Export

Use **File → Export Figure…** (`Ctrl+E`) to produce a publication figure. Exporting a
figure is different from saving a `.scplot`: the exported image is intended for
presentation, whereas the scene remains editable inside AngstromPro.
