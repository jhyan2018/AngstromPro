# Workspaces and the Inspector

Workspaces are the common runtime layer connecting AngstromPro modules. Each
live module has a private workspace, shown in the **Workspace** dock, and can
also attach to one application-level shared workspace. Open or hide the dock
with **View → Workspace** (`Ctrl+1`).

## Open and switch panels

In the module being used, choose **View → Workspace** and **View → Inspector**.
Depending on the saved layout, these dockable panels may be separate, floating,
or stacked in one tabbed area. If stacked, click **Workspace** or **Inspector**
at the bottom to show that panel. Single-click a dataset in Workspace before
switching to Inspector; return to Workspace to double-click and display it.

The **Remove** and **Send…** buttons are directly below the Workspace item
list. **Active Processing Slots**, below those buttons in modules that provide
input slots, shows the items that will be used by processes. It is not a menu.

### Make room for long item names

Workspace item names can be longer than the dock's default width. Drag the
**Workspace** dock by its title bar out of the module window to make it a
floating window, then resize it horizontally to show full names. Floating the
dock also prevents a wide workspace list from reducing the module's central
viewing area. Drag it back to an edge of the module window when you want to dock
it again, and use `Ctrl+1` at any time to show or hide it. This is particularly
useful when comparing several datasets with similar long filenames.

## Private and shared workspaces

Use **Workspace → Shared Workspace Manager…** in the Main Workbench to create,
rename, or delete shared workspaces and configure module attachments. The app
can own any number of shared workspaces, while each module instance can attach
to at most one of them. The manager can also save a selected shared workspace
or import a `.apws` archive as a new shared workspace, including when no module
is attached.

An attached module continues to show and access its private items. Its
Workspace dock displays separate **Private workspace** and **Shared** sections,
with radio buttons beside the headings. Select one as the **active destination**
for incoming items, newly opened data, and new process or simulation outputs.
Shared is selected on first attachment; you can select Private without
detaching. The choice is independent for each module instance, and switching it
does not move existing data or change input slots. A running process retains
the destination chosen when it was submitted. Operations
on an existing item, such as removing it or changing its annotations, still
apply to the workspace that owns that item. Detaching returns new output to the
private workspace; it does not delete either collection.

Process input slots remain local to each module and can refer to items from
either visible section. Shared workspaces persist at application level even
when no module is attached, until they are explicitly deleted.

## Workspace items

Every row in a workspace is a `WorkspaceItem`. The item provides runtime
identity and transport information around a data payload:

- A stable item identity and display name
- The source file path, when the item came from disk
- A payload type ID used for module and process compatibility
- Named annotations such as points, lines, and regions
- The payload itself

The payload is not restricted to one scientific array format. Any data type
that follows AngstromPro's runtime-data contract can be placed in a workspace.
This is what allows future modules to introduce structures, lattices, scenes,
tables, or other domain objects without replacing the workspace system.

Common payloads include:

- `UdsDataStru`: an elementary scientific array with axes, metadata, and
  processing history.
- `ScenePlot`: a composite plot scene containing figure and axes settings,
  artist descriptions, styles, and UDS data used by its artists.

`ScenePlot` should not be confused with a `.scet` scene template. A scene is a
runtime data payload and can be inspected, sent, saved, and reopened with its
datasets intact. A template is a reusable, data-free rendering style used when
the Curve Stack Viewer or Data Browser turns raw UDS data into a new plot or
thumbnail.

## Using a workspace

Mouse actions have different purposes:

| Action | Result |
| --- | --- |
| **Single left-click** | Selects and highlights the item. The Inspector follows this selection, and **Send…** and **Remove** operate on the selected item. Always single-click the intended row before sending it. |
| **Double left-click** | Asks the current module to load or activate the item as an input. It does not send the item to another module. |
| **Right-click** | Opens the actions available for that item in the current module, such as adding data to a plot. Right-clicking a named annotation provides its annotation actions, such as **Clear**. |

- Single-click an item, then click **Send…** below the Workspace list.
  In the destination dialog, single-click a module and click **OK**, or
  double-click the destination to confirm.
- Single-click an item and click the **Remove** button below the list to remove it from the current runtime workspace.
- Right-click an item and choose **Set alias…** to give it a shorter display
  label. The alias does not change the item's real workspace name or processing
  identity. Automatically named process outputs reuse this alias and append
  their normal result suffix. If you set a new alias on an output, later
  outputs continue from that shorter alias. Right-click the same item and choose **Clear alias** to show the real
  name again.
- Expand an item to see its named annotations; an annotation can be cleared
  from its context menu.

