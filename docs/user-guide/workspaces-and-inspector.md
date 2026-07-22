# Workspaces and the Inspector

Workspaces are the common runtime layer connecting AngstromPro modules. Each
live module owns its own workspace, shown in the **Workspace** dock. Open or
hide the dock with **View → Workspace** (`Ctrl+1`).

### Make room for long item names

Workspace item names can be longer than the dock's default width. Drag the
**Workspace** dock by its title bar out of the module window to make it a
floating window, then resize it horizontally to show full names. Floating the
dock also prevents a wide workspace list from reducing the module's central
viewing area. Drag it back to an edge of the module window when you want to dock
it again, and use `Ctrl+1` at any time to show or hide it. This is particularly
useful when comparing several datasets with similar long filenames.

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

- Use **Send…** after selecting an item to pass it to another compatible module.
- Use **Remove** to remove it from the current runtime workspace.
- Expand an item to see its named annotations; an annotation can be cleared
  from its context menu.

Sending moves the item from the source workspace by default. Preferences can
keep the source item as well. Workspaces are runtime containers: save important
results to a supported file before closing the application.

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

Most displayed values are informational. Double-click an array node to open
the array viewer/editor. Right-click an axis node to edit its semantic axis
type. These operations modify the runtime object, so save the result if the
change must persist after the session.
