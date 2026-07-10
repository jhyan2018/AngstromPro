from .image_stack_viewer  import DEFAULTS as _image_stack_viewer
from .curve_stack_viewer  import DEFAULTS as _curve_stack_viewer
from .rt_synthesis        import DEFAULTS as _rt_synthesis

DEFAULTS = {
    "image_stack_viewer": _image_stack_viewer,
    "curve_stack_viewer": _curve_stack_viewer,
    "rt_synthesis":       _rt_synthesis,
}
