# Preferences

Open **File → Preferences…** or press `Ctrl+,`. The window from which you open
Preferences determines what is shown:

- The **Main Workbench** contains application-wide settings shared by every
  module, including file-channel mappings.
- A module window contains settings for that module type. For example, open
  Preferences from the Image Stack Viewer to configure its synchronisation,
  scale, canvas, and colormap defaults.

## Applying and saving changes

The three buttons have different scopes:

| Button | Effect |
| --- | --- |
| **Apply** | Uses the edited values in the current session. Open widgets update where supported, but the values are not written as future defaults. |
| **Save as default** | Applies the values and stores them in the active user-data folder. New module instances and later application sessions use them. |
| **Reset to default** | Restores AngstromPro's built-in values in the fields and current session. Use **Save as default** afterward to remove saved overrides. Channel mappings are independent and are not changed by this bulk reset. |

Settings concerned with startup or plugin discovery naturally take full effect
on the next launch. Data Browser display and scanner settings, viewer display
settings, and colormap palettes are applied to the open module.

## Application settings

Open Preferences from the Main Workbench for these sections:

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

Select a **File format** on the left before editing its independent settings.
Each table row describes one logical AngstromPro channel:

- **Display name** is the stable name used for the loaded dataset and Data
  Browser card.
- **Load by default** preselects a matched channel in the normal file-open
  dialog. It also determines which channels the Data Browser renders as
  thumbnails.
- **Exact aliases** are semicolon-separated raw channel names. Matching is
  exact and case-sensitive; their order determines which match wins first.
- **Source (.3ds)** distinguishes swept **Channels** from per-pixel
  **Experiment parameters**. Choose the source of a logical row, or **Either**
  when both are possible. This choice is used for file opening and Data Browser
  thumbnails. **Either** prefers a Channel if the exact same alias exists in
  both sources; choose **Experiment parameters** to force the per-pixel map.
  Other formats continue to use their ordinary channel list.
- **Auto-load defaults for this format** is a separate, format-level option.
  It skips the normal selection dialog and loads the matched default rows.

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
Browser always renders matched channels marked **Load by default**. Existing
cached thumbnails are not rewritten merely because mappings changed; use
**Re-render all** or re-render an individual card.

## Module settings

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

The real-time colormap editor provides two distinct save actions. **Save to My
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
copied, and the original folder is retained as a backup. For a standalone
launch, fully exit and launch AngstromPro again. In Spyder, restart the kernel
and launch AngstromPro again; merely reopening the hidden hosted session is
still the same runtime.

While a change is queued, a temporary pending record is stored beside the
OS-managed pointer. After the next session adopts the change, that record is
removed and `datapath.txt` contains only the new absolute path.

Plugin modules whose IDs use a plugin namespace can store settings in separate
files under `config/plugins/`, preventing a plugin from overwriting the main
configuration.

Use the Preferences reset controls carefully: regenerable cache data can be
recreated, but configuration changes may need to be entered again.
