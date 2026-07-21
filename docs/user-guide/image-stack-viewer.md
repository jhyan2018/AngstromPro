# Image Stack Viewer

The Image Stack Viewer is intended for three-dimensional data such as
energy-resolved maps. It presents **Primary** and **Reference** images side by
side and maintains a workspace for source data and results.

## Load data

Send a compatible item from the Data Browser or another module. Workspace items
can then be assigned to the viewer's input roles. The viewer validates that
image-stack data has three dimensions.

The layer control moves through the stack and displays the corresponding
physical-axis value when metadata is available. Complex data can be shown as
magnitude, phase, real, or imaginary values.

## Display controls

Each panel provides colour-range and colormap controls. Use:

- **View → RT-ColorMap (Primary)** to edit the Primary colormap live.
- **View → RT-ColorMap (Reference)** to edit the Reference colormap live.

Preferences control whether layer, cursor, picked points, and field-of-view
zoom are synchronised between panels.

## Annotations

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
