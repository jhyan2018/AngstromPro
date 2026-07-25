# Troubleshooting

## Installation is rejected because of the Python version

AngstromPro requires Python 3.10 or newer. Pip will intentionally reject an
older interpreter with an error such as:

```text
Package 'angstrompro' requires a different Python: 3.9.x not in '>=3.10'
```

Do not bypass this check or edit `requires-python`. Create a current environment
and install AngstromPro there:

```bash
conda create -n angstrompro python=3.12 pip
conda activate angstrompro
cd path/to/AngstromPro
python -m pip install ".[pyqt5]"
```

This example chooses PyQt5; PyQt6 and PySide6 are equally supported choices in
a clean environment. Install only one.

An old Spyder application can sometimes connect to this environment through
**Preferences → Python interpreter**. If its required `spyder-kernels` version
does not support the newer Python, update Spyder or install a current Anaconda
or standalone Spyder release. Avoid upgrading the Python interpreter inside an
old base environment in place.

## Qt DLL load failure in Anaconda or Spyder on Windows

An error such as the following means that Python found a Qt binding but Windows
loaded an incompatible Qt DLL:

```text
ImportError: DLL load failed while importing QtCore:
The specified procedure could not be found.
```

This commonly happens when pip's PyQt6 is installed into an Anaconda base or
Spyder environment that already contains PyQt5, PySide6, or Conda's own Qt
libraries. Installing several bindings does not make them interchangeable;
Windows may resolve a DLL belonging to a different Qt build.

The recommended solution is a dedicated environment:

```bat
conda create -n angstrompro python=3.12 pip
conda activate angstrompro
cd path\to\AngstromPro
python -m pip install ".[pyqt5]"
angstrompro
```

If AngstromPro must run in the same environment as Spyder, use the Qt binding
already required by Spyder. For an environment whose working binding is
PyQt5, remove the conflicting pip-installed PyQt6 packages and reinstall the
PyQt5 extra:

```bat
python -m pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
cd path\to\AngstromPro
python -m pip install ".[pyqt5]"
angstrompro
```

Do not remove a binding required by other applications unless you have first
confirmed which environment and binding they use. A dedicated AngstromPro
environment avoids changing Spyder's dependencies.

## The Qt Cocoa platform plugin is unavailable on macOS

This error means Python passed the version check, but Qt cannot load its macOS
window-system plugin:

```text
qt.qpa.plugin: Could not find the Qt platform plugin "cocoa"
This application failed to start because no Qt platform plugin could be initialized.
```

It is usually caused by mixed Conda and pip Qt packages, multiple Qt bindings,
or an environment variable pointing to another Qt installation. The preferred
fix is a clean environment containing exactly one binding:

```bash
conda create -n angstrompro python=3.12 pip
conda activate angstrompro
cd path/to/AngstromPro
python -m pip install ".[pyqt5]"
angstrompro
```

If the error remains, check that `which python` and `which angstrompro` both
refer to this environment. Inspect `env | grep -E '^(QT|DYLD)'`; stale
`QT_PLUGIN_PATH` or `QT_QPA_PLATFORM_PLUGIN_PATH` values should not be carried
from another Qt installation.

## The `angstrompro` command is not found

Activate the Python environment in which AngstromPro was installed, then run:

```powershell
python -m pip show angstrompro
```

If it is absent, return to the repository root and install it again with the
appropriate Qt extra.

## No Qt binding is available

Install one supported binding. For example:

```powershell
python -m pip install ".[pyqt5]"
```

Alternatively use `.[pyqt6]` or `.[pyside6]`, but do not install the alternatives
together.

Inside an existing Spyder or Qt environment, first confirm that its Python is
3.10 or newer and identify its existing binding. Prefer that binding rather
than adding a conflicting one; PyQt5 and PySide6 extras are available. When
several bindings are installed, first install AngstromPro without a Qt extra
and let it use the binding already loaded by Spyder. Move to a clean environment
if Qt loading errors continue. Use `%pip` at a Spyder IPython prompt only after
the console has been attached to the intended compatible environment.

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
2. Confirm the format is enabled in Data Browser Preferences.
3. Review channel mappings for multichannel instrument files.
4. Re-render the thumbnail after changing mappings.

## A process is missing

Open the Process Browser with `Ctrl+B`. If the process is registered, use
**Configure Process Menu…** to add it to the current module type. A process may
also be hidden when strict compatibility filtering determines that its input
requirements do not match the module.

## A plugin does not load

Confirm that Preferences contains the plugin's `src/` folder and its importable
top-level module name. Restart AngstromPro, then inspect the application log for
the import error. When running inside Spyder, restart the Spyder kernel as well;
merely closing and reopening the hosted AngstromPro session keeps previously
imported plugin modules in memory.

## Logs and cache

Diagnostic logs are stored in `<UserDataFolder>/logs/angstrompro.log` with
rotating backups. Thumbnail data under `<UserDataFolder>/cache/` is
regenerable; use the Data Browser cache controls rather than manually removing
files while AngstromPro is running.
