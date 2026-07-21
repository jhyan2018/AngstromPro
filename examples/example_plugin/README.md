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

First install AngstromPro from the repository root:

```powershell
python -m pip install -e ".[pyqt6]"
```

Then install this plugin:

```powershell
python -m pip install -e "examples/example_plugin"
```

Restart AngstromPro after installation. The package entry point imports the
plugin during startup; no path-plugin preference is required.

### Alternative: load directly from Preferences

For local development, the plugin can be loaded without installing its package.
Open the main workbench's **File → Preferences… → Plugins**, click
**Add plugin**, and enter:

```text
Path (src/ folder): <AngstromPro repository>\examples\example_plugin\src
Module name:        angstrompro_example
```

Use the `…` folder button to locate the `src` directory inside your own
AngstromPro checkout; its absolute path depends on where you cloned or copied
the repository. Save the preference and restart AngstromPro. Use either this
source-path method or the installed entry-point method above. Installing the
package and also adding its source path is unnecessary.

## Try the workflow

1. Open **Modules → Examples → Example Workflow**.
2. Click **Generate synthetic data**. The simulation runs through AngstromPro's
   task system and adds a `1 × 96 × 96` image stack to the module workspace.
3. Double-click the generated workspace item to make it the active input.
4. Set a scale factor and click **Scale active data**.
5. Select the result and open **View → Inspector** (`Ctrl+2`) to inspect its UDS
   payload, axes, metadata, and processing history.
6. Send either item to the Image Stack Viewer for visualisation.

The registered operations also appear in the Process Browser. **Scale Image
Stack** is included in the module's Process menu, and **Gaussian Demo Stack** is
included in its Simulate menu.

## Try the example format

Open `sample.apdemo` through **File → Open…** or add this directory to the Data
Browser. The loader parses a small synthetic JSON array and returns normal
`UdsDataStru` image-stack data.

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
