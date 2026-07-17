"""Reusable default blocks shared across multiple modules."""

IMAGE_VIEWER_DEFAULTS = {
    "colormap": {
        "cmap_palette_list": ["blue1", "Blues", "blue2", "viridis", "bwr", "Greys", "pink"],
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
