# Contributing

## Development installation

Create or activate a Python 3.10+ environment, check which Qt binding it already
contains, then install the checkout in editable mode. If one supported binding
is already installed:

```powershell
python -m pip install -e ".[full]"
```

If no binding is installed, add exactly one of `pyqt5`, `pyqt6`, or `pyside6`
to the extras, for example `python -m pip install -e ".[pyqt5,full]"`.

Launch the installed entry point:

```powershell
angstrompro
```

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
documentation should describe contracts and extension points. Avoid copying
instructions from the historical README unless they have been verified against
the current implementation.

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

Project-specific automated test and formatting commands should be documented
here when they are added to the repository.
