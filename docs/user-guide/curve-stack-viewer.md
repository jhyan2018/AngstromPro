# Curve Stack Viewer

The Curve Stack Viewer displays two-dimensional spectroscopy and line-scan data
as a matplotlib figure containing a stack of curves.

## Build a plot

- Double-click a workspace item to make it the primary dataset.
- Open an item's context menu and choose **Add to plot** to overlay it.
- Choose **Set as Reference** when a two-input process needs that item.
- Choose **Clear Reference** to remove the current reference assignment.

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

Use **Scene → Save as Scene…** (`Ctrl+Shift+S`) to save the complete scene.
After styling a plot, use **Scene → Save Template…** to reuse that appearance,
or **Scene → Load Template** to apply a saved template.

Choose the Curve Stack Viewer's **Default template** in Preferences when every
fresh UDS dataset loaded as a new primary plot should begin with that style.
The template is applied before the raw UDS data is rendered. Loading a saved
`ScenePlot` instead restores the scene's own data, layout, and styling; it does
not replace them with the default template.

Saved templates are shared with the Data Browser, which can use the same style
when generating thumbnails for raw UDS data. Reopen a `.scplot` through the
normal file-loading workflow.

## Preferences

Open Preferences from this module to configure:

- **Color map:** choose and order the colormaps available to fresh plots.
- **Default template:** select the `.scet` style applied when fresh raw UDS
  data becomes a new primary plot. Select `(none)` for Matplotlib defaults.

The default template does not override an existing plot or a loaded `.scplot`.
Use **Apply** for the current module and **Save as default** for future Curve
Stack Viewer instances.

## Export

Use the export command (`Ctrl+E`) to produce a publication figure. Exporting a
figure is different from saving a `.scplot`: the exported image is intended for
presentation, whereas the scene remains editable inside AngstromPro.
