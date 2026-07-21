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

- A `.scplot` scene stores the complete plot, including its data and styling.
- A `.scet` template stores reusable style settings for fresh plots.

Use **Scene → Save as Scene…** (`Ctrl+Shift+S`) to save a scene. Use the same
menu to load or save templates and manage the default style. Reopen a `.scplot`
through the normal file-loading workflow.

## Export

Use the export command (`Ctrl+E`) to produce a publication figure. Exporting a
figure is different from saving a `.scplot`: the exported image is intended for
presentation, whereas the scene remains editable inside AngstromPro.
