# Image Stack Viewer

The Image Stack Viewer is intended for three-dimensional data such as
energy-resolved maps. It presents the **Primary** image beside a persistent
right-hand area that switches between **Reference Image** and **Curve Preview**
without clearing either view. It also maintains a workspace for source data
and results.

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

Open Preferences from this module to configure:

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
