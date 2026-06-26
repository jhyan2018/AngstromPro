# -*- coding: utf-8 -*-
"""
IO for UdsDataStru.

New format : HDF5  (.uds or any extension) — full precision, type_id="uds"
Legacy format : custom binary (.uds)        — read-only, converted on load

Version history
---------------
v1 (current) — initial HDF5 format
"""

import json
import logging
from pathlib import Path

import numpy as np

from angstrompro.core.data.uds_data import Axis, ProcRecord, UdsDataStru
from angstrompro.io.angstrom_io import register_io
from angstrompro.io.migration import apply_migrations

log = logging.getLogger(__name__)

_VERSION = 1


# ------------------------------------------------------------------
# Intermediate dict  ←→  UdsDataStru
# ------------------------------------------------------------------

def _uds_to_dict(uds: UdsDataStru) -> dict:
    return {
        "name": uds.name,
        "data": uds.data,
        "axes": [
            {
                "values": ax.values,
                "label":  ax.label,
                "units":  ax.units,
                "ticks":  ax.ticks,
            }
            for ax in uds.axes
        ],
        "info":         uds.info,
        "proc_history": [
            {"step": r.step, "params": r.params, "input_item_names": r.input_item_names}
            for r in uds.proc_history
        ],
        # landmarks: tuple keys serialised as JSON arrays
        "landmarks": {json.dumps(list(k)): v for k, v in uds.landmarks.items()},
    }


def _dict_to_uds(d: dict) -> UdsDataStru:
    axes = [
        Axis(
            values = ax["values"],
            label  = ax.get("label", "? (?)"),
            units  = ax.get("units", ""),
            ticks  = {float(k): v for k, v in ax.get("ticks", {}).items()},
        )
        for ax in d.get("axes", [])
    ]
    proc_history = [ProcRecord(**r) for r in d.get("proc_history", [])]
    landmarks = {
        tuple(float(x) for x in json.loads(k)): v
        for k, v in d.get("landmarks", {}).items()
    }
    return UdsDataStru(
        name         = d["name"],
        data         = d["data"],
        axes         = axes,
        info         = d.get("info", {}),
        proc_history = proc_history,
        landmarks    = landmarks,
    )


# ------------------------------------------------------------------
# HDF5 group-level helpers (used by project_io too)
# ------------------------------------------------------------------

def _write_to_group(g, uds: UdsDataStru) -> None:
    """Write a UdsDataStru into an already-open h5py group."""
    g.attrs["name"]    = uds.name
    g.attrs["version"] = _VERSION
    g.create_dataset("raw_data", data=uds.data, compression="gzip")
    for i, ax in enumerate(uds.axes):
        ag = g.create_group(f"axes/{i}")
        ag.create_dataset("values", data=ax.values)
        ag.attrs["label"] = ax.label
        ag.attrs["units"] = ax.units
        ag.attrs["ticks"] = json.dumps(
            {str(k): v for k, v in ax.ticks.items()}
        )
    g.attrs["info"]         = json.dumps(uds.info)
    g.attrs["proc_history"] = json.dumps(
        [{"step": r.step, "params": r.params, "input_item_names": r.input_item_names}
         for r in uds.proc_history]
    )
    g.attrs["landmarks"] = json.dumps(
        {json.dumps(list(k)): v for k, v in uds.landmarks.items()}
    )


def _read_from_group(g) -> dict:
    """Read an intermediate dict from an h5py group (no migration applied)."""
    axes = []
    if "axes" in g:
        for i in range(len(g["axes"])):
            ag = g[f"axes/{i}"]
            axes.append({
                "values": ag["values"][()],
                "label":  str(ag.attrs.get("label", "? (?)")),
                "units":  str(ag.attrs.get("units", "")),
                "ticks":  json.loads(ag.attrs.get("ticks", "{}")),
            })
    return {
        "name":         str(g.attrs.get("name", "")),
        "data":         g["raw_data"][()],
        "axes":         axes,
        "info":         json.loads(g.attrs.get("info", "{}")),
        "proc_history": json.loads(g.attrs.get("proc_history", "[]")),
        "landmarks":    json.loads(g.attrs.get("landmarks", "{}")),
    }


# ------------------------------------------------------------------
# HDF5 file save / load
# ------------------------------------------------------------------

