# AngstromPro

AngstromPro is a desktop application for analysing scanning probe microscopy and
spectroscopy data. It provides a unified interface for browsing measurement folders,
visualising image and curve stacks, running analysis processes, and exporting
publication-ready figures.

The physics and mathematics behind the analysis algorithms are described in the
accompanying paper: <https://arxiv.org/abs/2604.18962>

If you use AngstromPro in published research, please cite the accompanying
paper. This reference will be updated with the journal citation and DOI after
publication.

## Installation

AngstromPro requires Python 3.10 or newer and one supported Qt Python binding:
PyQt5, PyQt6, or PySide6.

Before installing, check your Python version, interpreter path, and existing
Qt bindings using the commands in the
[installation guide](docs/user-guide/getting-started.md#check-your-python-environment).
These checks help you install into the intended environment and avoid adding
an unnecessary Qt binding.

The commands below install AngstromPro directly from a GitHub ZIP archive
and automatically install its basic Python dependencies.
They assume that your current Python environment already contains a supported Qt
binding. If none is present, replace `angstrompro` inside the quotation marks
with `angstrompro[pyqt5]` to install PyQt5 as well. You can replace `pyqt5`
with `pyqt6` or `pyside6` to use a different Qt binding; choose only one.

### macOS

Run in Terminal:

```bash
python3 -m pip install "angstrompro @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

See the [detailed macOS instructions](docs/user-guide/getting-started.md#macos).

### Windows

Run in PowerShell, Command Prompt, or Anaconda Prompt:

```powershell
python -m pip install "angstrompro @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

See the [detailed Windows instructions](docs/user-guide/getting-started.md#windows).

### Linux

Run in a terminal:

```bash
python3 -m pip install "angstrompro @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

See the [detailed Linux instructions](docs/user-guide/getting-started.md#linux).

Use the same Python command for the environment checks and installation,
replacing `python3` with `python` where appropriate.

After installation, run `angstrompro` from the same environment.

For installation from a cloned or downloaded source directory, see
[Installing from a local copy](docs/user-guide/getting-started.md#installing-from-a-local-copy).

## Quick start

Launch AngstromPro from the same Python environment used for installation:

```powershell
angstrompro
```

Closing the Main Workbench exits the application. Restart AngstromPro after
changing application or plugin source code to load the revised code.

On first launch, AngstromPro asks you to choose a parent location and creates
an `angstrompro-user/` folder beneath it. Configuration, interface settings,
thumbnail caches, and logs stay inside that dedicated folder. By default, the
application opens the **Data Browser**, **Image Stack Viewer**, and **Curve
Stack Viewer**.

To analyse your own measurements:

0. Before importing data, check the channel mappings in the Main Workbench's
   **Preferences… → Channels** section. On Windows, open **File → Preferences…**;
   on macOS, open **Preferences…** from the application menu, which may be
   labelled **Python**. Select the relevant **File format**, such as
   `nanonis_3ds`, `nanonis_sxm`, or `nanonis_dat`. **Display name** is the label
   used in AngstromPro; **Exact aliases** lists the original channel names to
   match in the measurement file, including any custom name configured in
   Nanonis before acquisition.

   For example, the default `nanonis_3ds` mapping uses **Display name = dI/dV**
   and includes `LI Demod 1 X (A)` among its **Exact aliases**. If your `.3ds`
   file records the dI/dV signal under that name, AngstromPro recognises it
   using this mapping. If you configured a different acquisition-channel
   name, double-click the **Exact aliases** cell and enter that exact name.
   You can enter multiple alternative names separated by semicolons; these
   are alternative matches for the same logical channel, not names to merge.
   Apply the changes before opening the data.

   When first opening your data, review any channel-selection or unmatched-channel
   dialog that appears. If an expected channel is missing or is not loaded as
   intended, return to **Preferences… → Channels** and check its **Exact aliases**
   against the names stored in the source file. Data Browser's **Preferences…**
   also contains a **Channels** section for editing the same application-wide
   mappings, including those used to generate thumbnails.

1. Open a file in **Image Stack Viewer** (maps) or **Curve Stack Viewer**
   (spectra) using **File → Open…** in that viewer, and choose the required
   channels when prompted. Alternatively, locate the desired channel's
   thumbnail in **Data Browser**, right-click the data image, and choose
   **Send to module…** from the context menu. Single-click the destination
   module in the dialog and click **OK** (or double-click the destination).
2. Open **View → Inspector** and single-click a workspace item to check its
   axes and units. Inspector is a
   dockable panel that can also float as a separate window. Depending on the
   current layout, it may appear separately or share a tabbed panel with
   **Workspace**. If they share a panel, use the **Workspace** and **Inspector**
   tabs at the bottom to switch between them. Return to **Workspace** and
   double-click the item to display it.
3. For analysis, use **Process → Configure Process Menu…** to customise the
   **Process** menu: choose which data-processing algorithms appear and
   organise them into submenus of your choice. After saving the configuration,
   the selected algorithms appear under the corresponding submenus in the
   **Process** menu.
   Double-click the intended workspace item to display it. In Image Stack
   Viewer, this loads the data into **Primary**. For data whose name does not
   end in `_fft` and which are not otherwise identified as FFT data, the viewer
   automatically generates the corresponding FFT (or reuses an existing
   associated FFT) and displays it in **Reference Image**.
   Check **Active Processing Slots** below the Workspace list, then select
   the required algorithm from the appropriate submenu in the **Process**
   menu configured above. In its dialog, check **Inputs** and any required
   **Annotations**, adjust the parameters, and click **Run**.
4. After processing is complete, the result appears as a new item in
   **Workspace**. Single-click the result and choose **File → Save…** to
   preserve its numerical data, or save the collection with **File → Save
   Workspace…**.
5. Export images, videos, or figures, and save editable plots as needed:

   - In **Image Stack Viewer**, choose **File → Export Image…** to export
     the displayed image. In the export dialog, choose **Destination = File**
     to save an image file, or **Destination = Clipboard** to copy the image
     for pasting into another application.
   - For multilayer data, such as dI/dV maps acquired at different energies,
     choose **File → Export Video…**. Select the panel to export, the layer
     range, output format, and frame rate. Each layer in the selected range
     becomes one video frame, showing how the image changes across the stack.
   - In **Curve Stack Viewer**, choose **File → Export Figure…** to export
     the plotted figure. To preserve an editable plot, choose **Scene → Save
     as Scene…**, enter a scene name, and confirm. This creates a new scene
     item in **Workspace** containing the plotted data and the plot
     configuration, including line styles, colours, and axis settings.
     Single-click that scene item, choose **File → Save…**, and save it as
     a `.scplot` file. Reopening this file restores the data and configuration
     together for further editing; **Save as Scene…** alone does not write
     the file to disk.

The [step-by-step tutorials](docs/user-guide/tutorials.md) explain
[file and channel loading](docs/user-guide/file-formats.md#tutorial-open-and-verify-a-measurement),
[image/FFT inspection and line cuts](docs/user-guide/image-stack-viewer.md#tutorial-inspect-images-and-their-fourier-transforms),
[background subtraction](docs/user-guide/processes.md#tutorial-run-background-subtraction),
[curve plotting and error bars](docs/user-guide/curve-stack-viewer.md#tutorial-compare-and-style-spectra),
and [saving/exporting results](docs/user-guide/file-formats.md#tutorial-save-data-and-export-results).
For menu paths, panel tabs, and mouse actions, see
[How to find controls and use the mouse](docs/user-guide/tutorials.md#how-to-find-controls-and-use-the-mouse).
For atomically resolved images, see the
[lattice-correction and registration workflows](docs/user-guide/image-processing-workflows.md).

## Documentation

### [Open the User Guide →](docs/README.md#user-guide)

Installation, workflows, modules, processes, file formats, preferences, and
troubleshooting for people using AngstromPro.

### [Open the Developer Guide →](docs/README.md#developer-guide)

Architecture, the data model, modules, processes, plugins, I/O handlers,
configuration, and contributing for people extending AngstromPro.

## Workspaces and runtime data

Each live module owns a **Workspace** containing `WorkspaceItem` objects. A
workspace item can carry any runtime payload that implements the extensible
`WorkspaceData` contract; it is not limited to NumPy arrays or UDS files. This
allows AngstromPro to grow as a platform: new modules can introduce new data
types while retaining the same workspace, sending, processing, and inspection
workflow.

`UdsDataStru` is the elementary scientific array type used by many processes.
Higher-level types can compose elementary data: for example, `ScenePlot` stores
a complete plot hierarchy whose artists may contain one or more UDS datasets. Select an item
and open **View → Inspector** (`Ctrl+2`) to examine the fields exposed by its
payload type.

See [Workspaces and the Inspector](docs/user-guide/workspaces-and-inspector.md)
for users and [Runtime data and workspaces](docs/developer-guide/workspaces.md)
for extension authors.

## Built-in modules

### Planewave Synthesiser

The Planewave Synthesiser constructs a two-dimensional real-space image from a
sum of plane waves:

$$
f(x,y) = \sum_j A_j \cos\!\left(
2\pi\frac{q_{x_j}X + q_{y_j}Y}{\mathrm{size}} - \varphi_j
\right)
$$

Add or remove wave components, adjust their wavevectors, amplitudes, and phases,
then save the live result to the workspace. This optional module helps explore
how wavevectors, amplitudes, and phases produce spatial patterns and provides
synthetic references for analysis.

### Data Browser

The Data Browser provides a thumbnail gallery for exploring measurement files
in configured watch folders, helping you preview measurements, identify data
of interest, and send selected files to analysis modules without opening each
file individually in a viewer.

You can browse a folder on its own or include its subfolders, filter files by
filename and format, and sort the visible results. Ratings from zero to five
stars help mark measurements of interest. For multilayer data, you can choose
which layer appears in the thumbnail and re-render thumbnails when display
settings change.

To analyse a measurement, right-click its thumbnail and choose **Send to
module…**. In the destination dialog, select an open analysis module and click
**OK**, or double-click the destination to send the file directly.

The background scanner pre-renders and caches thumbnails for files in your
watch folders, making later browsing faster. In the Data Browser window, open
**File → Preferences… → Background scanner** to enable or disable scanning,
set the scan order, and adjust the delay between render requests and full
passes. Choose scanned formats in the same dialog's **Watched formats** section.

### Image Stack Viewer

The Image Stack Viewer lets you visualise, compare, and process spatial image
stacks, such as dI/dV maps acquired at different energies. Image readers
represent topographic images and single-energy dI/dV maps as single-layer
stacks: three-dimensional datasets shaped `(1, rows, columns)`. Generic array
files must already have this stack dimension to display as images; see
[data-shape requirements](docs/user-guide/file-formats.md#tutorial-open-and-verify-a-measurement).
The viewer displays data in side-by-side **Primary** and
**Reference Image** panels.

You can move through the layers while reading their physical-axis values,
adjust colour limits, and edit each panel's colormap in real time. For complex
data, the display can switch between real, imaginary, magnitude, and phase
representations. Layers, picked points, cursors, and field-of-view zoom can be
synchronised between the two panels to support direct comparisons.

Right-click the canvas in **Primary** or **Reference Image** to select points.
The **Picked Points** controls to the right of each canvas provide a colour
dropdown for the point markers and a display-mode dropdown with **Points**,
**Lines**, **Circle**, and **Region**. With two points selected, these modes
show the points alone, a connecting line, a circle, or a rectangular region,
respectively. The list below shows the selected point coordinates. To remove
a point, single-click its entry in the list and click **Remove Point**.

After selecting points, use the **Points** menu to assign them to the required
analysis task; choosing a display mode alone does not save an analysis
annotation. In **Primary**, use **Points → Cut → Set Line Cut from Primary**
for a line cut, **Points → Set Mask Center from Primary** for a mask centre,
or **Points → Set Interest Region from Primary** for a region of interest.
When **Reference Image** displays the FFT of the Primary data, select the
required peaks there and choose **Points → Set Bragg Peaks from Reference**,
**Points → Set Filter Points from Reference**, or **Points → Set Lock-in Peak
from Reference**, as appropriate.

Data-processing operations use the data displayed in **Primary** as their
first input; two-input operations also use the staged reference. In the
real-space/FFT workflow above, points assigned through the **Points** menu
are stored as annotations beneath the Primary data item in **Workspace**.
When **Reference Image** displays the FFT of the current Primary data,
select Bragg or lock-in peaks on that
FFT and use **Points → Set Bragg Peaks from Reference** or **Points → Set
Lock-in Peak from Reference**. The saved peak information appears beneath
the current **Primary** data item in **Workspace**, not beneath the FFT item:
these peaks provide the reciprocal-space coordinates needed to process the
Primary data. Expand the Primary data item to inspect the saved annotations.
Setting the same annotation type again replaces its
previous values. Moving or removing points on the canvas does not update an
already saved annotation: use the appropriate **Points** menu command again
to save the revised selection.

Run compatible algorithms from the **Process** menu, inspect the resulting
workspace items, and send results to other modules for further analysis.
Use **File → Export Image…** to save or
copy an image, or **File → Export Video…** to export a sequence of layers as
video frames.

### Curve Stack Viewer

The Curve Stack Viewer lets you visualise and compare spectroscopy and
line-scan datasets as curve stacks. A one-dimensional spectrum acquired at a
single point is displayed as a single-curve stack, conceptually shaped
`(1, points)`. The viewer also accepts a one-dimensional array directly;
displaying it does not convert the stored data into a two-dimensional stack.
The viewer lets you prepare styled figures for presentation while preserving
an editable version of the plot.

Double-click a workspace item to display it as the primary dataset, or
right-click another item and choose **Add to plot** to overlay it on the
current figure. For processes that require two inputs, assign a reference
dataset through the workspace item's **Set as Reference** context-menu option.
Curve styles and colours, axis limits and scales, labels, and grids can be
adjusted to make comparisons clearer.

Open the corresponding dock panels through **View → Curve Style** and
**View → Axes**. If the item is not yet plotted, double-click it in
**Workspace** to start a new plot, or use **Add to plot** to preserve the
current figure and add it. In the **Datasets / Curves** panel,
click the triangle beside the dataset to expand its curve list, then
single-click the curve you want to edit. Adjust its line style, colour, and
other appearance settings in **Curve Style**; use **Axes** to adjust the
plot's axis limits, scales, labels, and grids. Axis settings apply to the
axes shared by the plotted curves, rather than only to the selected curve.
If the two docks share a panel, click the **Curve Style** or **Axes** tab to
switch between them.

To preserve the plotted data together with their styling and axis settings,
choose **Scene → Save as Scene…** to create a scene item in **Workspace**,
then select that item and use **File → Save…** to write a `.scplot` file.
For consistent styling across different measurements, save a `.scet` template
through **Scene → Save Template…** and apply it through **Scene → Load
Template**. Use **File → Export Figure…** to produce a presentation copy
of the figure.

## Preferences

Open **File → Preferences…** (`Ctrl+,`) in the window whose settings you want
to edit. The Main Workbench exposes application-wide settings; each module
window exposes preferences for that module type. **Apply** changes the current
session, while **Save as default** also stores the values for future instances
and later sessions. See the complete
[Preferences guide](docs/user-guide/preferences.md).

For multichannel `.3ds`, `.sxm`, and `.dat` files, open **Preferences… → Channels**
and select the relevant **File format**, as described in Quick start, step 0.
In the channel table, **Display name** is the label used in AngstromPro, while
**Exact aliases** contains the original channel names stored in your measurement
files. If you used custom channel names during acquisition, enter those names
here; separate multiple alternative names with semicolons.

**Load by default** is a checkbox for each channel in this table. When checked,
a matching channel is preselected in the file-opening dialog and included when
Data Browser generates thumbnails. It does not, by itself, skip the
channel-selection dialog.

You can check **Load by default** for multiple channels within the same file
format; it is not limited to one channel. All matching checked channels are
preselected when you open a file of that format. If **Auto-load defaults for
this format** is enabled, those channels load together automatically from
the same file.

The separate **Auto-load defaults for this format (skip selection dialog)**
checkbox above the table applies to the selected file format. Enable it to load
matched default channels without showing the normal selection dialog. If a
default channel cannot be matched, AngstromPro opens a mapping dialog so you
can select the corresponding channel from the file. If expected channels are
missing, check their **Exact aliases** against the names stored in the source
file. The **Channels** section in Data Browser’s preferences edits the same
application-wide mappings.

## Processes

Processes are registered analysis operations that act on data in a module's
workspace. Compatible processes can be run from that module's **Process** menu.
Activate the required input data before selecting an operation, then review
its inputs and parameters in the dialog. AngstromPro runs the work in the
background and adds the result to the workspace. Previously used parameter
values are remembered for later runs.

Each module also provides two tools in its **Process** menu:

- **Process → Process Browser…** (`Ctrl+B`) lists every registered process. Search by
  name, label, or category, then inspect its description, required inputs,
  outputs, and parameters.
- **Process → Configure Process Menu…** creates user-named submenus, adds or removes
  registered processes, and controls the order of both submenus and entries.
  A new layout starts empty; every registered process can still be inspected
  through **Process → Process Browser…**.

## Supported file formats

The built-in input/output registry currently includes:

| Format | Read | Write | Description |
| --- | :---: | :---: | --- |
| `.uds` | Yes | Yes | Native scientific data; legacy UDS files can be imported and upgraded |
| `.scplot` | Yes | Yes | Saved plot scene |
| `.npy` | Yes | Low-level API only | NumPy array |
| `.sxm` | Yes | No | Nanonis map |
| `.3ds` | Yes | No | Nanonis grid spectroscopy |
| `.dat` | Yes | No | Nanonis point spectroscopy |
| `.1fl` | Yes | No | LF dI/dV map |
| `.tfr` | Yes | No | LF topography map |
| `.mat` | Yes | No | MATLAB data |
| `.txt` | Yes | No | Whitespace-delimited numeric data |

NumPy writing is available through the low-level API, not the viewer's
**File → Save…** command. Save scientific datasets as `.uds` from the interface;
see [File I/O](docs/user-guide/file-formats.md#built-in-formats) for details.

In the **Main Workbench**, open **Help → Supported Formats…** for the formats
registered at runtime, including formats supplied by plugins.

## Extending AngstromPro

Working extension examples are provided in `AngstromPro/examples/`. Start with
the [example plugin](examples/example_plugin/README.md), which demonstrates a
GUI module, a process, a simulation, and a read-only file loader. The
[Developer Guide](docs/README.md#developer-guide) explains their interfaces
and how they fit into the application architecture.

AngstromPro separates extension components from the mechanism used to load
them. GUI modules provide interactive tools, processes provide analysis
algorithms, and file-format handlers provide data import or export support.
A plugin packages one or more of these components for loading without changes
to AngstromPro's source code. The following sections describe the components
first, then explain how to organise and load them as a plugin.

### Modules and processes

A GUI module provides a window for a particular visualisation or analysis
workflow. Subclass `AGuiModule` and apply `register_module` to register it.
The base class supplies standard menus, Workspace and Inspector panels,
data sending, preferences, and background-task result handling. Implement
`build_ui()` to create the module's interface and `on_item_loaded()` to respond
when a workspace item is activated:

```python
from angstrompro.core.modules import AGuiModule, register_module
from angstrompro.utils.qt_compat import QtWidgets


@register_module
class MyModule(AGuiModule):
    module_id = "example.my_module"
    display_name = "My Module"
    category = "Analysis"
    accepted_types = {"uds"}
    accepted_ndim = 3

    def build_ui(self):
        self.setCentralWidget(QtWidgets.QLabel("Select an image stack."))

    def on_item_loaded(self, item):
        self.process_inputs = [item]
```

Here, `accepted_types` and `accepted_ndim` declare the supported data, while
`process_inputs` identifies the workspace items staged for processing. Use
stable, namespaced IDs to avoid collisions with other extensions. Import the
registration code during application startup, normally through a plugin,
so the module appears under **+ New Module → Analysis → My Module**.

A process adds an algorithm without requiring a new GUI module. Decorate its
Python function with `register_process` and provide a `ProcessSchema` containing
`InputSpec`, `OutputSpec`, and `ParameterSpec` declarations. These describe the
accepted inputs, returned data, and user-adjustable parameters; annotation
requirements can also be declared for operations that use selected points or
regions. The function receives the resolved inputs and parameters and should
return a result without modifying the input data in place.

Registration takes effect only when the Python module containing the decorated
classes or functions is imported. If this code is already imported during
AngstromPro startup, no additional plugin configuration is required. For code
stored separately, use one of the plugin-loading methods described below to
make it available at startup. Plugin loading imports the code so its
registration runs; it is not a second registration step.

Registered algorithms can be inspected through **Process → Process Browser…**
and added to a compatible module's menu through **Process → Configure Process
Menu…**. Registration does not automatically create a user-defined submenu.
Custom module buttons should use `submit_process()` to run registered
operations through the task system and return results to the workspace,
rather than performing lengthy calculations directly in the interface thread.
Use `register_simulation` for data generators exposed through **Simulate**.

The repository's [examples/example_plugin/](examples/example_plugin/README.md)
directory contains working examples: [module.py](examples/example_plugin/src/angstrompro_example/module.py)
implements a GUI module, and [processes.py](examples/example_plugin/src/angstrompro_example/processes.py)
implements an image-stack scaling process and a simulation. These demonstrate
input selection, parameter handling, and task-backed execution together.
See the developer guides for [GUI modules](docs/developer-guide/modules.md),
[processes](docs/developer-guide/processes.md), and
[background execution](docs/developer-guide/tasks.md) for further details.

### Plugins

Plugins organise extension components into importable Python packages. A
plugin can supply only an algorithm, or combine processes, GUI modules, and
file-format handlers. Its entry module should import the files containing the
registration decorators so that all components are discovered at startup;
it should not open windows or start a separate Qt event loop during import.
There are two supported loading mechanisms:

- For local development, open the Main Workbench's **Preferences… → Plugins**,
  click **Add plugin**, and enter the absolute path to the plugin's `src/`
  folder and its importable module name. For the supplied example, use
  `<repository>/examples/example_plugin/src` and `angstrompro_example`.
  Click **Save as default** and restart AngstromPro.
- For installed packages, expose the plugin through the `angstrompro.plugins`
  Python package entry-point group in `pyproject.toml`. Install the package in
  the same Python environment as AngstromPro and restart the application;
  no source-path preference is needed.

For example, with AngstromPro already installed, run the following from the
repository root to install the supplied plugin in editable mode:

```bash
python -m pip install -e "examples/example_plugin"
```

After restarting, open **+ New Module → Examples → Example Workflow**. The
example also includes a read-only `.apdemo` loader and the package entry-point
configuration. Choose either source-path loading or package installation;
there is no need to configure both. Restart AngstromPro after changing plugin
code so that the revised modules are imported.

Plugins load before the process registry is constructed. Keep component IDs
stable and namespaced, and use `context.get_plugin_config("example")` for
isolated plugin settings rather than editing AngstromPro's main configuration.
See the [example plugin instructions](examples/example_plugin/README.md),
[plugin development guide](docs/developer-guide/plugins.md), and
[file-format handler guide](docs/developer-guide/io-handlers.md) for packaging,
configuration, and additional extension interfaces.

## License

AngstromPro is free software licensed under the
[GNU General Public License v3.0 or later](LICENSE). Commercial use is permitted
under the GPL provided its terms are followed.

## Feedback

Please report bugs or send feedback to
[huiyuzhao.tju@gmail.com](mailto:huiyuzhao.tju@gmail.com) or
[jhyan2018@gmail.com](mailto:jhyan2018@gmail.com).
