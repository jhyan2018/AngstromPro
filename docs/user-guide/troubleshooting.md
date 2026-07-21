# Troubleshooting

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
than adding a conflicting one. PyQt5 and PySide6 extras are also available.

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
the import error.

## Logs and cache

Diagnostic logs are stored in `<UserDataFolder>/logs/angstrompro.log` with
rotating backups. Thumbnail data under `<UserDataFolder>/cache/` is
regenerable; use the Data Browser cache controls rather than manually removing
files while AngstromPro is running.
