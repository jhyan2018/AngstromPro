# Getting started

## Install from source

AngstromPro requires Python 3.10 or newer. From a source checkout, install it
with one Qt binding:

```powershell
python -m pip install ".[pyqt6]"
```

PyQt5 and PySide6 are supported alternatives:

```powershell
python -m pip install ".[pyqt5]"
python -m pip install ".[pyside6]"
```

Do not install several Qt bindings solely for AngstromPro. When working inside
an existing environment, use the binding already required by that environment.
AngstromPro's compact light and dark themes are included in the package; no
theme installation extra or third-party theme package is required.

These `python -m pip` commands run in a system terminal. From a Spyder IPython
console whose working directory is the AngstromPro repository, use `%pip`
instead:

```python
%pip install ".[pyqt5]"
```

This installs into the environment backing the active IPython console. Apply
the same substitution when choosing another installation extra.

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

On first launch, choose a user-data folder. AngstromPro creates these folders
beneath it:

```text
config/   application preferences and interface state
cache/    regenerable thumbnail and snapshot data
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
