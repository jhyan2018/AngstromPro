# Contributing

## Development installation

Use a Python 3.10 or newer environment. Before installing, check the interpreter
and available Qt bindings as described in
[Getting started](../user-guide/getting-started.md#check-your-python-environment).

Run the following commands from the repository root, which contains
`pyproject.toml`. Use `python3` instead of `python` where appropriate.

If a supported Qt binding is already available, install in editable mode
with the optional image-processing dependencies:

```text
python -m pip install -e ".[full]"
```

If no supported Qt binding is available, include one Qt extra:

```text
python -m pip install -e ".[pyqt5,full]"
```

The example uses PyQt5. You can replace `pyqt5` with `pyqt6` or `pyside6`;
choose only one Qt extra. Reuse an existing supported binding rather than
adding another one.

Editable installation uses the working source tree. Restart AngstromPro
after changing source code.

Launch from a terminal:

```text
angstrompro
```

When Markdown documentation changes, rebuild the packaged offline HTML:

```text
python -m pip install -e ".[docs]"
python tools/build_docs.py
```

The generated files under `src/angstrompro/resources/docs/` are displayed
by **Help → Documentation…** in the **Main Workbench** and must remain
synchronized with `docs/`.

## Design expectations

- Keep scientific algorithms independent from Qt widgets.
- Represent reusable operations as registered processes.
- Return new data objects instead of mutating process inputs.
- Run expensive work through the task system.
- Add stable, namespaced IDs for externally configurable components.
- Define configuration defaults and expose normal settings through preference
  schemas.
- Register file formats through the central dispatcher.
- Preserve compatibility with PyQt6, PyQt5, and PySide6 through `qt_compat`.

## Documentation

User documentation should describe observable behavior and workflows. Developer
documentation should describe contracts and extension points. Verify menu
paths, control names, and operation sequences against the current implementation.

Update the relevant guide whenever a menu name, file format, preference, or
public extension contract changes. Keep the root README short and link to the
detailed guide.

## Before submitting a change

1. Review the working tree and preserve unrelated user changes.
2. Exercise the affected workflow with a representative dataset.
3. Test every supported Qt binding affected by compatibility changes when
   practical.
4. Check that registered processes and formats appear in their runtime
   browsers.
5. Validate Markdown links and update documentation.
6. Confirm new files contain no credentials, personal data, or generated cache.

For an extension, check its complete route through the application, not only
the numerical function:

- **Module:** open two instances and confirm that display state and process
  inputs are independent. Test private and shared output workspaces.
- **Process:** verify input immutability, result dimensions and axes, handling
  of invalid inputs, and history through the registered execution path.
- **Reader/writer:** test representative and malformed files, then round-trip
  every field the format promises to preserve. Test workspace archives
  separately if a group-level codec is provided.
- **Preview:** render without a viewer window and check that the payload is
  unchanged. A thumbnail must not replace the scientific data sent to a module.
- **Plugin:** confirm discovery after restarting, using one loading method at
  a time. A successful import does not prove that every component was registered.

## Run the automated tests

Complete the editable development installation above, including a working Qt
binding and the optional image-processing dependencies. Install pytest in the
same environment:

```text
python -m pip install pytest
```

Run the test suite from the repository root:

```text
python -m pytest -q -rs tests
```

The `-rs` option shows why tests were skipped. Tests that require an unavailable
optional plugin, such as `myplugin.io`, may be skipped; review those reasons
rather than treating a skipped test as a pass.

For a headless run on macOS or Linux, use Qt's offscreen platform:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q -rs tests
```

In Windows PowerShell, set the equivalent variable before running pytest:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q -rs tests
```

An offscreen run does not replace interactive checks of rendering, window
behaviour, or platform-specific installation. Test each supported Qt binding
in a suitable separate environment when changing compatibility code.

Before submitting, check the patch for whitespace errors:

```text
git diff --check
```

Rebuild the offline HTML after documentation changes using the command above.
