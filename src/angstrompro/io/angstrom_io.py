# -*- coding: utf-8 -*-
"""
Central IO dispatcher for all angstrompro file formats.

File extensions
---------------
All modern files are HDF5 content regardless of extension:
    scan.uds         — UdsDataStru  (new HDF5)
    comparison.scene — DataScene
    map.sts          — future StsMap
    anything.h5      — generic, type_id read from root attribute

Legacy files use the same .uds extension but are the old custom binary format.
The loader detects them automatically by the HDF5 magic bytes (\\x89HDF).

Usage
-----
    from angstrompro.io import load, save

    data  = load(Path("scan.uds"))         # auto-detects legacy vs HDF5
    scene = load(Path("compare.scene"))    # HDF5 DataScene
    save(Path("out.uds"),   uds_data)      # writes HDF5 with type_id="uds"
    save(Path("out.scene"), scene_data)    # writes HDF5 with type_id="scene"

Extending
---------
    from angstrompro.io.angstrom_io import register_io
    register_io(
        "my_type", my_load_fn, my_save_fn,
        extension=".myt",
        display_name="My Type",
        description="What this format stores",
    )
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from angstrompro.core.data.base import WorkspaceData

log = logging.getLogger(__name__)

_HDF5_MAGIC = b"\x89HDF"


@dataclass
class FormatInfo:
    type_id:      str
    extension:    str
    display_name: str
    description:  str
    readable:     bool = True
    writable:     bool = True


_READERS:  dict[str, Callable]    = {}
_WRITERS:  dict[str, Callable]    = {}
_FORMATS:  dict[str, FormatInfo]  = {}

# Legacy format entry — always present, read-only
_FORMATS["__legacy_uds__"] = FormatInfo(
    type_id      = "__legacy_uds__",
    extension    = ".uds",
    display_name = "UDS Data (legacy)",
    description  = "Old custom binary format from AngstromPro v1. Read-only; "
                   "save as .uds to upgrade to HDF5.",
    readable     = True,
    writable     = False,
)


def register_io(
    type_id:      str,
    reader:       Callable,
    writer:       Callable,
    extension:    str  = "",
    display_name: str  = "",
    description:  str  = "",
) -> None:
    _READERS[type_id] = reader
    _WRITERS[type_id] = writer
    _FORMATS[type_id] = FormatInfo(
        type_id      = type_id,
        extension    = extension,
        display_name = display_name or type_id,
        description  = description,
        readable     = True,
        writable     = True,
    )


def registered_formats() -> list[FormatInfo]:
    """Return all known formats sorted by display name, legacy last."""
    modern = [f for f in _FORMATS.values() if not f.type_id.startswith("__")]
    legacy = [f for f in _FORMATS.values() if f.type_id.startswith("__")]
    return sorted(modern, key=lambda f: f.display_name) + legacy


def _is_hdf5(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) == _HDF5_MAGIC
    except OSError:
        return False


def _load_hdf5(path: Path) -> WorkspaceData:
    from angstrompro.io import uds_io    # noqa: F401
    from angstrompro.io import scene_io  # noqa: F401

    try:
        import h5py
        with h5py.File(path, "r") as f:
            type_id = str(f.attrs.get("type_id", ""))
    except Exception as exc:
        raise ValueError(f"Cannot open {path.name} as HDF5: {exc}") from exc

    if type_id not in _READERS:
        raise ValueError(
            f"Unknown type_id {type_id!r} in {path.name}. "
            f"Known types: {list(_READERS)}"
        )
    return _READERS[type_id](path)


def load(path: Path) -> WorkspaceData:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if _is_hdf5(path):
        return _load_hdf5(path)

    if path.suffix.lower() == ".uds":
        from angstrompro.io import uds_io
        return uds_io.load_legacy(path)

    ext = path.suffix.lower()
    _EXT_DISPATCH = {
        ".npy": "npy",
        ".txt": "txt",
        ".mat": "mat",
        ".sxm": "nanonis_sxm",
        ".3ds": "nanonis_3ds",
        ".dat": "nanonis_dat",
        ".1fl": "lf_1fl",
        ".tfr": "lf_tfr",
    }
    if ext in _EXT_DISPATCH:
        from angstrompro.io import formats  # noqa: F401  — registers readers
        type_id = _EXT_DISPATCH[ext]
        if type_id not in _READERS:
            raise ValueError(
                f"Reader for {ext!r} (type_id={type_id!r}) not registered."
            )
        return _READERS[type_id](path)

    raise ValueError(
        f"Cannot load {path.name}: not an HDF5 file and extension {ext!r} "
        f"is not a recognised format."
    )


def save(path: Path, data: WorkspaceData) -> None:
    path    = Path(path)
    type_id = data.type_id

    from angstrompro.io import uds_io    # noqa: F401
    from angstrompro.io import scene_io  # noqa: F401

    if type_id not in _WRITERS:
        raise TypeError(
            f"No IO handler registered for type_id {type_id!r}. "
            f"Known types: {list(_WRITERS)}"
        )
    _WRITERS[type_id](path, data)
    log.debug("Saved %s → %s", type_id, path.name)
