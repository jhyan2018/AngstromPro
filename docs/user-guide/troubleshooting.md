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

If using Spyder, check its console environment and reuse the binding already
loaded there. If conflicts persist, use a separate environment with one
supported Qt binding.

See the [macOS installation instructions](getting-started.md#macos).

## Windows: Qt DLL loading errors

An error such as `DLL load failed while importing QtCore` can indicate
incompatible Qt libraries or a DLL search path pointing to another installation.

First confirm the interpreter path and available bindings using the
[environment checks](getting-started.md#check-your-python-environment).

If the Spyder console already uses PyQt5, install AngstromPro without a Qt
extra. Adding PyQt6 does not replace PyQt5 within the running console and
can introduce conflicting libraries.

Do not remove packages required by Spyder or other applications without
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

In Spyder, use the Python launch instructions in
[Using Spyder](getting-started.md#using-spyder), rather than entering
`angstrompro` as a Python statement.

## No Qt binding is available

Use the [environment checks](getting-started.md#check-your-python-environment)
to identify bindings in the interpreter you intend to use.

If the result is `[]`, follow the installation command for your operating
system that includes a Qt extra. Select one of `pyqt5`, `pyqt6`, or `pyside6`.

If one or more bindings are listed, avoid adding another one. Package
detection does not guarantee that Qt can load; use the operating-system-specific
guidance above if loading fails.

## Spyder: check the console environment

If AngstromPro fails to install or launch from Spyder, run the following
Python code in Spyder's **IPython Console**, not in a system terminal:

```python
import sys

print(sys.version)
print(sys.executable)
print([n for n in ("PyQt5", "PyQt6", "PySide6") if n in sys.modules])
```

These outputs identify the console's Python version, interpreter path, and
supported Qt bindings already loaded in the console's Python process, not all
bindings installed in its environment. For example, `['PyQt5']` means PyQt5
is already loaded. Spyder normally includes PyQt5 for its own interface, but
its console may run in a separate environment. This check does not import
another binding, avoiding IPython's protection against incompatible Qt imports.

If the Python version is 3.10 or newer and a supported binding is listed,
install AngstromPro without a Qt extra using the command in
[Using Spyder](getting-started.md#using-spyder). If PyQt5 is already used by
the console, do not add PyQt6 as a replacement. Use event-loop integration
matching the loaded binding: the `%gui qt5` example in Getting started is for
PyQt5, not a universal setting for all supported bindings.
If several bindings appear as loaded, restart
the kernel and avoid importing different bindings into the same process.

If Python is older than 3.10, select a compatible interpreter in Spyder's
Python interpreter settings or [create a separate environment](getting-started.md#creating-a-separate-environment).
If the selected environment lacks a working Qt binding, use a suitable
environment through the same interpreter settings rather than mixing bindings
in the running console.
If the binding list is empty (`[]`), none of these bindings has been loaded
yet; this does not mean none is installed. Check installed packages before
deciding whether a Qt extra is needed. You can run `%pip show PyQt5 PyQt6 PySide6`
in the console to inspect package installation metadata without importing the
bindings. Do not install another binding solely because this list is empty.
An external environment also requires a `spyder-kernels` version compatible
with your Spyder installation.

This check is not a full test of AngstromPro or Qt compatibility. If launch
still fails, consult the operating-system-specific sections above.
For standalone Spyder installations, use an external environment for additional
packages rather than modifying Spyder's bundled application environment.
If the interpreter path contains `spyder-runtime`, it indicates that bundled
runtime. Confirm that installation and launch use the interpreter
reported by `sys.executable`, and restart the kernel after installation.

## Reopening AngstromPro in Spyder

Spyder owns the IPython kernel's Qt event loop. Closing the Main Workbench
hides all AngstromPro windows without destroying that shared Qt session.
Running AngstromPro again in the same console reopens the existing module
instances and windows. This is different from a standalone `angstrompro`
process, which exits when its Main Workbench is closed.

After changing AngstromPro or plugin source code, restart the Spyder kernel
before launching again. Existing widgets and imported classes do not safely
hot-reload inside a live Qt session.

## Startup stops at the folder dialog

AngstromPro requires a writable parent location where it can create its
`angstrompro-user/` folder and the `config`, `cache`, and `logs` subfolders.
Cancelling the dialog cancels application startup.

## A file or channel is missing

1. Check **Help → Supported Formats…**.
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

In Main Workbench, open **File → Preferences… → Plugins** and confirm
that it contains the plugin's `src/` folder and its importable
top-level module name. Restart AngstromPro, then inspect the application log for
the import error. When running inside Spyder, restart the Spyder kernel as well;
merely closing and reopening the hosted AngstromPro session keeps previously
imported plugin modules in memory.

## Logs and cache

Diagnostic logs are stored in `<UserDataFolder>/logs/angstrompro.log` with
rotating backups. Thumbnail data under `<UserDataFolder>/cache/` is
regenerable; use the Data Browser cache controls rather than manually removing
files while AngstromPro is running.
