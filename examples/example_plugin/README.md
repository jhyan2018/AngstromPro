# AngstromPro example plugin

This installable plugin demonstrates the main AngstromPro extension points
without using experimental research data. It provides:

- A registered GUI module named **Example Workflow**
- A task-backed process that scales an image stack
- A simulation that generates a synthetic Gaussian image stack
- A read-only `.apdemo` JSON file loader
- A Python package entry point for automatic plugin discovery

The example is intentionally small. It shows how the pieces connect while
leaving scientific plotting and production file validation to real plugins.

## Install

First install AngstromPro from the repository root, using the Python
environment that will run the application. If it already contains a supported
Qt binding:

```powershell
python -m pip install -e .
```

If no supported Qt binding is installed, use `python -m pip install -e ".[pyqt5]"`
instead. You can replace `pyqt5` with `pyqt6` or `pyside6`; choose only one.
See the [environment checks](../../docs/user-guide/getting-started.md#check-your-python-environment).

Then install this plugin from the same repository root:

```powershell
python -m pip install -e "examples/example_plugin"
```

Restart AngstromPro after installation. The package entry point imports the
plugin during startup; no path-plugin preference is required.

After changing plugin source code, fully exit and restart AngstromPro to load
the revised code.

### Alternative: load directly from Preferences

For local development, the plugin can be loaded without installing its package.
Open the Main Workbench's **File → Preferences… → Plugins** (on macOS, open
**Preferences…** from the application menu), click **Add plugin**, and enter:

```text
Path (src/ folder): <AngstromPro repository>\examples\example_plugin\src
Module name:        angstrompro_example
```

Use the `…` folder button to locate the `src` directory inside your own
AngstromPro checkout; its absolute path depends on where you cloned or copied
the repository. Click **Save as default** and restart AngstromPro. Use either
this source-path method or the installed entry-point method above. Installing the
package and also adding its source path is unnecessary.

## Try the workflow

1. In Main Workbench, click **+ New Module → Examples → Example Workflow**.
2. Click **Generate synthetic data**. The simulation runs through AngstromPro's
   task system and adds a `1 × 96 × 96` image stack to the module workspace.
3. Double-click the generated workspace item to make it the active input.
   (For **Send…**, single-click the intended item first so its row is
   highlighted; double-clicking activates an item rather than sending it.)
4. Set a scale factor and click **Scale active data**.
5. Select the result and open **View → Inspector** (`Ctrl+2`) to inspect its UDS
   payload, axes, metadata, and processing history.
6. Open **+ New Module → Basic → Image Stack Viewer** in Main Workbench if
   needed. Single-click the desired item in Example Workflow's Workspace,
   click **Send…**, and choose that viewer. Double-click the received item
   there to display it.

The registered operations can also be inspected through **Process → Process
Browser…**. To run **Scale Image Stack** from the menu rather than the button,
first add it through **Process → Configure Process Menu…**. It is not added
automatically. **Gaussian Demo Stack** is available in the module's **Simulate**
menu under its registered category.

## Try the example format

In Example Workflow or Image Stack Viewer, open this directory's
`sample.apdemo` through **File → Open…**. The loader parses a small synthetic
JSON array and returns normal `UdsDataStru` image-stack data.

The current Data Browser watched-format list does not include formats registered
only through `register_ext_loader()`, so adding the example directory does not
make `.apdemo` files appear in its gallery. To preview the loaded data there,
single-click its workspace item, save it as `.uds` with **File → Save…**, and
browse the saved file. See the [I/O guide](../../docs/developer-guide/io-handlers.md#register-a-raw-extension-loader)
for the distinction between file loading and browser format discovery.

`.apdemo` is deliberately read-only. It demonstrates a raw extension loader,
not a recommended scientific storage format. Production plugins should define
metadata, validation, errors, and round-trip behavior appropriate to their
instrument format.

## Source layout

```text
src/angstrompro_example/
  __init__.py   imports every registration module
  io.py         registers the .apdemo loader
  module.py     registers the Example Workflow GUI module
  processes.py  registers the process and simulation
```

The stable `angstrompro_example.*` IDs prevent collisions with AngstromPro and
other plugins. Importing `angstrompro_example` must remain safe at application
startup because entry-point discovery imports it before the process registry is
constructed.
