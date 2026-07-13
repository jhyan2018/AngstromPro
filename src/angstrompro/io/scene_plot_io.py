# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

IO for ScenePlot — saved as a single self-contained HDF5 file.

Format: JSON payload in f.attrs["payload"] + raw numpy arrays in f["arrays/"].
"""

import json
import logging
from pathlib import Path

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.data.scene_plot import (
    ScenePlot, FigureConfig, AxesSpec, AxesConfig, ArtistSpec,
    LineStyle, ScatterStyle, ImageStyle, ContourStyle,
    FillStyle, BarStyle, ErrorBarStyle, TextStyle, PatchStyle,
)
from angstrompro.io.angstrom_io import register_io
from angstrompro.io.uds_io import (
    _write_to_group as _write_uds,
    _read_from_group as _read_uds,
    _uds_to_dict, _dict_to_uds,
)

log = logging.getLogger(__name__)

_VERSION = 1


# ── rcParams serialisation ────────────────────────────────────────────────────

def _serialisable(d: dict) -> dict:
    """Coerce rcParams values to JSON-safe primitives (drop non-serialisable keys)."""
    out = {}
    for k, v in d.items():
        try:
            if isinstance(v, (bool, int, float, str)):
                out[k] = v
            elif isinstance(v, (list, tuple)):
                out[k] = list(v)
            else:
                json.dumps(v)
                out[k] = v
        except (TypeError, ValueError):
            pass
    return out


# ── Style dataclass ↔ dict ────────────────────────────────────────────────────

_STYLE_DEFAULTS: dict[str, type] = {
    "line":     LineStyle,
    "scatter":  ScatterStyle,
    "image":    ImageStyle,
    "contour":  ContourStyle,
    "fill":     FillStyle,
    "bar":      BarStyle,
    "errorbar": ErrorBarStyle,
    "text":     TextStyle,
    "patch":    PatchStyle,
}


def _style_to_dict(kind: str, style) -> dict:
    d = {}
    for f in style.__dataclass_fields__:
        v = getattr(style, f)
        if isinstance(v, UdsDataStru):
            d[f] = _uds_to_dict(v)
        elif isinstance(v, tuple):
            d[f] = list(v)
        else:
            d[f] = v
    return d


def _dict_to_style(kind: str, d: dict):
    cls = _STYLE_DEFAULTS.get(kind)
    if cls is None:
        return LineStyle()
    defaults = cls()
    kwargs = {}
    for f in cls.__dataclass_fields__:
        val = d.get(f, getattr(defaults, f))
        # UdsDataStru fields inside ErrorBarStyle
        if f in ("yerr_data", "xerr_data"):
            kwargs[f] = _dict_to_uds(val) if val is not None else None
        elif isinstance(val, list) and f in ("xlim", "ylim", "x2lim", "y2lim",
                                              "xy_arrow"):
            kwargs[f] = tuple(val) if val is not None else None
        else:
            kwargs[f] = val
    return cls(**kwargs)


# ── ArtistSpec ↔ dict ─────────────────────────────────────────────────────────

def _artist_to_dict(a: ArtistSpec) -> dict:
    return {
        "kind":    a.kind,
        "label":   a.label,
        "visible": a.visible,
        "zorder":  a.zorder,
        "alpha":   a.alpha,
        "row":     a.row,
        "x_col":   a.x_col,
        "extra":   a.extra,
        "data":    _uds_to_dict(a.data) if a.data is not None else None,
        "style":   _style_to_dict(a.kind, a.style),
    }


def _dict_to_artist(d: dict) -> ArtistSpec:
    kind  = d.get("kind", "line")
    raw   = d.get("data")
    data  = _dict_to_uds(raw) if raw is not None else None
    style = _dict_to_style(kind, d.get("style", {}))
    row   = d.get("row")
    return ArtistSpec(
        kind    = kind,
        style   = style,
        data    = data,
        label   = d.get("label", ""),
        visible = d.get("visible", True),
        zorder  = d.get("zorder"),
        alpha   = d.get("alpha"),
        row     = int(row) if row is not None else None,
        x_col   = int(d.get("x_col", 0)),
        extra   = d.get("extra", {}),
    )


# ── AxesConfig ↔ dict ─────────────────────────────────────────────────────────

def _axescfg_to_dict(c: AxesConfig) -> dict:
    return {
        "title":      c.title,
        "xlabel":     c.xlabel,
        "ylabel":     c.ylabel,
        "xlim":       list(c.xlim) if c.xlim else None,
        "ylim":       list(c.ylim) if c.ylim else None,
        "xscale":     c.xscale,
        "yscale":     c.yscale,
        "grid":       c.grid,
        "grid_which": c.grid_which,
        "legend":     c.legend,
        "legend_loc": c.legend_loc,
        "aspect":     c.aspect,
        "x2label":    c.x2label,
        "y2label":    c.y2label,
        "x2lim":      list(c.x2lim) if c.x2lim else None,
        "y2lim":      list(c.y2lim) if c.y2lim else None,
        "x2scale":    c.x2scale,
        "y2scale":    c.y2scale,
    }


def _dict_to_axescfg(d: dict) -> AxesConfig:
    def _lim(v):
        return tuple(v) if v is not None else None
    return AxesConfig(
        title      = d.get("title", ""),
        xlabel     = d.get("xlabel", ""),
        ylabel     = d.get("ylabel", ""),
        xlim       = _lim(d.get("xlim")),
        ylim       = _lim(d.get("ylim")),
        xscale     = d.get("xscale", "linear"),
        yscale     = d.get("yscale", "linear"),
        grid       = d.get("grid", False),
        grid_which = d.get("grid_which", "major"),
        legend     = d.get("legend", False),
        legend_loc = d.get("legend_loc", "best"),
        aspect     = d.get("aspect", "auto"),
        x2label    = d.get("x2label", ""),
        y2label    = d.get("y2label", ""),
        x2lim      = _lim(d.get("x2lim")),
        y2lim      = _lim(d.get("y2lim")),
        x2scale    = d.get("x2scale", "linear"),
        y2scale    = d.get("y2scale", "linear"),
    )


# ── AxesSpec ↔ dict ───────────────────────────────────────────────────────────

def _axesspec_to_dict(ax: AxesSpec) -> dict:
    return {
        "config":          _axescfg_to_dict(ax.config),
        "artists":         [_artist_to_dict(a) for a in ax.artists],
        "row":             ax.row,
        "col":             ax.col,
        "rowspan":         ax.rowspan,
        "colspan":         ax.colspan,
        "projection":      ax.projection,
        "twin_of":         ax.twin_of,
        "twin_axis":       ax.twin_axis,
        "colorbar_target": ax.colorbar_target,
        "extra":           ax.extra,
    }


def _dict_to_axesspec(d: dict) -> AxesSpec:
    return AxesSpec(
        config          = _dict_to_axescfg(d.get("config", {})),
        artists         = [_dict_to_artist(a) for a in d.get("artists", [])],
        row             = int(d.get("row", 0)),
        col             = int(d.get("col", 0)),
        rowspan         = int(d.get("rowspan", 1)),
        colspan         = int(d.get("colspan", 1)),
        projection      = d.get("projection", "rectilinear"),
        twin_of         = int(d.get("twin_of", -1)),
        twin_axis       = d.get("twin_axis", ""),
        colorbar_target = int(d.get("colorbar_target", -1)),
        extra           = d.get("extra", {}),
    )


# ── FigureConfig ↔ dict ───────────────────────────────────────────────────────

def _figcfg_to_dict(fig: FigureConfig) -> dict:
    return {
        "nrows":     fig.nrows,
        "ncols":     fig.ncols,
        "mosaic":    fig.mosaic,
        "sharex":    fig.sharex,
        "sharey":    fig.sharey,
        "hspace":    fig.hspace,
        "wspace":    fig.wspace,
        "suptitle":  fig.suptitle,
        "axes_list": [_axesspec_to_dict(ax) for ax in fig.axes_list],
    }


def _dict_to_figcfg(d: dict) -> FigureConfig:
    return FigureConfig(
        nrows     = int(d.get("nrows", 1)),
        ncols     = int(d.get("ncols", 1)),
        mosaic    = d.get("mosaic", ""),
        sharex    = bool(d.get("sharex", False)),
        sharey    = bool(d.get("sharey", False)),
        hspace    = d.get("hspace"),
        wspace    = d.get("wspace"),
        suptitle  = d.get("suptitle", ""),
        axes_list = [_dict_to_axesspec(ax) for ax in d.get("axes_list", [])],
    )


# ── ScenePlot ↔ dict ──────────────────────────────────────────────────────────

def _scene_to_dict(scene: ScenePlot) -> dict:
    return {
        "name":           scene.name,
        "figure":         _figcfg_to_dict(scene.figure),
        "rcparams_delta": _serialisable(scene.rcparams_delta),
    }


def _dict_to_scene(d: dict) -> ScenePlot:
    return ScenePlot(
        name           = d.get("name", ""),
        figure         = _dict_to_figcfg(d.get("figure", {})),
        rcparams_delta = d.get("rcparams_delta", {}),
    )



# ── HDF5 save / load ──────────────────────────────────────────────────────────

def save(path: Path, scene: ScenePlot) -> None:
    import h5py

    payload = json.dumps(_scene_to_dict(scene), default=str)

    with h5py.File(path, "w") as f:
        f.attrs["type_id"] = "scene_plot"
        f.attrs["version"] = _VERSION
        f.attrs["name"]    = scene.name
        f.attrs["payload"] = payload

        # Embed raw UDS arrays as proper HDF5 datasets for portability
        # (payload holds the full dict but with data as lists — HDF5 arrays
        # are the authoritative numerical storage; _uds_to_dict already converts
        # ndarray → list for JSON, so payload is self-contained too).
        # We keep the flat HDF5 array groups for external tools to read directly.
        eg = f.create_group("arrays")
        _embed_arrays(eg, scene)


def _embed_arrays(grp, scene: ScenePlot) -> None:
    """Write raw numpy arrays into HDF5 groups alongside the JSON payload."""
    import h5py
    for ai, ax_spec in enumerate(scene.figure.axes_list):
        ag = grp.create_group(f"axes_{ai}")
        for ji, artist in enumerate(ax_spec.artists):
            if artist.data is None:
                continue
            _write_uds(ag.create_group(f"artist_{ji}"), artist.data)
            # errorbar secondary UDS
            if artist.kind == "errorbar":
                st = artist.style
                if st.yerr_data is not None:
                    _write_uds(ag.create_group(f"artist_{ji}_yerr"), st.yerr_data)
                if st.xerr_data is not None:
                    _write_uds(ag.create_group(f"artist_{ji}_xerr"), st.xerr_data)


def load(path: Path) -> ScenePlot:
    import h5py

    with h5py.File(path, "r") as f:
        name = str(f.attrs.get("name", path.stem))
        d    = json.loads(str(f.attrs["payload"]))

    return _dict_to_scene(d)


# ── Register ──────────────────────────────────────────────────────────────────

register_io(
    "scene_plot", load, save,
    extension    = ".scplot",
    display_name = "Plot Scene",
    description  = "Multi-curve canvas: multiple UDS datasets combined with "
                   "individual plot styles and canvas layout configuration.",
)
