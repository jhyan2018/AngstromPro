# Data Browser

The Data Browser provides a thumbnail gallery for exploring measurement files
in configured watch folders, helping you preview measurements, identify data
of interest, and send selected files to analysis modules without opening each
file individually in a viewer. Its folder tree, filename and format filters,
sorting, and zero-to-five-star ratings help organise browsing; thumbnail-layer
selection and background caching control how previews are generated.

## Tutorial: browse and send a measurement

**Goal:** find a measurement by its preview and load the selected channel into
an analysis module.

**Input:** your measurement folder and at least one supported file. For a
single known file, you can instead [open it directly](file-formats.md#tutorial-open-and-verify-a-measurement).

1. In Main Workbench, click **+ New Module → Basic → Data Browser** and open
   the intended destination with **+ New Module → Basic → Image Stack Viewer**
   for maps or **+ New Module → Basic → Curve Stack Viewer** for spectra.
   Click **Show** on an existing module card instead of creating another instance.
2. From the Data Browser window, choose **File → Preferences…**. In **Watch
   folders**, add the measurement folder. Choose **Apply**, or **Save as
   default** if this folder should remain configured for later sessions.
3. Single-click the folder in the browser tree. Turn on **include subfolders** only
   if measurements are stored below it.
4. Use the filename search and **Formats** filter to narrow the gallery.
   In Preferences, **Watched formats** must also include the format.
5. Read the channel label on the relevant thumbnail card. For a multichannel
   file, identify whether the card represents topography, a spectroscopic
   channel, or another measurement.
6. Right-click the data image on the thumbnail card and choose **Send to module…**.
   Single-click the destination viewer in the dialog and click **OK**, or
   double-click that destination to confirm.
7. In the receiving module, single-click the new workspace row to inspect it,
   then double-click it to display the data. Verify the axes and channel before
   processing.

**Expected result:** a new workspace item contains the measurement channel,
not the thumbnail image. The browser reloads the scientific data from the file
when sending it.

**If no suitable destination appears:** open the required viewer in Main
Workbench and check whether the channel is an image stack or a curve stack.
Also check **File → Preferences… → Excluded send targets** in Main Workbench.

**If the gallery is empty or shows a missing channel:** check the folder,
format filters, and exact channel aliases. After changing mappings, right-click
the affected card and choose **Re-render thumbnail**, or use **Re-render all**
in the cache preferences. See [channel mapping](preferences.md#tutorial-configure-a-measurement-channel).

Background flattening in a thumbnail is only a preview setting. To remove a
background from the loaded data, run
[Background Subtract 2D](processes.md#tutorial-run-background-subtraction).

## Where to find the controls

Use the Data Browser window's **File → Preferences…** dialog for the
**Watch folders**, **Watched formats**, **Background scanner**, **Thumbnails**,
**Gallery navigation**, **Channels**, and **Cache** sections. Click **Apply**
or **Save as default** in that dialog after editing.
The filename search, **Formats** filter, and **include subfolders** checkbox
are controls in the main browser window, not Preferences menu entries.

For a single file, right-click its thumbnail image/card to open the context
menu. **Send to module…** opens a destination dialog; **Show in File Manager**
reveals the file; **Set thumbnail layer…** appears for cached multi-layer data;
**Rating** opens the star submenu; **Re-render thumbnail** refreshes that card.
To refresh all cached previews, open **File → Preferences… → Cache** and click
**Re-render all…**. This is separate from the card's right-click action.

## Watch folders

Add, remove, and reorder watch folders in the Data Browser window's
**File → Preferences… → Watch folders** section.
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

In **File → Preferences… → Gallery navigation**, **Mouse-wheel step
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

The Channel Manager shown under **File → Preferences… → Channels** is
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
Stack Viewer. In **File → Preferences… → Thumbnails**, choose a
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

In the Data Browser window's **File → Preferences…** dialog, you can:

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
