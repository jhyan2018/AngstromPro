# -*- coding: utf-8 -*-
"""
IO for DataScene — saved as a single self-contained HDF5 file.

Version history
---------------
v1 (current) — initial HDF5 format
"""

import json
import logging
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.data.data_scene import CanvasConfig, DataScene, PlotStyle, SceneEntry
from angstrompro.io.angstrom_io import register_io
from angstrompro.io.migration import apply_migrations
from angstrompro.io.uds_io import _write_to_group as _write_uds, _read_from_group as _read_uds, _dict_to_uds

log = logging.getLogger(__name__)

_VERSION = 1


# ------------------------------------------------------------------
# Intermediate dict  ←→  DataScene
# ------------------------------------------------------------------

def _scene_to_dict(scene: DataScene) -> dict:
    from angstrompro.io.uds_io import _uds_to_dict
    return {
        "name": scene.name,
        "canvas_config": {
            "title":          scene.canvas_config.title,
            "x_label":        scene.canvas_config.x_label,
            "y_label":        scene.canvas_config.y_label,
            "legend_visible": scene.canvas_config.legend_visible,
            "x_min":          scene.canvas_config.x_min,
            "x_max":          scene.canvas_config.x_max,
            "y_min":          scene.canvas_config.y_min,
            "y_max":          scene.canvas_config.y_max,
        },
        "entries": [
            {
                "uds": _uds_to_dict(entry.data),
                "style": {
                    "color":     entry.style.color,
                    "linewidth": entry.style.linewidth,
                    "marker":    entry.style.marker,
                    "alpha":     entry.style.alpha,
                    "label":     entry.style.label,
                    "visible":   entry.style.visible,
                },
            }
            for entry in scene.entries
        ],
    }


def _dict_to_scene(d: dict) -> DataScene:
    cc = d.get("canvas_config", {})

    def _nan_to_none(v):
        return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)

    canvas_config = CanvasConfig(
        title          = cc.get("title", ""),
        x_label        = cc.get("x_label", ""),
        y_label        = cc.get("y_label", ""),
        legend_visible = cc.get("legend_visible", True),
        x_min = _nan_to_none(cc.get("x_min")),
        x_max = _nan_to_none(cc.get("x_max")),
        y_min = _nan_to_none(cc.get("y_min")),
        y_max = _nan_to_none(cc.get("y_max")),
    )

    entries = []
    for e in d.get("entries", []):
        uds   = _dict_to_uds(e["uds"])
        s     = e.get("style", {})
        style = PlotStyle(
            color     = s.get("color", ""),
            linewidth = s.get("linewidth", 1.5),
            marker    = s.get("marker", ""),
            alpha     = s.get("alpha", 1.0),
            label     = s.get("label", ""),
            visible   = s.get("visible", True),
        )
        entries.append(SceneEntry(data=uds, style=style))

    return DataScene(name=d["name"], entries=entries, canvas_config=canvas_config)


# ------------------------------------------------------------------
# HDF5 file save / load
# ------------------------------------------------------------------

def save(path: Path, scene: DataScene) -> None:
    import h5py

    with h5py.File(path, "w") as f:
        f.attrs["type_id"] = "scene"
        f.attrs["version"] = _VERSION
        f.attrs["name"]    = scene.name

        cc = f.create_group("canvas_config")
        cc.attrs["title"]          = scene.canvas_config.title
        cc.attrs["x_label"]        = scene.canvas_config.x_label
        cc.attrs["y_label"]        = scene.canvas_config.y_label
        cc.attrs["legend_visible"] = scene.canvas_config.legend_visible
        for key in ("x_min", "x_max", "y_min", "y_max"):
            val = getattr(scene.canvas_config, key)
            cc.attrs[key] = val if val is not None else float("nan")

        eg = f.create_group("entries")
        for i, entry in enumerate(scene.entries):
            g = eg.create_group(str(i))
            _write_uds(g, entry.data)
            sg = g.create_group("style")
            sg.attrs["color"]     = entry.style.color
            sg.attrs["linewidth"] = entry.style.linewidth
            sg.attrs["marker"]    = entry.style.marker
            sg.attrs["alpha"]     = entry.style.alpha
            sg.attrs["label"]     = entry.style.label
            sg.attrs["visible"]   = entry.style.visible


def load(path: Path) -> DataScene:
    import h5py

    with h5py.File(path, "r") as f:
        file_version = int(f.attrs.get("version", 1))
        name         = str(f.attrs.get("name", path.stem))
        cc_g         = f["canvas_config"]

        canvas_config_raw = {
            "title":          str(cc_g.attrs.get("title", "")),
            "x_label":        str(cc_g.attrs.get("x_label", "")),
            "y_label":        str(cc_g.attrs.get("y_label", "")),
            "legend_visible": bool(cc_g.attrs.get("legend_visible", True)),
            "x_min":          float(cc_g.attrs.get("x_min", float("nan"))),
            "x_max":          float(cc_g.attrs.get("x_max", float("nan"))),
            "y_min":          float(cc_g.attrs.get("y_min", float("nan"))),
            "y_max":          float(cc_g.attrs.get("y_max", float("nan"))),
        }

        entries_raw = []
        eg = f["entries"]
        for i in range(len(eg)):
            g  = eg[str(i)]
            sg = g["style"]
            entries_raw.append({
                "uds": _read_uds(g),
                "style": {
                    "color":     str(sg.attrs.get("color", "")),
                    "linewidth": float(sg.attrs.get("linewidth", 1.5)),
                    "marker":    str(sg.attrs.get("marker", "")),
                    "alpha":     float(sg.attrs.get("alpha", 1.0)),
                    "label":     str(sg.attrs.get("label", "")),
                    "visible":   bool(sg.attrs.get("visible", True)),
                },
            })

    d = {"name": name, "canvas_config": canvas_config_raw, "entries": entries_raw}
    d = apply_migrations("scene", file_version, _VERSION, d)
    return _dict_to_scene(d)


# ------------------------------------------------------------------
register_io(
    "scene", load, save,
    extension    = ".scene",
    display_name = "Plot Scene",
    description  = "Multi-curve canvas: multiple UDS datasets combined with "
                   "individual plot styles and canvas layout configuration.",
)