def save(path: Path, uds: UdsDataStru) -> None:
    import h5py
    with h5py.File(path, "w") as f:
        f.attrs["type_id"] = "uds"
        f.attrs["version"] = _VERSION
        _write_to_group(f, uds)


def load(path: Path) -> UdsDataStru:
    import h5py
    with h5py.File(path, "r") as f:
        file_version = int(f.attrs.get("version", 1))
        d = _read_from_group(f)

    d = apply_migrations("uds", file_version, _VERSION, d)
    return _dict_to_uds(d)


# ------------------------------------------------------------------
# Legacy .uds binary reader (read-only)
# ------------------------------------------------------------------

def load_legacy(path: Path) -> UdsDataStru:
    """
    Read the old custom binary .uds format produced by UdsDataProcess.saveToFile().

    File layout
    -----------
    <name>\\n
    Shape=<d0>,<d1>,...\\n
    DataType=<dtype>\\n
    Axis Name=<n0>,<n1>,...\\n
    Axis Value=<v0,v1,...;v0,v1,...>   (';' between axes, ',' between values,
                                        '&' between real&imag / x&y pairs)\\n
    [key=value\\n ...]
    :INFO_END:\\n
    [proc_history line\\n ...]
    :PROC_HISTORY_END:\\n
    [proc_to_do line\\n ...]
    :HEADER_END:\\n
    <raw binary array data>
    """
    with open(path, "rb") as f:
        name       = f.readline().decode("utf-8").strip()
        shape_text = f.readline().decode("utf-8").strip().split("=")[-1].split(",")
        shape      = [int(s) for s in shape_text]
        data_type  = f.readline().decode("utf-8").strip().split("=")[-1]
        axis_name  = f.readline().decode("utf-8").strip().split("=")[-1]
        axis_value = f.readline().decode("utf-8").strip().split("=")[-1]
        info_start = f.tell()
        while True:
            line = f.readline().decode().strip()
            if line == ":HEADER_END:":
                break
        raw = np.fromfile(f, dtype=data_type, count=-1)

    try:
        data = raw.reshape(shape)
    except ValueError:
        log.warning("Legacy load: shape mismatch in %s", path.name)
        data = raw

    uds = UdsDataStru.from_array(data, name)

    with open(path, "rb") as f:
        f.seek(info_start)
        while True:
            line = f.readline().decode("utf-8").strip()
            if line in (":INFO_END:", ":HEADER_END:", ""):
                break
            if "=" in line:
                k, v = line.split("=", 1)
                uds.info[k] = v

    axis_name_list = axis_name.split(",") if axis_name else []
    for i, ax in enumerate(uds.axes):
        if i < len(axis_name_list):
            raw_label = axis_name_list[i]
            if "(" in raw_label and raw_label.endswith(")"):
                lbl, unit = raw_label[:-1].split("(", 1)
                ax.label = lbl.strip()
                ax.units = unit.strip()
            else:
                ax.label = raw_label

    axis_value_text_list = axis_value.split(";") if axis_value else []
    for i, av_txt in enumerate(axis_value_text_list):
        if i >= len(uds.axes):
            break
        if "&" not in av_txt:
            uds.axes[i].values = np.array(list(map(float, av_txt.split(","))),
                                          dtype=np.float64)
        else:
            pairs = [list(map(float, p.split("&"))) for p in av_txt.split(",")]
            uds.axes[i].values = np.array(pairs, dtype=np.float64)

    with open(path, "rb") as f:
        f.seek(info_start)
        while True:
            line = f.readline().decode("utf-8").strip()
            if line == ":INFO_END:":
                break
        while True:
            line = f.readline().decode("utf-8").strip()
            if line in (":PROC_HISTORY_END:", ":HEADER_END:", ""):
                break
            uds.proc_history.append(ProcRecord(step=line))

    log.info("Loaded legacy .uds: %s  shape=%s  dtype=%s", name, shape, data_type)
    return uds


# ------------------------------------------------------------------
register_io(
    "uds", load, save,
    extension    = ".uds",
    display_name = "UDS Data",
    description  = "Single scientific dataset with named axes, metadata, and "
                   "processing history. Supports 1D/2D/3D arrays of any dtype.",
)
