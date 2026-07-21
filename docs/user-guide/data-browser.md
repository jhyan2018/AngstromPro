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
