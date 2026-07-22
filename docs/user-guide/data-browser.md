# Data Browser

The Data Browser is the disk-to-application entry point. It combines a folder
tree with a thumbnail gallery and sends supported data to analysis modules.

## Watch folders

Add, remove, and reorder watch folders in **Preferences → Data Browser**.
Watched folders cannot be nested inside one another. Select a folder in the
tree to list its files; enable **include subfolders** when a recursive view is
needed.

The gallery can be narrowed by:

- Filename search
- Readable file format
- Sort order

The format checkboxes in the browser toolbar filter the current view. The
watched-format selection in Preferences additionally controls which formats
the background scanner processes.

## Thumbnail cards

A card represents a file and, for multichannel formats, the configured channel
used for its preview. From a card's context menu you can:

- Send the data to a compatible module
- Select a thumbnail layer for stack data
- Assign a rating from zero to five stars
- Re-render the thumbnail

If a required channel cannot be matched, review the application-wide channel
mappings in Preferences.

## Scene templates for thumbnails

The Data Browser can use the same `.scet` scene templates saved by the Curve
Stack Viewer. In **Preferences → Data Browser → Thumbnails**, choose a
**Plot template** to give raw UDS thumbnails a consistent presentation style.
The template can carry settings for both curve-stack and colormap rendering;
the browser chooses the appropriate representation from the dataset and its
configured stack threshold.

A template supplies styling only: it does not replace or modify the UDS data.
For a saved `ScenePlot` (`.scplot`), the thumbnail renderer uses the scene's own
stored layout and styling instead of the Data Browser template.

The **Z thumbnail background** preference optionally preprocesses data resolved
by the Channel Manager to the logical display channel `Z`:

- **Off** renders the raw image.
- **Polynomial surface** subtracts a first-order 2D plane, making tilted
  topography easier to see.
- **Per scan line** subtracts a first-order polynomial independently from every
  image row, reducing line-by-line scan backgrounds.

This is display-only: it does not change the source file, cached UDS data, or
data sent to another module. Other logical channels are never flattened.

Changing the selected template affects newly generated thumbnails. Existing
cached thumbnails also retain their current image when this background option
changes. Re-render an individual card or use **Re-render all** in the Data
Browser cache preferences to apply the new rendering settings.

## Background scanner

The scanner walks watch folders and pre-renders missing or stale thumbnails at
low priority. Cached thumbnails make later browsing faster and survive an
application restart. Files currently visible in the gallery receive higher
render priority.

In **Preferences → Data Browser**, you can:

- Enable or disable background scanning
- Choose the formats to watch
- Scan newest files first, oldest files first, or by name
- Set the delay between render requests
- Set the idle interval between complete passes
- Change thumbnail size and rendering options
- Inspect, clean, or regenerate the thumbnail cache

Disabling the scanner does not prevent thumbnails from being rendered when
files become visible.
