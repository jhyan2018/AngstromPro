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

**AngstromPro requires Python 3.10 or newer. Python 3.9 is not supported.**
AngstromPro works with plain Python and with IDEs such as Spyder, Visual Studio,
and VS Code. The IDE name does not decide which packages are available: its
selected Python environment does. Anaconda/Spyder environments commonly
already contain PyQt5, while a Visual Studio or VS Code project may select an
environment containing PyQt6 or no Qt binding at all. This is why both Python
and Qt must be checked first.

Run these checks in PowerShell, Command Prompt, or a macOS/Linux terminal before
installing:

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -c "import importlib.util as u; print([n for n in ('PyQt6','PyQt5','PySide6') if u.find_spec(n)])"
```

If Python is 3.10 or newer and the check lists exactly one binding, use the
simplest installation: clone the repository and install AngstromPro without a
Qt extra. It will use the binding already present:

```powershell
git clone https://github.com/jhyan2018/AngstromPro.git
cd AngstromPro
python -m pip install .
```

If Python is 3.10 or newer and no binding is listed, use the same steps but
choose exactly one supported Qt extra. For example:

```powershell
git clone https://github.com/jhyan2018/AngstromPro.git
cd AngstromPro
python -m pip install ".[pyqt5]"
```

PyQt6 and PySide6 are equally supported alternatives; replace `pyqt5` with
`pyqt6` or `pyside6`. Do not install more than one Qt extra.

If multiple bindings are listed, do not install another one. First use the
no-extra installation (`python -m pip install .`): AngstromPro prefers the
binding already loaded by an IDE such as Spyder. Create a clean environment
when Python is older than 3.10 or when the existing environment produces Qt
loading, DLL, or platform-plugin errors. With Conda:

```powershell
conda create -n angstrompro python=3.12 pip
conda activate angstrompro
git clone https://github.com/jhyan2018/AngstromPro.git
cd AngstromPro
python -m pip install ".[pyqt5]"
```

Without Conda, create a standard virtual environment using an installed Python
3.12, activate it, and run the same installation command:

```powershell
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install ".[pyqt5]"
```

This no-extra installation is normally the simplest choice for a compatible
Spyder environment that already uses PyQt5. Optional scikit-image features can
be installed without changing its Qt binding using
`python -m pip install ".[full]"`.

The README recommends `python -m pip install .` for normal use. Developers who
intend to edit the checkout should use `python -m pip install -e .` instead;
editable mode runs from the working source tree, so code changes are available
without reinstalling. Both forms install the same dependencies and
`angstrompro` launcher.

For Conda, standard-Python, Spyder, Visual Studio, and VS Code instructions, see
[Getting started](docs/user-guide/getting-started.md).

## Quick start

Launch AngstromPro from an activated Python environment:

```powershell
angstrompro
```

When launched from a Spyder IPython console, AngstromPro shares Spyder's Qt
event loop. Closing the Main Workbench therefore hides the current AngstromPro
session; launching it again in the same console reopens that session. Restart
the Spyder kernel after changing AngstromPro or plugin source code so the next
launch imports the revised classes. A standalone `angstrompro` process exits
normally when its Main Workbench is closed.

On first launch, AngstromPro asks you to choose a parent location and creates
an `angstrompro-user/` folder beneath it. Configuration, interface settings,
thumbnail caches, and logs stay inside that dedicated folder. By default, the
application opens the **Data Browser**, **Image Stack Viewer**, and **Curve
Stack Viewer**.

A useful first workflow does not require measurement files:

1. In the Main Workbench, choose **+ New Module → Planewave Synthesiser**.
2. Add one or more wavevectors and adjust their amplitudes and phases.
3. Choose **Save to workspace** to create a synthetic image stack.
4. Single-click the new workspace row to select it, choose **Send…**, and send
   it to the **Image Stack Viewer** to try compatible processes.

When working with experimental data, the typical workflow is:

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

### Planewave Synthesiser

The Planewave Synthesiser constructs a two-dimensional real-space image from a
sum of plane waves:

$$
f(x,y) = \sum_j A_j \cos\!\left(
2\pi\frac{q_{x_j}X + q_{y_j}Y}{\mathrm{size}} - \varphi_j
\right)
$$

Add or remove wave components, adjust their wavevectors, amplitudes, and phases,
then save the live result to the workspace. Because it generates its own data,
this is the recommended first module for learning workspace sending, the Image
Stack Viewer, and compatible processes without needing a measurement file.

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
