# Getting started

## Installation overview

AngstromPro requires Python 3.10 or newer and a supported Qt Python binding:
PyQt5, PyQt6, or PySide6.

Use your current Python environment if it meets these requirements, or an
environment managed by Conda or another tool. Run the installation commands
and launch AngstromPro from a system terminal, not a Python console.

The instructions below install directly from a GitHub ZIP archive; Git and
manual downloading or extraction are not required. To install from a cloned
or downloaded source directory instead, see
[Installing from a local copy](#installing-from-a-local-copy).

## Check your Python environment

A computer can contain several Python installations, and some environments
already contain a supported Qt binding. Check the interpreter that will be
used to install and run AngstromPro.

Before installing, run these commands in the terminal for your intended
environment:

```text
python --version
python -c "import sys; print(sys.executable)"
python -c "import importlib.util as u; print([n for n in ('PyQt6','PyQt5','PySide6') if u.find_spec(n)])"
```

On macOS or Linux, use `python3` instead of `python` if that is the command
for your intended interpreter. In an activated Conda environment, `python`
normally selects the environment's interpreter.

These commands show:

1. The Python version, which must be 3.10 or newer.
2. The interpreter path, identifying where AngstromPro will be installed.
3. The supported Qt bindings already available in that environment.

A Qt binding allows Python to use the Qt graphical interface framework.
PyQt5 uses Qt 5, whereas PyQt6 uses Qt 6, and their Qt objects cannot be used
interchangeably in the same application. AngstromPro must use exactly one Qt
binding. We have confirmed that AngstromPro does not start when both PyQt5 and
PyQt6 are installed in the same environment.

Do not remove an existing binding solely to make AngstromPro work, because the
consequences depend on the environment and other software installed there.
If several supported Qt bindings are present, create a
[separate clean environment](#creating-a-separate-environment) for AngstromPro
and install exactly one supported binding in it.

Use the check results as follows:

| Result | Installation choice and code example |
| --- | --- |
| Python is older than 3.10 | Select a Python 3.10 or newer environment before installing. |
| No Qt binding is listed (`[]`) | Choose exactly one Qt extra: `pyqt5`, `pyqt6`, or `pyside6`. The example below uses `pyqt5`.<br>`python -m pip install "angstrompro[pyqt5] @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"` |
| One Qt binding is listed | Install without a Qt extra to reuse the existing binding.<br>`python -m pip install "angstrompro @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"` |
| Several Qt bindings are listed | Do not install AngstromPro in this environment. Create a separate clean environment, then install AngstromPro with exactly one supported Qt binding. |

Run only the example matching your situation, in a terminal for your selected
environment. Use `python3` instead of `python` where appropriate.

The Qt check detects package availability; it does not test whether the
underlying libraries can load successfully.

AngstromPro prefers a binding already loaded in the current Python process.
When no binding is loaded, its preference among
the three supported choices is PyQt6, then PyQt5, then PySide6.

If your current Python environment does not meet the requirements or has
dependency conflicts, see
[Creating a separate environment](#creating-a-separate-environment).

## macOS

### 1. Check your Python environment

Open Terminal and run the environment checks above, using `python3` or
`python` as appropriate.

### 2. Install AngstromPro

If a supported Qt binding is already present:

```bash
python3 -m pip install "angstrompro @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

If no supported Qt binding is present, use the following alternative instead:

```bash
python3 -m pip install "angstrompro[pyqt5] @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

The alternative uses PyQt5 as an example. PyQt6 and PySide6 are also
supported, provided a compatible package is available for your Python,
macOS version, and architecture. Select one binding rather than installing
all three.

Choose one of the two commands above. Pip downloads the repository's main
branch as a ZIP archive and installs AngstromPro and its declared dependencies.

### 3. Launch

From the same environment:

```bash
angstrompro
```

## Windows

### 1. Check your Python environment

Open PowerShell, Command Prompt, or Anaconda Prompt and run the environment
checks above using `python`.

If you use the Windows Python launcher instead, use `py` for both the checks
and installation, and confirm the interpreter path reported by the checks.

### 2. Install AngstromPro

If a supported Qt binding is already present:

```powershell
python -m pip install "angstrompro @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

If no supported Qt binding is present, use the following alternative instead:

```powershell
python -m pip install "angstrompro[pyqt5] @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

The alternative uses PyQt5 as an example. You can replace `pyqt5`
with `pyqt6` or `pyside6`; select only one Qt extra.

Choose one of the two commands above. Pip downloads the repository's main
branch as a ZIP archive and installs AngstromPro and its declared dependencies.

### 3. Launch

From the same environment:

```powershell
angstrompro
```

## Linux

### 1. Check your Python environment

Open a terminal and run the environment checks above, using `python3` or
`python` as appropriate.

### 2. Install AngstromPro

If a supported Qt binding is already present:

```bash
python3 -m pip install "angstrompro @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

If no supported Qt binding is present, use the following alternative instead:

```bash
python3 -m pip install "angstrompro[pyqt5] @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

The alternative uses PyQt5 as an example. PyQt6 and PySide6 are also
supported, subject to package availability for your platform. Select only
one Qt extra.

Choose one of the two commands above. Pip downloads the repository's main
branch as a ZIP archive and installs the declared Python dependencies.
Some Linux systems also
require operating-system libraries for Qt's display backend; use your
distribution's package manager if a startup error identifies a missing library.

If pip reports an `externally-managed-environment` error, use an environment
managed by your preferred tool. See
[Creating a separate environment](#creating-a-separate-environment).

### 3. Launch

From the same environment, within a graphical desktop session:

```bash
angstrompro
```

## Optional dependencies

The `[full]` extra adds scikit-image for optional image-processing features.
To include these features, use:

```text
python -m pip install "angstrompro[full] @ https://github.com/jhyan2018/AngstromPro/archive/refs/heads/main.zip"
```

Use `python3` instead of `python` where appropriate.

## Installing from a local copy

Use this alternative if you want to keep a local source copy or install your
own source changes. It is not required for the ZIP installation above.

To clone the repository, first make sure Git is available (`git --version`),
then run in a system terminal:

```text
git clone https://github.com/jhyan2018/AngstromPro.git
cd AngstromPro
```

If you already have a cloned or downloaded and extracted copy, skip cloning
and open a terminal in its root directory, which contains `pyproject.toml`.
Run one of the following installation commands in that directory.

With an existing supported Qt binding:

```text
python -m pip install .
```

Without an existing supported Qt binding:

```text
python -m pip install ".[pyqt5]"
```

Use `python3` where appropriate. You can select `pyqt6` or `pyside6` instead
of `pyqt5`. For optional image-processing features, use
`python -m pip install ".[full]"` with an existing Qt binding, or
`python -m pip install ".[pyqt5,full]"` if one is needed.

Normal installation is intended for users. Developers who edit the source
can use `python -m pip install -e .`; editable installation uses the working
source tree. Restart the application after source changes.

## Creating a separate environment

If your current Python is too old, its dependencies conflict, or Qt cannot
load correctly, you can select another suitable environment or create a
separate one using your preferred environment manager.

### Conda: macOS, Windows, and Linux

Run in a system terminal or Anaconda Prompt:

```text
conda create -n spm-env python=3.12 pip
conda activate spm-env
```

Here, `spm-env` is the Conda environment name. You can choose another name;
use the same name in both commands.

Python 3.12 is used as an example. Another supported version, 3.10 or newer,
can be used if compatible dependencies are available.

Then follow the installation instructions for your operating system.

### venv: macOS and Linux

Using an installed Python version of 3.10 or newer:

```bash
python3 -m venv spm-env
source spm-env/bin/activate
```

Here, `spm-env` names the virtual environment folder created in the current
directory. You can choose another name; use the same folder name in the
creation command and activation path.

### venv: Windows

Using an installed Python version of 3.10 or newer:

```powershell
python -m venv spm-env
```

Here, `spm-env` names the virtual environment folder created in the current
directory. You can choose another name; use the same folder name in the
creation command and the appropriate activation path below.

Activate in PowerShell:

```powershell
.\spm-env\Scripts\Activate.ps1
```

Or in Command Prompt:

```bat
spm-env\Scripts\activate.bat
```

After activation, install AngstromPro using the appropriate instructions above.

## Start the application

```powershell
angstrompro
```

Closing the Main Workbench closes the modules and exits the application.
Restart AngstromPro after changing application or plugin source code.

On first launch, choose a parent location. AngstromPro creates a dedicated
`angstrompro-user/` folder there with this structure:

```text
angstrompro-user/
  config/   application preferences and interface state
  cache/    regenerable thumbnail data
  logs/     diagnostic logs
```

Choose a location you can retain and back up. The application stores only a
pointer to this location in the operating system's normal application-data
folder.

## Main Workbench and startup modules

AngstromPro opens three modules by default:

- **Data Browser** for finding measurement files.
- **Image Stack Viewer** for three-dimensional image stacks.
- **Curve Stack Viewer** for curve stacks and individual spectra.

Change startup modules in the Main Workbench through
**File → Preferences… → Startup**, then click **Save as default** in that dialog.

The Main Workbench lists every live module as a card. Click **+ New Module**
and choose **Basic → Data Browser**, **Basic → Image Stack Viewer**, or
**Basic → Curve Stack Viewer**. Choose **Simulation → Planewave Synthesiser**
for the synthesiser. Click **Show** on an existing module card to bring its
window forward; **Remove** on that card closes that instance.

## First workflow with your measurements

**Input:** a supported measurement file that you want to inspect or process.

1. In Main Workbench, choose **+ New Module → Basic → Image Stack Viewer** for maps,
   or **+ New Module → Basic → Curve Stack Viewer** for spectra. Click **Show**
   on its Main Workbench card if the module is already open.
2. In the viewer, choose **File → Open…**, select your file, and choose the
   required channels when prompted (channel settings are available in the
   Main Workbench under **Preferences… → Channels**). To find a file by preview, follow the
   [Data Browser tutorial](data-browser.md#tutorial-browse-and-send-a-measurement).
3. Show **View → Workspace** and **View → Inspector**. Single-click the
   desired channel item and verify its source, dimensions, axes, and units.
   If the two panels share a dock, click their **Workspace** / **Inspector**
   tabs at the bottom to switch; they may also appear separately or float.
4. Double-click that item to display it. Check the visible name and the
   **Active Processing Slots** beneath the Workspace list before running an analysis.
5. In Image Stack Viewer, inspect the layer, colour range, and automatic FFT.
   In Curve Stack Viewer, inspect the sweep axis and select the curves to show.
6. Add your required operation through **Process → Configure Process Menu…**.
   Save the menu configuration, select the algorithm from its configured
   submenu, check its inputs and parameters, and click **Run**.
   Follow [background subtraction](processes.md#tutorial-run-background-subtraction)
   for a first topographic operation, or
   [curve comparison](curve-stack-viewer.md#tutorial-compare-and-style-spectra)
   for a spectroscopy workflow.
7. Single-click the result and use **File → Save…** to preserve numerical
   data. For an editable curve plot, first use **Scene → Save as Scene…**,
   then select and save that scene item as `.scplot`. Export presentation
   figures separately.

**Expected result:** a verified measurement channel, a displayed or processed
result, and a saved file you can reopen.

Use the [tutorial index](tutorials.md) to continue with line cuts, average
spectra, error bars, workspace archives, lattice correction, or registration.
Each procedure lists its input requirements and the result to check.

## Next steps

- Follow the [measurement-data tutorials](tutorials.md).
- Compare [lattice-correction and registration workflows](image-processing-workflows.md).
- Understand [workspaces and the Inspector](workspaces-and-inspector.md).
- Learn how to [find and configure processes](processes.md).
- Configure the [Data Browser](data-browser.md).
- Review [file I/O](file-formats.md).
- Consult [troubleshooting](troubleshooting.md) if startup fails.
