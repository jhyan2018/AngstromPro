# Preferences

Open **File → Preferences…** or press `Ctrl+,`. The window from which you open
Preferences determines what is shown:

- The **Main Workbench** contains application-wide settings shared by every
  module, including file-channel mappings.
- A module window contains settings for that module type. For example, open
  Preferences from the Image Stack Viewer to configure its synchronisation,
  scale, canvas, and colormap defaults.

## Navigating the dialog

On Windows, Preferences is under **File → Preferences…**. On macOS, Qt moves
it into the application menu, which may be labelled **Python**. Bring the
intended AngstromPro window to the front before opening Preferences.

Open **File → Preferences…** in the window whose settings you want to edit.
The bold section names below are sections inside this dialog, not independent
menu-bar entries. Expand a collapsed section or embedded editor to reveal its
controls. Click checkboxes to toggle them, select dropdown values, and edit
text or number fields. The **Apply**, **Save as default**, and **Reset to
default** buttons are at the bottom of the Preferences dialog.

For example, **File → Preferences… → Sync → Sync layer** means open Preferences
in Image Stack Viewer, find **Sync**, then change its **Sync layer** checkbox.
For application-wide **Plugins**, **Startup**, or **General** settings, start
from the Main Workbench instead.

## Applying and saving changes

The three buttons have different scopes:

| Button | Effect |
| --- | --- |
| **Apply** | Uses the edited values in the current session. Open widgets update where supported, but the values are not written as future defaults. |
| **Save as default** | Applies the values and stores them in the active user-data folder. New module instances and later application sessions use them. |
| **Reset to default** | Restores AngstromPro's built-in values in the fields and current session. Use **Save as default** afterward to remove saved overrides. Channel mappings are independent and are not changed by this bulk reset. |

For settings concerned with startup or plugin discovery, click **Save as
default** and restart AngstromPro. Data Browser display and scanner settings,
viewer display settings, and colormap palettes are applied to the open module.

## Application settings

Open **File → Preferences…** from the Main Workbench for these sections:

- **General** controls log visibility and whether sending moves or copies a
  workspace item.
- **User data** changes the parent location used for configuration, cache, and
  logs on the next new application session.
- **Appearance** controls theme, font family, and application font size.
- **Hidden workspace docks** chooses module types whose Workspace dock starts
  hidden; use **View → Workspace** to show one again.
- **Excluded send targets** removes selected module types from Send dialogs.
- **Plugins** configures local plugin source paths. Restart AngstromPro after
  changing plugin discovery.
- **Files** supplies the starting folders for Open and Save dialogs.
- **Channels** configures multichannel file formats; see below.
- **Startup** chooses which modules and how many instances open at launch.

## Channel mappings

The Channel Manager is application-wide even when opened from Data Browser
Preferences. It currently applies to the built-in Nanonis `.3ds`, `.sxm`, and
`.dat` loaders.

Open **File → Preferences… → Channels** in Main Workbench or Data Browser,
expand the **Channel mappings** editor if collapsed, then single-click a
**File format** on the left before editing its independent settings.
Each table row describes one logical AngstromPro channel:

- **Display name** is the stable name used for the loaded dataset and Data
  Browser card.
- **Load by default** is a checkbox in each channel row. It preselects a
  matched channel in the normal file-open dialog. It also determines which
  channels the Data Browser renders as thumbnails.
- **Exact aliases** are semicolon-separated raw channel names. Matching is
  exact and case-sensitive; their order determines which match wins first.
- **Source (.3ds)** distinguishes swept **Channels** from per-pixel
  **Experiment parameters**. Choose the source of a logical row, or **Either**
  when both are possible. This choice is used for file opening and Data Browser
  thumbnails. **Either** prefers a Channel if the exact same alias exists in
  both sources; choose **Experiment parameters** to force the per-pixel map.
  Other formats continue to use their ordinary channel list.
- **Auto-load defaults for this format (skip selection dialog)** is a separate
  checkbox above the table, applying to the selected file format.
  It skips the normal selection dialog and loads the matched default rows.

For a given **File format**, you can check **Load by default** for multiple
channel rows, not just one. For example, select both topography and dI/dV if
both are available in your files. When opening a file, all matching checked
channels are preselected in the selection dialog. If **Auto-load defaults for
this format** is enabled, they load together automatically from that file.
This selects multiple channels; it is different from entering multiple
**Exact aliases**, which are alternative names for a single logical channel.

