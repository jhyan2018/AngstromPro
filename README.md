# AngstromPro

AngstromPro is a desktop application for analysing scanning probe microscopy and
spectroscopy data. It provides one interface for browsing measurement folders,
visualising image and curve stacks, running analysis processes, and exporting
publication-ready figures.

The physics and mathematics behind the analysis algorithms are described in the
accompanying paper: <https://arxiv.org/abs/2604.18962>

If you use AngstromPro in published research, please cite the accompanying
paper. This reference will be updated with the journal citation and DOI after
publication.

## Installation

AngstromPro requires Python 3.10 or newer. Clone this repository, enter its root
directory, and install the application with a Qt binding:

```powershell
git clone https://github.com/jhyan2018/AngstromPro.git
cd AngstromPro
python -m pip install ".[pyqt6]"
```

Alternative Qt bindings and optional scientific features are available as
installation extras. The AngstromPro light and dark themes are bundled with
the application and require no additional package:

```powershell
# For an environment that already uses PyQt5, such as some Spyder installations
python -m pip install ".[pyqt5]"

# Use PySide6 instead of PyQt
python -m pip install ".[pyside6]"

# Include optional scientific features provided by scikit-image
python -m pip install ".[pyqt6,full]"
```

Only one Qt binding is needed.

The commands above are for PowerShell, Command Prompt, or another system
terminal. If the repository is already the working directory in a Spyder
IPython console, use IPython's `%pip` command instead, for example:

```python
%pip install ".[pyqt5]"
```

The same substitution works for the other extras. Do not enter
`python -m pip ...` at the `In [ ]:` prompt; that syntax launches Python from a
system terminal, while `%pip` targets the active IPython environment directly.

## Quick start

Launch AngstromPro from an activated Python environment:

```powershell
angstrompro
```

On first launch, AngstromPro asks you to choose a user-data folder. It stores
configuration, interface settings, thumbnail caches, and logs beneath that
folder. By default, the application opens the **Data Browser**, **Image Stack
Viewer**, and **Curve Stack Viewer**.

A typical workflow is:

1. **Browse** a measurement folder and filter or sort its files.
2. **Send** a file to an appropriate viewer.
3. **Process** the data using the viewer's analysis menus.
4. **Save** results or export figures for later use.

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
a complete plot hierarchy whose artists may wrap UDS datasets. Select an item
and open **View → Inspector** (`Ctrl+2`) to examine the fields exposed by its
payload type.

See [Workspaces and the Inspector](docs/user-guide/workspaces-and-inspector.md)
for users and [Runtime data and workspaces](docs/developer-guide/workspaces.md)
for extension authors.

## Built-in modules

### Data Browser

The Data Browser displays files from configured watch folders as a thumbnail
gallery.

- Browse folders directly or include their subfolders.
- Filter by filename and format, then sort the visible files.
- Assign ratings from zero to five stars.
- Choose the data layer used to render thumbnails.
- Re-render thumbnails when display settings change.
- Send supported files to open analysis modules.
- The background scanner pre-renders and caches thumbnails for files in your
  watch folders, making later browsing faster. In **Preferences → Data Browser**,
  you can disable scanning, choose which formats it scans, set the scan order,
  and adjust the delay between render requests and full passes.

### Image Stack Viewer

The Image Stack Viewer displays three-dimensional datasets, such as
energy-resolved maps, using side-by-side **Primary** and **Reference** panels.

- Move through layers while viewing their physical-axis values.
- Adjust colour limits and switch between real, imaginary, magnitude, and phase
  representations of complex data.
- Edit the Primary or Reference colormap in real time.
- Pick points on an image for use by analysis processes.
- Synchronise layers, picked points, cursors, and field-of-view zoom between the
  two panels.
- Run compatible processes and pass their results to other modules.

### Curve Stack Viewer

The Curve Stack Viewer plots two-dimensional spectroscopy and line-scan data as
curve stacks.

