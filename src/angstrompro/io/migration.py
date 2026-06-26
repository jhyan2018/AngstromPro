# -*- coding: utf-8 -*-
"""
Version migration registry for angstrompro HDF5 files.

Each IO module declares its current version (_VERSION = N).
When loading a file whose version < current, migration functions
are applied in sequence on an intermediate dict until up to date.

Registering a migration
-----------------------
    from angstrompro.io.migration import register_migration

    @register_migration("uds", from_version=1, to_version=2)
    def _uds_v1_to_v2(d: dict) -> dict:
        # example: in v2 we split "label" into "label" + "units"
        d["axes"] = [
            {**ax, "units": ""} for ax in d["axes"]
        ]
        return d

Intermediate dict shape per type
---------------------------------
"uds":
    {
        "name": str,
        "data": np.ndarray,
        "axes": [{"values": np.ndarray, "label": str,
                  "units": str, "ticks": dict}],
        "info": dict,
        "proc_history": [{"step": str, "timestamp": str}],
    }

"scene":
    {
        "name": str,
        "canvas_config": { title, x_label, y_label,
                           legend_visible, x_min, x_max, y_min, y_max },
        "entries": [
            {
                "uds": <same shape as "uds" dict above>,
                "style": { color, linewidth, marker, alpha, label, visible },
            }
        ],
    }
"""

from typing import Callable

_MIGRATIONS: dict[tuple[str, int, int], Callable[[dict], dict]] = {}


class MigrationError(Exception):
    pass


def register_migration(type_id: str, from_version: int, to_version: int):
    """Decorator — registers a migration function for one version step."""
    if to_version != from_version + 1:
        raise ValueError("Migrations must be single-step (from_version + 1 == to_version)")

    def decorator(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        _MIGRATIONS[(type_id, from_version, to_version)] = fn
        return fn

    return decorator


def apply_migrations(type_id: str, file_version: int,
                     current_version: int, data: dict) -> dict:
    """
    Apply all registered migrations from file_version up to current_version.
    Returns the migrated dict.  Raises MigrationError if a step is missing.
    """
    if file_version == current_version:
        return data

    if file_version > current_version:
        raise MigrationError(
            f"File version {file_version} is newer than current "
            f"code version {current_version} for type {type_id!r}. "
            f"Please update AngstromPro."
        )

    for v in range(file_version, current_version):
        key = (type_id, v, v + 1)
        if key not in _MIGRATIONS:
            raise MigrationError(
                f"No migration registered for {type_id!r} v{v} → v{v + 1}. "
                f"The file may have been created by an intermediate version."
            )
        data = _MIGRATIONS[key](data)

    return data