These two default controls work together as follows:

| Load by default | Format auto-load | Opening `.3ds`, `.sxm`, or `.dat` |
| --- | --- | --- |
| Checked | Off | The normal channel-selection dialog opens with the matched row preselected. |
| Checked | On | The matched channel loads without the normal selection dialog. |
| Checked but no alias matches | On | An **Unmatched channels** dialog asks for a raw channel or allows the logical channel to be skipped. |
| Unchecked | Either | The logical channel is not selected automatically. |

During unmatched-channel resolution, select **Save alias** to prepend the raw
channel name to that logical channel for future files. For `.3ds`, the dialog
labels both sources; saving a chosen experiment parameter also remembers its
source. Switching between file
formats in Channel Manager preserves edits as drafts. Press **Apply** to use
all edited formats for the current session, or **Save as default** to retain
them after restarting.

For `.3ds`, the normal selection dialog labels each source and lets you check
multiple candidates, such as **Z (m)** and **Scan:Z (m)**, to compare them.
Experiment parameters contain one value per grid pixel, so each loads as a
single-layer image rather than a bias-sweep stack.

The format-level auto-load option does not change thumbnail selection: Data
Browser renders matched channels marked **Load by default** and shows a
missing-channel card when a default channel has no match. Existing cached
thumbnails are not rewritten merely because mappings changed; right-click
the affected card and choose **Re-render thumbnail**, or open Data Browser's
**File → Preferences… → Cache** and click **Re-render all…**.

## Tutorial: configure a measurement channel

Before importing your first measurement, check the mappings for `nanonis_3ds`,
`nanonis_sxm`, or `nanonis_dat`, as appropriate. For example, the default
`nanonis_3ds` row with **Display name = dI/dV** includes `LI Demod 1 X (A)`
among its **Exact aliases**. If you named that acquisition channel differently
in Nanonis before the experiment, enter the name actually recorded in the
file, not merely the label you want AngstromPro to display. Multiple aliases,
separated by semicolons, are alternative matches for one logical channel;
they do not merge several physical channels.

Review any channel-selection or unmatched-channel dialog that appears when
opening data. A prompt is not guaranteed on every first opening, because it
depends on the auto-load settings and matching results. If a channel is
missing or incorrectly identified, return here and check its exact raw name.

**Goal:** make the file loader and Data Browser recognise the channel names
used by your instrument.

**Input:** a `.sxm`, `.3ds`, or `.dat` file whose desired channel is missing
or has an unexpected label.

1. Open **File → Preferences…** from Main Workbench or Data Browser and find
   the **Channels** settings.
2. Select the correct **File format**. Settings for different formats are
   independent.
3. Find the logical channel row, or click **Add channel** below the table.
   Double-click its **Display name** cell to edit the label. Double-click
   its **Exact aliases** cell to enter the instrument's exact raw name,
   retaining its case, spaces, and unit suffix. Separate alternative raw names
   with semicolons.
4. For `.3ds`, use the row's **Source (.3ds)** dropdown: **Channels** for a
   swept signal, or **Experiment parameters** for one value per spatial pixel.
   A per-pixel Z parameter is not a bias-resolved spectrum.
5. Check **Load by default** to preselect this channel during file opening and
   include matching files in the browser's channel thumbnails.
6. Leave **Auto-load defaults for this format** off while checking the setup.
   Choose **Apply**, open a representative file, and inspect the matching raw
   channel shown by the picker.
7. Verify the loaded values, axis units, and dimensionality in the Inspector.
   Once the mapping is correct, choose **Save as default**. You may enable
   format auto-loading if future files should load those channels without the
   normal selection dialog.
8. Re-render affected Data Browser thumbnails to refresh existing cached cards.

**Expected result:** your intended channel is selected consistently for future
files with that raw name. The acquisition file itself is unchanged.

**If you do not know the exact alias:** use the file loader's unmatched-channel
dialog to inspect the available raw channels and select the intended one.
**Save alias** remembers that mapping; first confirm that the signal and units
are correct.

## Module settings

Open **File → Preferences…** from the named module below; the bold labels
identify sections or fields inside that module's Preferences dialog.

### Data Browser

- **Watch folders** controls the roots shown in the folder tree.
- **Watched formats** controls both gallery visibility and formats processed by
  the background scanner. The Formats button in the main browser toolbar is a
  separate, temporary view filter.
