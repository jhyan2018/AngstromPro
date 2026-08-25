# Processes

Processes are registered analysis operations. A process declares the data it
accepts, any annotations it needs, its parameters, and the result it produces.
AngstromPro uses this information to present the correct dialog and to avoid
offering incompatible operations where possible.

## Run a process

1. Load or select the required workspace data.
2. Choose an operation from the module's **Process** menu.
3. Supply any additional inputs and parameters requested by the dialog.
4. Start the process.

Long-running operations execute through the task system so the interface can
remain responsive. Successful results are added to the module workspace and
record their processing history. Parameter values are remembered for later
runs.

Some operations need annotations such as picked points, a region, or reference
points. In the Image Stack Viewer, create these from the **Points** menu before
running the process.

## Process Browser

Open **Process → Process Browser…** or press `Ctrl+B` to inspect every
registered process. The browser can filter by name, label, or category and
shows:

- Process ID and description
- Required input ports and dimensionality
- Output types
- Parameters, defaults, ranges, and units

The naming convention uses `_1D` for operations on curve stacks (`ndim=2`) and
`_2D` for operations on image stacks (`ndim=3`). Verify axis orientation in the
item inspector before processing unfamiliar data.

## Process categories

Each registered process has a developer-provided category used for searching
and browsing. Categories do not determine the submenus shown under
**Process**. Those submenu names and contents are entirely user-defined.

## Configure a module menu

Use **Process → Configure Process Menu…** to build the Process submenus for a
particular module. A new layout starts empty; until a submenu is created, the
Process menu contains only **Process Browser…** and
**Configure Process Menu…**.

1. Select the target module type.
2. Create and name one or more submenus.
3. Add compatible processes to the selected submenu.
4. Rename, delete, or reorder submenus and processes as needed.
5. Use **Move to…** to move selected processes between submenus.
6. Save the configuration.

Removing a process from this tree only removes its shortcut from the module
menu. The process remains registered and available through Process Browser.

## Simulations

Registered simulations appear in the **Simulate** menu. Unlike normal
processes, a simulation may generate data without an input dataset.
