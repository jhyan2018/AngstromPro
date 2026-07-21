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

## Start the application

```powershell
angstrompro
```

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

## Default workspace

AngstromPro opens three modules by default:

- **Data Browser** for finding measurement files.
- **Image Stack Viewer** for three-dimensional image stacks.
- **Curve Stack Viewer** for two-dimensional curve stacks.

Startup modules can be changed in Preferences.

## First workflow

1. Open Preferences and add one or more Data Browser watch folders.
2. Select a folder in the Data Browser.
3. Choose **Send to module…** on a supported file.
4. Select a compatible open module.
5. Run an operation from its **Process** menu.
6. Save workspace data with **File → Save…**, or use the viewer's export tools.

Workspace items belong to a module instance. Sending an item transfers it to
another module by default; this behavior is configurable.

## Next steps

- Understand [workspaces and the Inspector](workspaces-and-inspector.md).
- Learn how to [find and configure processes](processes.md).
- Configure the [Data Browser](data-browser.md).
- Review [file I/O](file-formats.md).
- Consult [troubleshooting](troubleshooting.md) if startup fails.