- Load a workspace item as the primary dataset or overlay it on the current
  figure.
- Assign a reference dataset for processes that require two inputs.
- Edit curve styles, axes, limits, scales, labels, and grids.
- Use **Scene → Save as Scene…** to save the complete plot as a `.scplot` file.
- Use `.scet` style templates to apply consistent presentation settings to new
  plots.

### Planewave Synthesiser

The Planewave Synthesiser constructs a two-dimensional real-space image from a
sum of plane waves:

$$
f(x,y) = \sum_j A_j \cos\!\left(
2\pi\frac{q_{x_j}X + q_{y_j}Y}{\mathrm{size}} - \varphi_j
\right)
$$

Add or remove wave components, adjust their wavevectors, amplitudes, and phases,
and send the live result to the workspace for visualisation or further
processing.

## Processes

Processes are registered analysis operations that act on data in a module's
workspace. Compatible processes can be run from that module's **Process** menu;
AngstromPro asks for any required inputs and parameters, runs the work in the
background, and adds the result to the workspace. Previously used parameter
values are remembered for later runs.

Each module also provides two tools in its **Process** menu:

- **Process Browser…** (`Ctrl+B`) lists every registered process. Search by
  name, label, or category, then inspect its description, required inputs,
  outputs, and parameters.
- **Configure Process Menu…** adds registered processes to a module's menu and
  controls the order of user-added entries. Processes supplied in the module's
  default menu remain visible as read-only defaults.

## Supported file formats

The built-in input/output registry currently includes:

| Format | Read | Write | Description |
| --- | :---: | :---: | --- |
| `.uds` | Yes | Yes | Native scientific data; legacy UDS files can be imported and upgraded |
| `.scplot` | Yes | Yes | Saved plot scene |
| `.npy` | Yes | Yes | NumPy array |
| `.sxm` | Yes | No | Nanonis map |
| `.3ds` | Yes | No | Nanonis grid spectroscopy |
| `.dat` | Yes | No | Nanonis point spectroscopy |
| `.1fl` | Yes | No | LF dI/dV map |
| `.tfr` | Yes | No | LF topography map |
| `.mat` | Yes | No | MATLAB data |
| `.txt` | Yes | No | Whitespace-delimited numeric data |

Open **Help → Supported Formats…** in AngstromPro for the formats registered at
runtime, including formats supplied by plugins.

## Extending AngstromPro

### Modules and processes

AngstromPro discovers built-in and third-party GUI modules through its module
registry. A module is registered by subclassing `AGuiModule` and applying the
`register_module` decorator:

```python
from angstrompro.core.modules import AGuiModule, register_module


@register_module
class MyModule(AGuiModule):
    module_id = "my_module"
    display_name = "My Module"
    category = "Analysis"
```

Import the module before `AppContext` is created so that it appears in the
Modules menu. Analysis operations use the `register_process` decorator and a
`ProcessSchema` describing their inputs, outputs, and parameters. Once their
module is imported, registered processes appear in the Process Browser and can
be added to compatible module menus.

### Plugins

Plugins can contribute processes, GUI modules, and file-format handlers without
modifying AngstromPro itself. There are two supported loading mechanisms:

- For local development, add the plugin's `src/` folder and importable module
  name under **Preferences → Plugins**. The plugin is loaded on the next launch.
- For installed packages, expose the plugin through the `angstrompro.plugins`
  Python package entry-point group.

Plugins load before the process registry is created, allowing their decorated
components to be discovered during startup. A plugin can also keep its settings
in an isolated configuration file rather than modifying AngstromPro's main
configuration.

## License

AngstromPro is free software licensed under the
[GNU General Public License v3.0 or later](LICENSE). Commercial use is permitted
under the GPL provided its terms are followed.

## Feedback

Please report bugs or send feedback to
[huiyuzhao.tju@gmail.com](mailto:huiyuzhao.tju@gmail.com) or
[jhyan2018@gmail.com](mailto:jhyan2018@gmail.com).
