# Troubleshooting

## Qt DLL load failure in Anaconda or Spyder

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
python -m pip install ".[pyqt6]"
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

## The `angstrompro` command is not found

Activate the Python environment in which AngstromPro was installed, then run:

```powershell
python -m pip show angstrompro
```

If it is absent, return to the repository root and install it again with the
appropriate Qt extra.

## No Qt binding is available

Install one supported binding:

```powershell
python -m pip install ".[pyqt6]"
```

Inside an existing Spyder or Qt environment, prefer its existing binding rather
than adding a conflicting one. PyQt5 and PySide6 extras are also available. At
a Spyder IPython `In [ ]:` prompt, use `%pip install ".[pyqt5]"` instead of the
terminal form `python -m pip install ".[pyqt5]"`.

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

AngstromPro requires a writable user-data folder. Choose a location where your
account can create `config`, `cache`, and `logs` subfolders. Cancelling the
dialog cancels application startup.

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
