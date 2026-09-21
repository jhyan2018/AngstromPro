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

In **Preferences → Data Browser → Gallery navigation**, **Mouse-wheel step
(px)** controls how far one wheel notch moves the thumbnail gallery. The
default is 80 pixels, independent of how many cards are in the folder. Smooth
touchpad gestures and dragging the scrollbar retain their native behavior.

Enable **Hide one-star cards** in the same preference section to use a one-star
rating as a hidden/rejected marker. The filter matches exactly one star:
unrated cards and cards rated two through five stars remain visible. To review
or change hidden ratings, disable the preference temporarily. The underlying
ratings and cached thumbnails are never deleted.

## Thumbnail cards

A card represents a file and, for multichannel formats, the configured channel
used for its preview. From a card's context menu you can:

- Send the data to a compatible module
- Show the source file in the system file manager
- Select a thumbnail layer for stack data
- Assign a rating from zero to five stars
- Re-render the thumbnail

## Multichannel thumbnails

The Channel Manager shown under **Preferences → Data Browser → Channels** is
application-wide; it edits the same mappings available in Main Workbench
Preferences. For `.3ds`, `.sxm`, and `.dat` files, the browser creates cards
only for logical channels that:

1. are marked **Load by default** for that file format, and
2. have an exact, case-sensitive alias matching the configured source in the
   file. For `.3ds`, that source may be **Channels** or **Experiment
   parameters**.

The format-level **Auto-load defaults** checkbox does not control thumbnails.
It controls whether interactive file opening skips the normal channel-selection
dialog. See [Preferences](preferences.md#channel-mappings) for the complete
two-level behavior.

If a card says that a channel was not found, add the raw instrument channel
name as an exact alias. Existing cached cards are not replaced automatically;
re-render the file or use **Re-render all** after changing mappings or default
channels.

A `.3ds` experiment-parameter card is a single-layer spatial image, not a
spectroscopy stack. If you change its source or aliases in Channel Manager,
re-render the cached card to apply the new mapping.

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
- **Per scan line** subtracts a first-order polynomial independently down every
  image column (Y). This is the default per-line direction.
- **Per image row (X)** applies the same operation across each image row.

Choose the direction that follows the visible scan-line artifacts. Both
directions preserve the image orientation and overall mean.

This is display-only: it does not change the source file, cached UDS data, or
data sent to another module. Other logical channels are never flattened.

Changing the selected template affects newly generated thumbnails. Existing
cached thumbnails also retain their current image when the background option,
channel mappings, or default-channel selection changes. Re-render an individual
card or use **Re-render all** in the Data Browser cache preferences to apply the
new rendering settings.

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
- Hide cards rated exactly one star
- Adjust the mouse-wheel step for the gallery
- Inspect, clean, or regenerate the thumbnail cache

Disabling the scanner does not prevent thumbnails from being rendered when
files become visible.

Press **Apply** to use browser changes in the open module. Press **Save as
default** to retain them for future browser instances and application sessions.
