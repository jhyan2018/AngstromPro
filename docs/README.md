# AngstromPro documentation

The documentation is divided by audience. Start with the user guide if you
want to install and operate AngstromPro. Use the developer guide when extending
or contributing to the application.

## Tutorials using your own measurements

Start with the [tutorial index](user-guide/tutorials.md) for a route from file
loading to saved results. Each tutorial gives input requirements, numbered
steps, expected results, and checks for common problems.

Read [How to find controls and use the mouse](user-guide/tutorials.md#how-to-find-controls-and-use-the-mouse)
for menu paths, right-click actions, single-click versus double-click, and
switching between Workspace and Inspector tabs.

- [Open a measurement and verify channels](user-guide/file-formats.md#tutorial-open-and-verify-a-measurement)
- [Inspect images, FFTs, and line cuts](user-guide/image-stack-viewer.md#tutorial-inspect-images-and-their-fourier-transforms)
- [Configure and run a process](user-guide/processes.md#tutorial-configure-a-process-menu)
- [Compare spectra and save an editable figure](user-guide/curve-stack-viewer.md#tutorial-compare-and-style-spectra)
- [Save data and export results](user-guide/file-formats.md#tutorial-save-data-and-export-results)
- [Correct a lattice or register images](user-guide/image-processing-workflows.md)

## User guide

1. [Getting started](user-guide/getting-started.md)
2. [Tutorials: working with your measurement data](user-guide/tutorials.md)
3. [Image-processing workflows](user-guide/image-processing-workflows.md)
4. [Planewave Synthesiser](user-guide/planewave-synthesiser.md)
5. [Workspaces and the Inspector](user-guide/workspaces-and-inspector.md)
6. [Processes](user-guide/processes.md)
7. [Image Stack Viewer](user-guide/image-stack-viewer.md)
8. [Curve Stack Viewer](user-guide/curve-stack-viewer.md)
9. [Data Browser](user-guide/data-browser.md)
10. [File I/O](user-guide/file-formats.md)
11. [Preferences](user-guide/preferences.md)
12. [Troubleshooting](user-guide/troubleshooting.md)

## Developer guide

Working examples are available in the repository's `AngstromPro/examples/`
folder. Start with `examples/example_plugin/`, introduced in the
[example plugin guide](developer-guide/plugins.md#complete-example). Its README
explains installation and a complete workflow, while its source
demonstrates a GUI module, a registered process, a simulation, and a read-only
file loader.

Read [Architecture](developer-guide/architecture.md) for the separation of
data management, visualisation, processing, and I/O. Then choose the relevant
extension guide below. GUI modules and processes implement functionality;
plugins organise and load those components. You do not need a new GUI module
for every new algorithm or file format.

1. [Architecture](developer-guide/architecture.md)
2. [Runtime data and workspaces](developer-guide/workspaces.md)
3. [Data model](developer-guide/data-model.md)
4. [Modules](developer-guide/modules.md)
5. [Processes](developer-guide/processes.md)
6. [Tasks and background execution](developer-guide/tasks.md)
7. [Plugins](developer-guide/plugins.md)
8. [I/O handlers](developer-guide/io-handlers.md)
9. [Configuration](developer-guide/configuration.md)
10. [Contributing](developer-guide/contributing.md)

The guides describe the current `src/angstrompro` application. The accompanying
[software paper](https://arxiv.org/abs/2604.18962v2), Section 2 and Figures 1–4,
explains the architectural design;
the interfaces and examples here follow the current code. For environment
setup and validation commands, see [Contributing](developer-guide/contributing.md).
