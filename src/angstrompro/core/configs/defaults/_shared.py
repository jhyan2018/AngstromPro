"""Reusable default blocks shared across multiple modules."""

IMAGE_VIEWER_DEFAULTS = {
    "colormap": {
        "cmap_palette_list": ["blue1", "Blues", "blue2", "viridis", "bwr", "Greys", "pink"],
    },
    "sync": {
        "picked_points": False,
        "real_time_cursor": False,
        "layer": False,
        "canvas_view_zoom": False,
    },
    "lock": {
        "data_scale_fixed_main": False,
        "data_scale_fixed_slave": False,
    },
    "factor": {
        "sigma": 5,
        "fft_auto_scale_factor": 0.5,
        "slider_scale_zoom_factor": 0.6,
    },
    "canvas": {
        "bias_text": False,
        "bias_text_color": "Red",
    },
}
