# Getting started

## Check the target Python environment

**AngstromPro requires Python 3.10 or newer; Python 3.9 is not supported.**
Run the following in PowerShell, Command Prompt, or a macOS/Linux terminal:

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -c "import importlib.util as u; print([n for n in ('PyQt6','PyQt5','PySide6') if u.find_spec(n)])"
```

The final command lists supported Qt bindings already present in that exact
environment. Use this decision:

- **Python is older than 3.10:** do not install there. Create a new environment
  with Python 3.12.
- **No Qt binding is listed:** choose exactly one of `.[pyqt5]`, `.[pyqt6]`,
  or `.[pyside6]`. All three are supported.
- **Exactly one binding is listed:** install with `pip install .` and let
  AngstromPro use it; do not install another Qt extra.
- **Several bindings are listed:** do not add another binding. Try the
  no-extra installation first; AngstromPro prefers a binding already loaded by
  the IDE. Use a clean environment if Qt loading errors occur.

Qt packages in separate environments do not conflict. The problem occurs when
incompatible bindings or Qt libraries are mixed in the same environment. If
Spyder and AngstromPro deliberately share an environment that already contains
PyQt5, install AngstromPro without an extra rather than adding PyQt6.

## Create a Conda environment in a system terminal

For Conda or Anaconda, create and install into the environment from Anaconda
Prompt, PowerShell, or a macOS/Linux terminal. Do not enter these commands in
the Spyder IPython console:

```powershell
conda create -n angstrompro python=3.12 pip
conda activate angstrompro
cd path/to/AngstromPro
python -m pip install ".[pyqt5]"
```

The example chooses PyQt5, which is common in Spyder installations. PyQt6 and
PySide6 are also supported in a clean environment; replace the extra rather
than installing bindings together.

Do not install AngstromPro or a second Qt binding into Anaconda's base
environment.

## Install with standard Python

Anaconda and an IDE are not required. Install Python 3.12 from a trusted Python
distribution, then create a virtual environment in the repository.

On Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install ".[pyqt5]"
```

On macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[pyqt5]"
```

Visual Studio and VS Code users can select this `.venv` as the project
interpreter. Users without an IDE can activate it and run AngstromPro directly
from the terminal.

## Install from Spyder

In the Spyder IPython console, check its Python version:

```python
import sys
print(sys.version)
```

If it is older than Python 3.10, install a current Anaconda distribution and
open its new Spyder application. Then clone AngstromPro and install it directly
from the new Spyder IPython console:

```python
!git clone https://github.com/jhyan2018/AngstromPro.git
%cd AngstromPro
%pip install .
```

If the repository is already present, use `%cd` with its existing path and run
only `%pip install .`. Current Spyder installations already provide a supported
Qt binding, so do not install an additional Qt extra. Restart the Spyder kernel
after installation.

## Normal and editable installation

Use `python -m pip install .` for normal use. It builds and installs AngstromPro
into the active environment. Use `python -m pip install -e .` only when
developing AngstromPro: editable mode points the installation at the checkout,
so Python source changes take effect without reinstalling. Restart a running
application or Spyder kernel after changing code.

AngstromPro's compact light and dark themes are included in the package; no
theme installation extra or third-party theme package is required.

## Start the application

```powershell
angstrompro
```

### Running from Spyder

AngstromPro shares the Qt event loop owned by Spyder's IPython kernel. Closing
the Main Workbench hides all AngstromPro windows but preserves the session;
launching AngstromPro again from the same console reopens the existing module
instances and windows.

Restart the Spyder kernel before launching again after changing AngstromPro or
plugin source code. A live session retains its already imported classes, so it
is not a safe way to test revised code. This hosted behavior is specific to
Spyder and similar interactive Qt consoles: when started with the standalone
`angstrompro` command, closing the Main Workbench closes the modules and exits
the process.

On first launch, choose a parent location. AngstromPro creates a dedicated
`angstrompro-user/` folder there with this structure:

```text
angstrompro-user/
  config/   application preferences and interface state
  cache/    thumbnail and snapshot data
  logs/     diagnostic logs
```

Choose a location you can retain and back up. The application stores only a
pointer to this location in the operating system's normal application-data
folder.

## Main Workbench and startup modules

AngstromPro opens three modules by default:

- **Data Browser** for finding measurement files.
- **Image Stack Viewer** for three-dimensional image stacks.
- **Curve Stack Viewer** for two-dimensional curve stacks.

Startup modules can be changed in Preferences.

The Main Workbench lists every live module. Use **+ New Module** to open another
module, **Show** to bring an existing module window forward, and **Remove** to
close an instance you no longer need.

## First workflow without measurement data

Start with the Planewave Synthesiser if you do not have a supported data file
available:

1. In the Main Workbench, choose **+ New Module → Planewave Synthesiser**.
2. Set `qx` and `qy` for the first wave component.
3. Add further components and adjust their amplitude and phase values.
4. Choose **Save to workspace** in the Planewave Synthesiser.
5. Single-click the generated item in its Workspace dock so its row is
   highlighted, then choose **Send…**. The send command always uses the
   currently selected row.
6. Send it to an open **Image Stack Viewer**.
7. Inspect its layers and try a compatible operation from the **Process** menu.

This introduces module windows, generated data, workspaces, cross-module
sending, viewers, and processes without requiring private example files. See
the [Planewave Synthesiser guide](planewave-synthesiser.md) for its controls.

## Workflow with measurement data

1. Open Preferences and add one or more Data Browser watch folders.
2. Select a folder in the Data Browser.
3. Choose **Send to module…** on a supported file.
4. Select a compatible open module.
5. Run an operation from its **Process** menu.
6. Save workspace data with **File → Save…**, or use the viewer's export tools.

Workspace items belong to a module instance. Sending an item transfers it to
another module by default; this behavior is configurable.

## Next steps

- Generate practice data with the [Planewave Synthesiser](planewave-synthesiser.md).
- Understand [workspaces and the Inspector](workspaces-and-inspector.md).
- Learn how to [find and configure processes](processes.md).
- Configure the [Data Browser](data-browser.md).
- Review [file I/O](file-formats.md).
- Consult [troubleshooting](troubleshooting.md) if startup fails.
