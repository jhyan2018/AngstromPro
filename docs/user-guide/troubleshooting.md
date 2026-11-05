# Troubleshooting

## Installation is rejected because of the Python version

AngstromPro requires Python 3.10 or newer. Check the interpreter used for
installation:

```text
python --version
python -c "import sys; print(sys.executable)"
```

Use `python3` where appropriate. If the interpreter is too old, select an
existing compatible environment or follow
[Creating a separate environment](getting-started.md#creating-a-separate-environment).

Do not bypass the package's Python-version requirement.

## macOS: Qt or Cocoa platform-plugin errors

Confirm that installation and launch use the same Python environment:

```bash
python3 -c "import sys, platform; print(sys.executable); print(platform.machine())"
```

For a native setup, use ARM64 Python on Apple Silicon and x86_64 Python on
Intel. Keep Python and its compiled dependencies in the same architecture.

Qt loading can also fail when the environment contains conflicting Qt
libraries or when `QT_PLUGIN_PATH` or `QT_QPA_PLATFORM_PLUGIN_PATH` points
to another installation.

If Qt conflicts persist, use a separate environment with one supported Qt
binding.

See the [macOS installation instructions](getting-started.md#macos).

## Windows: Qt DLL loading errors

An error such as `DLL load failed while importing QtCore` can indicate
incompatible Qt libraries or a DLL search path pointing to another installation.

First confirm the interpreter path and available bindings using the
[environment checks](getting-started.md#check-your-python-environment).

Do not remove packages required by other applications without
checking their dependencies. If the current environment cannot load Qt
reliably, use a separate environment with one supported binding.

See the [Windows installation instructions](getting-started.md#windows).

## Linux: environment or Qt display errors

If pip reports `externally-managed-environment`, select an environment
managed by your preferred tool or follow
[Creating a separate environment](getting-started.md#creating-a-separate-environment).

AngstromPro requires a graphical desktop session. If Qt reports a missing
display plugin or shared library, check the detailed error and install the
required system packages using your distribution's package manager.

Pip installs Python dependencies but does not install operating-system
packages.

See the [Linux installation instructions](getting-started.md#linux).

## The angstrompro command is not found

Activate the environment used for installation and check:

```text
python -m pip show angstrompro
```

Use `python3` where appropriate.

If AngstromPro is absent, install it following the instructions for your
operating system. If it is present, check that the environment's executable
directory is on your PATH.

Run `angstrompro` in a system terminal, not as a Python statement.

## No Qt binding is available

Use the [environment checks](getting-started.md#check-your-python-environment)
to identify bindings in the interpreter you intend to use.

If the result is `[]`, follow the installation command for your operating
system that includes a Qt extra. Select one of `pyqt5`, `pyqt6`, or `pyside6`.

If one or more bindings are listed, avoid adding another one. Package
detection does not guarantee that Qt can load; use the operating-system-specific
guidance above if loading fails.

## Startup stops at the folder dialog

AngstromPro requires a writable parent location where it can create its
`angstrompro-user/` folder and the `config`, `cache`, and `logs` subfolders.
Cancelling the dialog cancels application startup.

## A file or channel is missing

1. In the **Main Workbench**, check **Help → Supported Formats…**.
2. In Data Browser, open **File → Preferences… → Watched formats** and
   confirm that the format is checked.
3. Review **File → Preferences… → Channels** in Main Workbench or Data Browser.
4. After changing mappings, right-click the data thumbnail and choose
   **Re-render thumbnail**.

## A process is missing

Open **Process → Process Browser…** or press `Ctrl+B`. If the process is registered, use
**Process → Configure Process Menu…** to add it to the current module type. A process may
also be hidden when strict compatibility filtering determines that its input
requirements do not match the module.

## A plugin does not load

For a local source plugin, open **File → Preferences… → Plugins** in Main
Workbench and confirm the absolute `src/` path and importable top-level module
name. Click **Save as default**, then restart AngstromPro.

For an installed plugin, confirm that its package is installed in the same
Python environment as AngstromPro and exposes an `angstrompro.plugins` entry
point. This method does not require a source-path preference.

Inspect the application log for import errors. After editing plugin code,
fully exit and restart the application to load the revised modules. See
[Plugins](../developer-guide/plugins.md) for both loading methods.

## Logs and cache

Diagnostic logs are stored in `<UserDataFolder>/logs/angstrompro.log` with
rotating backups. Thumbnail data under `<UserDataFolder>/cache/` is
regenerable; use the Data Browser cache controls rather than manually removing
files while AngstromPro is running.
