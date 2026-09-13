"""Colormap discovery, registration, and managed user storage.

The Matplotlib registry is deliberately treated as a rendering mechanism, not
as the source of provenance.  AngstromPro presets and user-defined colormaps
are tracked explicitly so the Preferences UI can present stable source groups
regardless of registration order.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Iterable, Mapping
from uuid import uuid4

import matplotlib
from matplotlib import colors
import numpy as np

from angstrompro.app.user_data_folder import user_data_subpath
from angstrompro.utils.qt_compat import QtCore, Signal


log = logging.getLogger(__name__)

SOURCE_MATPLOTLIB = "matplotlib"
SOURCE_ANGSTROMPRO = "angstrompro"
SOURCE_USER = "user"

SOURCE_LABELS = {
    SOURCE_MATPLOTLIB: "Matplotlib",
    SOURCE_ANGSTROMPRO: "AngstromPro presets",
    SOURCE_USER: "My colormaps",
}
SOURCE_ORDER = (SOURCE_MATPLOTLIB, SOURCE_ANGSTROMPRO, SOURCE_USER)

USER_COLORMAP_FORMAT = "angstrompro-colormap"
USER_COLORMAP_VERSION = 1

_BUNDLED_DIR = Path(__file__).resolve().parents[1] / "resources" / "colormaps"
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED_STEMS = {
    "con", "prn", "aux", "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


@dataclass(frozen=True)
class ColormapRecord:
    """One available colormap and its explicit source."""

    name: str
    source: str
    path: Path | None = None


class ColormapNameConflictError(ValueError):
    """Raised when a user colormap name would make provenance ambiguous."""

    def __init__(self, name: str, conflicting: ColormapRecord):
        self.name = name
        self.conflicting = conflicting
        label = SOURCE_LABELS.get(conflicting.source, conflicting.source)
        super().__init__(
            f'A colormap named "{conflicting.name}" already exists in {label}.'
        )


def _normalise_anchors(
    anchors: Iterable[Mapping[str, object]],
) -> list[dict[str, float]]:
    items: list[dict[str, float]] = []
    for anchor in anchors:
        try:
            item = {
                "position": float(anchor["position"]),
                "red": float(anchor["red"]),
                "green": float(anchor["green"]),
                "blue": float(anchor["blue"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Every anchor must contain numeric position, red, green, and blue values."
            ) from exc
        if not all(np.isfinite(value) for value in item.values()):
            raise ValueError("Colormap anchor values must be finite numbers.")
        for key in item:
            item[key] = max(0.0, min(1.0, item[key]))
        items.append(item)

    if len(items) < 2:
        raise ValueError("A colormap requires at least two anchors.")
    items.sort(key=lambda item: item["position"])
    items[0]["position"] = 0.0
    items[-1]["position"] = 1.0
    if any(
        right["position"] <= left["position"]
        for left, right in zip(items, items[1:])
    ):
        raise ValueError("Colormap anchor positions must be strictly increasing.")
    return items


def colormap_from_anchors(
    name: str,
    anchors: Iterable[Mapping[str, object]],
    *,
    size: int = 256,
) -> colors.LinearSegmentedColormap:
    """Build a Matplotlib colormap from AngstromPro anchor dictionaries."""
    items = _normalise_anchors(anchors)
    channel_data = {"red": [], "green": [], "blue": []}
    for item in items:
        position = item["position"]
        for channel in channel_data:
            value = item[channel]
            channel_data[channel].append((position, value, value))
    return colors.LinearSegmentedColormap(name, channel_data, N=size)


def _normalise_legacy_rgb(data: np.ndarray) -> np.ndarray:
    data = np.asarray(data, dtype=float)
    data = np.atleast_2d(data)
    if data.shape[0] < 2 or data.shape[1] < 3:
        raise ValueError("A legacy colormap must contain at least two RGB rows.")
    data = data[:, :3]
    if not np.all(np.isfinite(data)) or np.min(data) < 0:
        raise ValueError("Legacy RGB values must be finite and non-negative.")

    maximum = float(np.max(data))
    if maximum <= 1.0:
        divisor = 1.0
    elif maximum <= 255.0:
        divisor = 255.0
    elif maximum <= 65025.0:
        # Historical AngstromPro files use 255 * 255 as their full scale.
        divisor = 65025.0
    elif maximum <= 65535.0:
        divisor = 65535.0
    else:
        raise ValueError("Legacy RGB values exceed the supported 16-bit range.")
    return np.clip(data / divisor, 0.0, 1.0)


def load_legacy_txt_colormap(path: Path, name: str | None = None):
    """Load an AngstromPro legacy tab-delimited ``.txt`` colormap."""
    data = np.loadtxt(path, delimiter="\t", skiprows=1)
    rgb = _normalise_legacy_rgb(data)
    cmap_name = name or Path(path).stem
    positions = np.linspace(0.0, 1.0, len(rgb))
    channel_data = {
        channel: [
            (positions[index], rgb[index, column], rgb[index, column])
            for index in range(len(rgb))
        ]
        for column, channel in enumerate(("red", "green", "blue"))
    }
    return colors.LinearSegmentedColormap(cmap_name, channel_data, N=256)


def write_legacy_txt_colormap(
    path: Path,
    name: str,
    anchors: Iterable[Mapping[str, object]],
) -> None:
    """Export a sampled colormap in the historical AngstromPro text format."""
    cmap = colormap_from_anchors(name, anchors, size=4096)
    rgb = np.clip(
        np.round(cmap(np.linspace(0.0, 1.0, 256))[:, :3] * 65025.0),
        0,
        65025,
    ).astype(int)
    with Path(path).open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(f"{name}[][0]\t{name}[][1]\t{name}[][2]\n")
        for red, green, blue in rgb:
            stream.write(f"{red}\t{green}\t{blue}\n")


def user_colormaps_dir(*, create: bool = True) -> Path:
    """Return ``<UserDataFolder>/colormaps``."""
    directory = user_data_subpath("colormaps")
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


class ColormapCatalog(QtCore.QObject):
    """Central source-aware catalog backed by Matplotlib's registry."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._presets_loaded = False
        self._preset_records: dict[str, ColormapRecord] = {}
        self._user_records: dict[str, ColormapRecord] = {}
        self._registered_user_names: set[str] = set()
        self._loaded_user_dir: Path | None = None

    def register_all(self) -> None:
        """Register packaged presets and managed user colormaps."""
        changed = False
        if not self._presets_loaded:
            changed = self._register_presets() or changed

        try:
            directory = user_colormaps_dir()
        except RuntimeError:
            directory = None
        if directory != self._loaded_user_dir:
            changed = self._reload_user_colormaps(directory) or changed
        if changed:
            self.changed.emit()

    def reload_user_colormaps(self) -> None:
        """Rescan the managed user folder and notify open source pickers."""
        if not self._presets_loaded:
            self._register_presets()
        try:
            directory = user_colormaps_dir()
        except RuntimeError:
            directory = None
        self._reload_user_colormaps(directory)
        self.changed.emit()

    def names(self, source: str) -> list[str]:
        self.register_all()
        if source == SOURCE_ANGSTROMPRO:
            return sorted(self._preset_records, key=str.casefold)
        if source == SOURCE_USER:
            return sorted(self._user_records, key=str.casefold)
        if source == SOURCE_MATPLOTLIB:
            explicit = set(self._preset_records) | set(self._user_records)
            return sorted(
                (name for name in matplotlib.colormaps if name not in explicit),
                key=str.casefold,
            )
        raise ValueError(f"Unknown colormap source: {source}")

    def source_for_name(self, name: str) -> str | None:
        self.register_all()
        if name in self._user_records:
            return SOURCE_USER
        if name in self._preset_records:
            return SOURCE_ANGSTROMPRO
        if name in matplotlib.colormaps:
            return SOURCE_MATPLOTLIB
        return None

    def save_user_colormap(
        self,
        name: str,
        anchors: Iterable[Mapping[str, object]],
        *,
        overwrite: bool = False,
    ) -> Path:
        """Save a versioned anchor-based map into the managed user folder."""
        self.register_all()
        clean_name = str(name).strip()
        if not clean_name or any(ord(character) < 32 for character in clean_name):
            raise ValueError("Enter a non-empty colormap name without control characters.")
        normalised = _normalise_anchors(anchors)

        conflict = self._find_name_conflict(clean_name)
        existing: ColormapRecord | None = None
        if conflict is not None:
            if (
                overwrite
                and conflict.source == SOURCE_USER
                and conflict.name == clean_name
            ):
                existing = conflict
            else:
                raise ColormapNameConflictError(clean_name, conflict)

        directory = user_colormaps_dir()
        if (
            existing is not None
            and existing.path is not None
            and existing.path.name.lower().endswith(".cmap.json")
        ):
            destination = existing.path
        else:
            destination = self._new_user_path(directory, clean_name)

        payload = {
            "format": USER_COLORMAP_FORMAT,
            "version": USER_COLORMAP_VERSION,
            "name": clean_name,
            "anchors": normalised,
        }
        temporary = destination.with_name(
            f".{destination.name}.{uuid4().hex}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, destination)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

        self.reload_user_colormaps()
        return destination

    def _register_presets(self) -> bool:
        changed = False
        for path in sorted(
            _BUNDLED_DIR.glob("*.txt"),
            key=lambda item: item.stem.casefold(),
        ):
            name = path.stem
            self._preset_records[name] = ColormapRecord(
                name=name,
                source=SOURCE_ANGSTROMPRO,
                path=path,
            )
            if name in matplotlib.colormaps:
                log.warning(
                    "AngstromPro preset %s collides with an existing Matplotlib colormap; "
                    "the existing registration is being retained.",
                    name,
                )
                continue
            try:
                matplotlib.colormaps.register(
                    load_legacy_txt_colormap(path, name),
                    name=name,
                )
                changed = True
            except Exception as exc:
                log.warning("Could not load AngstromPro preset %s: %s", name, exc)
        self._presets_loaded = True
        return changed

    def _reload_user_colormaps(self, directory: Path | None) -> bool:
        previous = set(self._user_records)
        for name in self._registered_user_names:
            try:
                matplotlib.colormaps.unregister(name)
            except (KeyError, ValueError):
                pass
        self._registered_user_names.clear()
        self._user_records.clear()
        self._loaded_user_dir = directory

        if directory is None:
            return bool(previous)

        json_paths = sorted(
            directory.glob("*.cmap.json"),
            key=lambda item: item.name.casefold(),
        )
        txt_paths = sorted(
            directory.glob("*.txt"),
            key=lambda item: item.name.casefold(),
        )
        for path in [*json_paths, *txt_paths]:
            try:
                if path.name.lower().endswith(".cmap.json"):
                    name, cmap = self._load_user_json(path)
                else:
                    name = path.stem
                    cmap = load_legacy_txt_colormap(path, name)
                if name in self._user_records:
                    # Versioned JSON takes precedence over a same-named legacy export.
                    if path.suffix.lower() != ".txt":
                        log.warning("Duplicate user colormap name %s in %s", name, path)
                    continue
                conflict = self._find_name_conflict(name, include_users=False)
                if conflict is not None:
                    log.warning(
                        "Ignoring user colormap %s because it conflicts with %s (%s)",
                        path,
                        conflict.name,
                        SOURCE_LABELS.get(conflict.source, conflict.source),
                    )
                    continue
                matplotlib.colormaps.register(cmap, name=name)
                self._registered_user_names.add(name)
                self._user_records[name] = ColormapRecord(
                    name=name,
                    source=SOURCE_USER,
                    path=path,
                )
            except Exception as exc:
                log.warning("Could not load user colormap %s: %s", path, exc)
        return previous != set(self._user_records)

    @staticmethod
    def _load_user_json(path: Path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("format") != USER_COLORMAP_FORMAT:
            raise ValueError("Not an AngstromPro colormap file.")
        if payload.get("version") != USER_COLORMAP_VERSION:
            raise ValueError(
                f"Unsupported colormap version: {payload.get('version')!r}"
            )
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("The colormap name is missing.")
        anchors = _normalise_anchors(payload.get("anchors", []))
        return name, colormap_from_anchors(name, anchors)

    def _find_name_conflict(
        self,
        name: str,
        *,
        include_users: bool = True,
    ) -> ColormapRecord | None:
        folded = name.casefold()
        records = list(self._preset_records.values())
        if include_users:
            records.extend(self._user_records.values())
        for record in records:
            if record.name.casefold() == folded:
                return record
        for registered_name in matplotlib.colormaps:
            if registered_name.casefold() == folded:
                return ColormapRecord(registered_name, SOURCE_MATPLOTLIB)
        return None

    @staticmethod
    def _new_user_path(directory: Path, name: str) -> Path:
        stem = _INVALID_FILENAME_CHARS.sub("_", name).strip(" .") or "colormap"
        stem = stem[:100].rstrip(" .") or "colormap"
        if stem.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_STEMS:
            stem += "_"
        candidate = directory / f"{stem}.cmap.json"
        if not candidate.exists():
            return candidate
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        candidate = directory / f"{stem}-{digest}.cmap.json"
        index = 2
        while candidate.exists():
            candidate = directory / f"{stem}-{digest}-{index}.cmap.json"
            index += 1
        return candidate


_catalog: ColormapCatalog | None = None


def get_colormap_catalog() -> ColormapCatalog:
    global _catalog
    if _catalog is None:
        _catalog = ColormapCatalog()
    return _catalog


def register_all() -> None:
    """Compatibility entry point used by existing viewers."""
    get_colormap_catalog().register_all()