- **Background scanner** enables background thumbnail generation and controls
  scan order and pacing.
- **Thumbnails** controls card size, curve-to-colormap stack threshold, plot
  template, display-only Z background subtraction, and the in-memory pixmap
  cache.
- **Gallery navigation** can hide cards rated exactly one star and sets the
  gallery's mouse-wheel step in pixels per notch. Hiding does not affect
  unrated or 2–5-star cards. The default wheel step is 80 pixels; touchpad
  gestures are unaffected.
- **Channels** edits the same application-wide Channel Manager described
  above. Auto-load affects interactive opening, not background rendering.
- **Cache** controls orphan cleanup and provides cache inspection and
  regeneration tools.

Changing thumbnail style, background processing, or channel mappings does not
rewrite already cached images. Re-render the affected cards to see the change.

### Image Stack Viewer

- **Color map** chooses and orders the palette shown in both image panels.
- **Sync** independently synchronises layer, picked points, live cursor, and
  field-of-view pan/zoom from Primary to Reference.
- **Scale** controls histogram sigma scaling, FFT upper scaling, scale-button
  zoom, and canvas wheel sensitivity.
- **Canvas** controls maximum canvas size and the optional bias-value overlay.
- **Curve preview** selects a scene template created in Curve Stack Viewer.
  Each Image Stack Viewer loads it once and retains the resulting preview style
  across primary-data changes; choosing a different template reapplies it.

### Curve Stack Viewer

- **Color map** chooses and orders the colormap palette available to plots.
- **Default template** styles each fresh raw UDS plot. It is not applied over a
  loaded `.scplot`, because a saved scene already contains its own styling.

### Planewave Synthesiser

- **Color map** chooses and orders the image palette.
- **Scale** controls histogram sigma scaling, scale-button zoom, and canvas
  wheel sensitivity.
- **Canvas** controls maximum canvas size and the optional bias-value overlay.

Plugin modules may contribute additional sections. Their settings can be
stored in separate plugin configuration files.

See the [Data Browser](data-browser.md),
[Image Stack Viewer](image-stack-viewer.md),
[Curve Stack Viewer](curve-stack-viewer.md), and
[Planewave Synthesiser](planewave-synthesiser.md) guides for the surrounding
module workflows.

## Appearance

AngstromPro provides its own compact light and dark themes. They use a
consistent Qt Fusion foundation and do not require a separate theme package.
The **Auto** option selects light or dark from the environment when the theme
is applied.

The font-family list contains up to ten modern sans-serif choices available on
the current system, previews each family, and always shows the active choice
when closed. The default 10-point size is intended for information-dense module
panels; its spin box accepts 7 to 24 points. Theme and font changes are applied
application-wide.

## Colormaps

Colormap palette preferences separate available maps by their source:

- **Matplotlib** contains maps supplied by Matplotlib.
- **AngstromPro presets** contains the maps bundled with AngstromPro.
- **My colormaps** contains maps saved beneath the active user-data folder.

Open the editor from **View → RT-ColorMap (Primary)** or
**View → RT-ColorMap (Reference)** in Image Stack Viewer. The real-time
colormap editor provides two distinct save buttons. **Save to My
Colormaps…** stores the editable anchors as a versioned file under
`colormaps/`, registers the map immediately, and makes it available in
Preferences. **Export As…** writes the historical sampled text format to a
location you choose. Legacy `.txt` maps placed directly in the managed
`colormaps/` folder are also loaded for compatibility.

## Storage

Application preferences are saved beneath the selected user-data folder in
`config/config.json`. Interface geometry and other Qt state are stored in
`config/settings.ini`. Only values that differ from built-in defaults need to
be persisted.

The **User data** page shows the active folder and can queue a different parent
location. AngstromPro creates or uses `<parent>/angstrompro-user/`. At the next
new application session it copies the existing user data to the new location
before switching the pointer. The obsolete `cache/snapshots/` folder is not
copied, and the original folder is retained as a backup. Fully exit and launch
AngstromPro again to apply the change.

While a change is queued, a temporary pending record is stored beside the
OS-managed pointer. After the next session adopts the change, that record is
removed and `datapath.txt` contains only the new absolute path.

Plugin modules whose IDs use a plugin namespace can store settings in separate
files under `config/plugins/`, preventing a plugin from overwriting the main
configuration.

Use the Preferences reset controls carefully: regenerable cache data can be
recreated, but configuration changes may need to be entered again.
