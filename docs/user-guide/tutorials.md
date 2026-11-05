# Tutorials: working with your measurement data

These tutorials take you from an existing measurement file to an inspected,
processed, and saved result. Use your own topography, spectroscopy, or
spectroscopic-imaging data in a [supported format](file-formats.md#built-in-formats).
Complete [installation](getting-started.md) first.

## Choose a starting point

| Your task | Start here | Result |
| --- | --- | --- |
| Open a known measurement file | [Open and verify a measurement](file-formats.md#tutorial-open-and-verify-a-measurement) | Selected channels in the correct viewer, with axes checked |
| Find a measurement among many files | [Browse and send a measurement](data-browser.md#tutorial-browse-and-send-a-measurement) | A chosen file channel in an analysis module |
| Inspect topography or energy-resolved maps | [Inspect images and their Fourier transforms](image-stack-viewer.md#tutorial-inspect-images-and-their-fourier-transforms) | Real-space and reciprocal-space views with controlled display settings |
| Remove a background | [Run background subtraction](processes.md#tutorial-run-background-subtraction) | A separate processed dataset for comparison |
| Extract a spatial line profile or a sequence of spectra | [Create a line cut](image-stack-viewer.md#tutorial-create-a-line-cut) | A curve-stack result ready for plotting and saving |
| Compare and format spectra | [Compare-and-style workflow](curve-stack-viewer.md#tutorial-compare-and-style-spectra) | An editable multi-curve figure |
| Average a spectroscopy map with error bars | [Average-spectrum workflow](curve-stack-viewer.md#tutorial-plot-an-average-spectrum-with-error-bars) | Spatial mean and its selected error measure |
| Save progress and reopen it | [Save and resume an analysis](workspaces-and-inspector.md#tutorial-save-and-resume-an-analysis) | Native data and a workspace archive |
| Export a figure or layer sequence | [Export instructions](file-formats.md#tutorial-save-data-and-export-results) | Presentation files plus a separate editable data copy |
| Correct a lattice or register two images | [Advanced image-processing workflows](image-processing-workflows.md) | Corrected datasets and checks on the transformation |

For a first image analysis, follow: **open a measurement → inspect the image →
configure a process menu → subtract the background → compare → save/export**.
For point spectra, start with the Curve Stack Viewer instead of the Image Stack
Viewer.

## Before following a procedure

0. Before importing data, open the Main Workbench's **Preferences… → Channels**
   and check the mappings for the relevant file format. On Windows, use
   **File → Preferences…**; on macOS, use the application menu, which may be
   labelled **Python**. **Exact aliases** must match the acquisition-channel
   names recorded in your files, while **Display name** is the label used in
   AngstromPro. For the default `.3ds` dI/dV mapping, an alias is
   `LI Demod 1 X (A)`; add your own acquisition name if it differs. Separate
   alternative names with semicolons and apply the changes. If expected
   channels are missing, consult [channel mapping instructions](preferences.md#tutorial-configure-a-measurement-channel).
   Data Browser's **Channels** preferences edit these same shared mappings.
1. In the **Main Workbench**, click the **+ New Module** button, open **Basic**,
   and select **Data Browser**, **Image Stack Viewer**, or **Curve Stack Viewer**.
   For an existing instance, click **Show** on its module card.
2. In the module, show **View → Workspace** and **View → Inspector**.
3. Open the file with **File → Open…** in the viewer, or right-click a data
   thumbnail in Data Browser and choose **Send to module…**.
4. Double-click the intended workspace item to activate it. Merely opening a
   file or highlighting a row does not necessarily display it.
5. Check the displayed item name and **Active Processing Slots** below the
   Workspace list before each operation. Assign a compatible reference as
   well when the algorithm needs two inputs; see [Run a process](processes.md#run-a-process).
6. In the viewer, open **Process → Configure Process Menu…** to choose the
   data-processing algorithms you need and organise them into custom submenus.
   Save the configuration, then select an algorithm through **Process → your
   configured submenu → operation**. In the dialog that opens, check **Inputs**
   and **Annotations** where applicable, edit the parameter fields, and click
   the **Run** button at the bottom to start processing.

Each tutorial specifies its input, numbered steps, expected result, and checks
to make when that result does not appear. Interface labels are shown in **bold**.
Names such as `topography_raw` are suggested aliases, not supplied datasets.
Tutorial submenu names such as **Basic analysis** are created by you; they are
not assumed to exist in a fresh installation. **Process → Process Browser…**
only displays information about algorithms; it does not run them.

## How to find controls and use the mouse

Menu paths such as **File → Open…** start in the menu bar of the window named
in the step. On macOS, bring that window to the front before using the system
menu bar; **Preferences…** is in the application menu. An arrow into a
Preferences section means open the Preferences dialog and find that section
inside it, not another menu-bar submenu.

- **Buttons and fields:** single left-click a button, checkbox, tab, or list
  entry. For a dropdown, click it and select a value. Parameter names refer
  to fields in the dialog or panel identified by the procedure.
- **Workspace items:** single-click selects an item for inspection, saving,
  sending, or removal. Double-click activates it in the current viewer.
  Right-click the item for its context menu, including **Set alias…**.
- **Data Browser thumbnails:** right-click the image/card for **Send to
  module…**, **Set thumbnail layer…**, **Rating**, and **Re-render thumbnail**.
  These are not File-menu commands.
- **Image-viewer canvas:** right-click to pick a point. Single-click a
  point-list entry before clicking
  **Remove Point**. Save process annotations using the viewer's **Points** menu.
- **Tree rows:** click the small disclosure arrow beside a row to expand its
  children. Clicking a checkbox changes visibility or selection for that
  control; it is not the same as double-clicking a workspace dataset.
- **Docked panels:** open **View → Workspace** or **View → Inspector**.
  They can appear separately, float, or share one tabbed area. Use the
  **Workspace** / **Inspector** tabs at the bottom when they share an area.
  Drag a panel's title bar to float or redock it.

## Four distinctions that prevent common mistakes

| Distinction | What to do |
| --- | --- |
| Selected row versus process input | Single-click selects the target for saving/sending; double-click activates an input. Check **Active Processing Slots** before running a process. |
| File channel versus file | One acquisition file can produce several independent workspace items. Confirm the channel, units, and axes, not just the filename. |
| Display setting versus analysis | Changing a colour range, plot offset, or preview does not create processed data. Run a registered process to create a result with processing history. |
| Saved data versus exported figure | Save `.uds`, `.scplot`, or `.apws` for later analysis; export images or figures for presentation. |

The procedures describe the current application. The accompanying software
article provides the architectural background: separate module workspaces,
explicit process inputs, and separate data-saving and figure-export workflows.
