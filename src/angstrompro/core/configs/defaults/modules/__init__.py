from .data_browser import DEFAULTS as _data_browser
from .gui_var_manager import DEFAULTS as _gui_var_manager
from .image_stack_viewer import DEFAULTS as _image_stack_viewer
from .rt_synthesis2u3 import DEFAULTS as _rt_synthesis2u3
from .line_analyzer import DEFAULTS as _line_analyzer
from .band_viewer import DEFAULTS as _band_viewer
from .dft_importer import DEFAULTS as _dft_importer
from .ai_denoising import DEFAULTS as _ai_denoising

DEFAULTS = {
    "data_browser": _data_browser,
    "gui_var_manager": _gui_var_manager,
    "image_stack_viewer": _image_stack_viewer,
    "rt_synthesis2u3": _rt_synthesis2u3,
    "line_analyzer": _line_analyzer,
    "band_viewer": _band_viewer,
    "dft_importer": _dft_importer,
    "ai_denoising": _ai_denoising,
}
