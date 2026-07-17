from .app import DEFAULTS as _app
from .appearance import DEFAULTS as _appearance
from .tasks import DEFAULTS as _tasks
from .io import DEFAULTS as _io
from .algorithms import DEFAULTS as _algorithms
from .modules import DEFAULTS as _modules
from .plugins import DEFAULTS as _plugins

DEFAULTS: dict = {
    "app":        _app,
    "appearance": _appearance,
    "tasks":      _tasks,
    "io":         _io,
    "algorithms": _algorithms,
    "modules":    _modules,
    "plugins":    _plugins,
}
