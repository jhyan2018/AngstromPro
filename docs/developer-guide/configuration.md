# Configuration

`ConfigManager` starts from built-in `DEFAULTS`, validates saved values, and
deep-merges the saved overrides. It writes only values that differ from the
built-in defaults.

## Built-in defaults

Defaults live under `angstrompro.core.configs.defaults` and are assembled into
top-level groups such as:

- `app`
- `appearance`
- `algorithms`
- `io`
- `modules`
- `plugins`
- `tasks`

Add a default before relying on a new setting. The default supplies both the
fallback value and the shape used for validation.

The `appearance` group controls the bundled theme and application font. An
empty `font_family` selects AngstromPro's
cross-platform sans-serif default; it does not inherit the font of an existing
Spyder `QApplication`. Theme support is built in and has no installation extra.

## Reading and writing

Use the shared context rather than opening JSON directly:

```python
value = context.config.get("app", "delete_after_send", True)
group = context.config.get_group("appearance")

context.config.set("app", "delete_after_send", False)
context.config.save_defaults()
```

Getters return copies so consumers cannot mutate global configuration
accidentally. `set` changes memory; `save_defaults` persists the sparse diff.

## Startup modules

`app.startup_workspaces` is a list of named, initially empty shared workspaces:

```json
[
  {"name": "Analysis", "attachments": [
    {"module_id": "image_stack_viewer", "instance": 2,
     "active_destination": "private"}
  ]}
]
```

Attachment numbers are 1-based slots within the corresponding
`app.startup_modules` count, not runtime instance IDs. Core validates this plan
against registered module types (including plugins), counts, instance limits,
unique names, and one attachment per slot. Preferences retain invalid bindings
visibly and block Apply/Save; runtime loading logs and skips invalid actions.
Failed module creation does not renumber subsequent slots. Reused singleton
instances are not reattached. Workspaces are prepared before the deferred
module-creation queue begins, and this one-shot setup never writes runtime
changes back into config.

Custom preference controls can implement `bind_preferences_controls(controls)`
to observe other draft controls and `validation_errors()` to block Apply/Save
without changing the live configuration.

Startup-module lists use special merge behavior: built-in module entries remain
present, user entries with the same ID override their counts, and new user
entries are appended.

## Module preferences

Built-in modules store their configuration beneath `modules.<module_id>`.
Preference schemas describe how those values appear in the common Preferences
panel. Apply callbacks should update open widgets without performing slow work
on the Qt thread.

**Apply** changes an instance's in-memory configuration. **Save as default**
also writes the module configuration so later instances inherit it. The Main
Workbench owns application-wide groups such as `app`, `appearance`, `io`, and
`plugins`; opening Preferences from another module edits that module's settings
instead.

The Channel Manager is a special application-wide control embedded in both the
Main Workbench and Data Browser preference schemas. Its widget must preserve
per-format drafts while users navigate between formats, and commit every draft
when the enclosing Preferences panel collects its controls.

## Plugin configuration

Plugins use `PluginConfig`, backed by one file per namespace under
`config/plugins/`. It has similar default, validation, and diff-only semantics
without granting the plugin ownership of core settings.

## Developer editor

The internal configuration editor is available with `Ctrl+Shift+D`. It is a
development and diagnostic tool, not a substitute for a supported preference
schema.
