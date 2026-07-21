"""Registration entry point for the AngstromPro example plugin."""

# Import every extension module so its registration calls run during startup.
from . import io as _io  # noqa: F401
from . import processes as _processes  # noqa: F401
from . import module as _module  # noqa: F401

__all__: list[str] = []
