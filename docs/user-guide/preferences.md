# Preferences

Open **File → Preferences…** or press `Ctrl+,` from a module window. The panel
combines application-wide settings with settings contributed by modules.

## Application settings

Application-wide preferences include:

- Appearance and optional theme
- Whether sending moves or copies a workspace item
- Modules excluded as send targets
- Local plugin source paths
- File-loading behavior and mappings for multichannel formats
- Modules created at startup
- Task concurrency

## Module settings

Module sections contain controls relevant to that module. Examples include
Data Browser watch folders and scanner settings, Image Stack Viewer
synchronisation, and Curve Stack Viewer templates.

Changes are applied to open modules where supported. Some settings, especially
plugin discovery and startup behavior, take full effect on the next launch.

## Storage

Application preferences are saved beneath the selected user-data folder in
`config/config.json`. Interface geometry and other Qt state are stored in
`config/settings.ini`. Only values that differ from built-in defaults need to
be persisted.

Plugin modules whose IDs use a plugin namespace can store settings in separate
files under `config/plugins/`, preventing a plugin from overwriting the main
configuration.

Use the Preferences reset controls carefully: regenerable cache data can be
recreated, but configuration changes may need to be entered again.