Sending moves the item from the source workspace by default. Preferences can
keep the source item as well. Send uses the receiving module's active
destination, shown in the target picker. No copy is made if that destination
already owns the selected item. Both modules may remain attached to the same
shared workspace while receiving new items in their own private workspaces.

Use **File → Save…** to save one selected item in its native format. Opening
that HDF5 file again restores its alias, item identity, and named annotations
as well as its data. This also works for installed plugin formats that write
HDF5 files. When an alias is set, the Save dialog suggests it as the filename;
the item's real name is unchanged. Older native files without item metadata
still open with empty alias and annotations. If the item's name or identity is
already present, AngstromPro keeps the existing item and gives the imported
one a distinct name or identity.

Use **File → Save Workspace…** to store all supported items in one `.apws` HDF5
archive. When the module is attached, choose either workspace, with the active
destination selected by default; without an attachment, the private
workspace is used directly. **File → Open Workspace…** uses the same choice and
adds the archive items to that workspace. Importing into a shared workspace
requires confirmation because every attached module sees the changes
immediately. If unsupported payload types are
present, AngstromPro lists every skipped item; click **OK** to save the remaining
items.
Existing items are kept, and imported name conflicts are resolved with numeric
suffixes such as `_2` and `_3`. Installed plugins can register their workspace
payload formats. If a required plugin is unavailable when an archive is opened,
AngstromPro skips only those payloads, loads the supported items, and reports
the skipped names, types, and providers.

## Tutorial: save and resume an analysis

**Goal:** retain inputs, processed results, annotations, and editable plots for
a later session.

1. Before processing, single-click each input and inspect its source path,
   shape, axis names, and units in **View → Inspector**. Right-click the
   workspace row and choose **Set alias…**
   for clear labels such as `topography_raw` and `topography_background_removed`.
2. After a process finishes, select its result and inspect the processing
   history. Check the operation and parameters rather than relying only on
   an automatically generated suffix.
3. To retain one dataset, single-click its workspace row and choose **File →
   Save…**. Use `.uds` for numerical data or `.scplot` for a captured plot
   scene. Saving is based on the selected row, not necessarily what is drawn.
4. To retain the collection, choose **File → Save Workspace…** and save a
   `.apws` archive. If the module is attached to a shared workspace, choose
   the shared or private collection explicitly.
5. Review any list of unsupported items before accepting a partial save.
   Data held only in other modules' private workspaces is not included.
6. Open another instance of the appropriate module and choose **File → Open
   Workspace…** to import the archive. Check the expected items and annotations
   in the Workspace and Inspector.
7. Double-click the desired dataset or scene to restore the working view, and
   set the reference input again when needed.

**Expected result:** supported workspace data can be reopened with its axes,
history, aliases, and annotations. A workspace archive is a data collection,
not a full desktop-session snapshot: it does not restore every module window,
its selected input slots, or unsaved plot edits.

If a curve plot must be retained, first create a scene with **Scene → Save as
Scene…**. Saving a workspace of raw curves alone does not capture the current
plot arrangement.

## Tutorial: share data between two modules

**Goal:** let two viewers access the same collection without repeatedly sending
items.

1. Open the two module instances from Main Workbench.
2. In Main Workbench, choose **Workspace → Shared Workspace Manager…**, create
   a named shared workspace, and configure both module attachments.
3. Check each module's Workspace dock: both should show that shared collection
   as **Active output**, alongside any existing private items.
4. Open a measurement or run a process in one attached module. Its new output
   appears in the shared section visible to both modules.
5. In the other module, double-click a compatible shared item to display it.
   Image and curve viewers still enforce their own data requirements.
6. Save the shared collection with **File → Save Workspace…**, selecting the
   shared workspace when prompted.

**Expected result:** both modules access the same data items while their
process-input choices remain independent. Attaching a module does not
automatically move its existing private items into the shared collection.

Changes or removals to shared items affect the shared collection seen by both
modules. Detaching a module does not delete it. A shared workspace's persistence
within the application does not replace saving it to disk.

## Workspace Item Inspector

Open **View → Inspector** or press `Ctrl+2`. Selecting a workspace row updates
the Inspector with:

- Item name, payload type, and source path
- Fields chosen by that payload type
- Nested groups and composite structure
- NumPy array shape, data type, and values
- Scientific axes and their semantic axis types

The Inspector is generic. Each runtime payload describes its own fields, so a
new plugin data type can become inspectable without adding a new Inspector
widget.

Most displayed values are informational. Click disclosure arrows to expand the item and its data fields. Double-click an array node to open
the array viewer/editor. Right-click an axis node to edit its semantic axis
type. These operations modify the runtime object, so save the result if the
change must persist after the session.
