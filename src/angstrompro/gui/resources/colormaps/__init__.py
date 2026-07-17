"""Register custom colormaps from bundled .txt files with matplotlib."""

from __future__ import annotations

import pathlib
import logging

import numpy as np
import matplotlib
from matplotlib import colors

log = logging.getLogger(__name__)

_COLORMAPS_DIR = pathlib.Path(__file__).parent
_registered = False


def register_all() -> None:
    """Load every .txt colormap file and register it with matplotlib. Idempotent."""
    global _registered
    if _registered:
        return
    for txt in _COLORMAPS_DIR.glob("*.txt"):
        name = txt.stem
        if name in matplotlib.colormaps:
            continue
        try:
            data = np.loadtxt(txt, delimiter="\t", skiprows=1) / 256 / 256
            # columns: R G B, values originally in 0-65535 range → divide by 256*256
            n = len(data)
            positions = np.linspace(0, 1, n)
            cdict = {
                "red":   [(positions[i], data[i, 0], data[i, 0]) for i in range(n)],
                "green": [(positions[i], data[i, 1], data[i, 1]) for i in range(n)],
                "blue":  [(positions[i], data[i, 2], data[i, 2]) for i in range(n)],
            }
            cmap = colors.LinearSegmentedColormap(name, segmentdata=cdict, N=256)
            matplotlib.colormaps.register(cmap, name=name)
        except Exception as exc:
            log.warning("Could not load colormap %s: %s", name, exc)
    _registered = True
