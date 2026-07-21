from .image_stack_viewer  import DEFAULTS as _image_stack_viewer
from .curve_stack_viewer  import DEFAULTS as _curve_stack_viewer
from .planewave_synthesiser import DEFAULTS as _planewave_synthesiser
from .data_browser        import DEFAULTS as _data_browser

DEFAULTS = {
    "image_stack_viewer": _image_stack_viewer,
    "curve_stack_viewer": _curve_stack_viewer,
    "planewave_synthesiser": _planewave_synthesiser,
    "data_browser":       _data_browser,
}
