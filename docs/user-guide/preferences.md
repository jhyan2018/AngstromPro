# Preferences

Open **File → Preferences…** or press `Ctrl+,` from a module window. The panel
combines application-wide settings with settings contributed by modules.

## Application settings

Application-wide preferences include:

- Appearance, including the bundled light or dark theme and application font
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

## Appearance

AngstromPro provides its own compact light and dark themes. They use a
consistent Qt Fusion foundation and do not require a separate theme package.
The **Auto** option selects light or dark from the environment when the theme
is applied.

The font-family list contains up to ten modern sans-serif choices available on
the current system, previews each family, and always shows the active choice
when closed. The default 10-point size is intended for information-dense module
panels; its spin box accepts 7 to 24 points. Theme and font changes are applied
application-wide.

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
