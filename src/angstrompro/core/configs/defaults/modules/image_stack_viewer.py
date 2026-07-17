import copy
from .._shared import IMAGE_VIEWER_DEFAULTS

DEFAULTS = copy.deepcopy(IMAGE_VIEWER_DEFAULTS)
DEFAULTS["sync"] = {
    "picked_points": False,
    "real_time_cursor": False,
    "layer": False,
    "canvas_view_zoom": False,
}
DEFAULTS["lock"] = {
    "data_scale_fixed_main": False,
    "data_scale_fixed_slave": False,
}
