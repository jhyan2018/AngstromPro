from .app import DEFAULTS as _app
from .gui import DEFAULTS as _gui
from .appearance import DEFAULTS as _appearance
from .data import DEFAULTS as _data
from .tasks import DEFAULTS as _tasks
from .workflow import DEFAULTS as _workflow
from .io import DEFAULTS as _io
from .visualization import DEFAULTS as _visualization
from .algorithms import DEFAULTS as _algorithms
from .batch_runner import DEFAULTS as _batch_runner
from .modules import DEFAULTS as _modules
from .plugins import DEFAULTS as _plugins

DEFAULTS: dict = {
    "app": _app,
    "gui": _gui,
    "appearance": _appearance,
    "data": _data,
    "tasks": _tasks,
    "workflow": _workflow,
    "io": _io,
    "visualization": _visualization,
    "algorithms": _algorithms,
    "batch_runner": _batch_runner,
    "modules": _modules,
    "plugins": _plugins,
}
