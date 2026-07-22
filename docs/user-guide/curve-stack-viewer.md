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

## Export

Use the export command (`Ctrl+E`) to produce a publication figure. Exporting a
figure is different from saving a `.scplot`: the exported image is intended for
presentation, whereas the scene remains editable inside AngstromPro.
