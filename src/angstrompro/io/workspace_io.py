"""HDF5 archive IO for one module workspace.

The archive stores every supported WorkspaceItem in one file, including the
item wrapper metadata that the ordinary single-payload save path does not own.
Loading is intentionally additive: imported items are appended to the target
workspace and name collisions receive numeric suffixes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
import uuid

from angstrompro.core.data.annotation_data import (
    AnnotationData, deserialize_annotation, serialize_annotation,
)

if TYPE_CHECKING:
    from angstrompro.core.data.base import WorkspaceData
    from angstrompro.core.workspaces.workspace import Workspace
    from angstrompro.core.workspaces.workspace_item import WorkspaceItem


_TYPE_ID = "workspace"
_VERSION = 1


@dataclass
class ArchivedWorkspaceItem:
    """One fully loaded item waiting to be added to a Workspace."""

    name: str
    payload: WorkspaceData
    item_id: str = ""
    source_path: Path | None = None
    alias: str = ""
    annotations: dict[str, AnnotationData] = field(default_factory=dict)


@dataclass(frozen=True)
class SkippedWorkspaceItem:
    """An archive entry that could not be represented by this installation."""

    name: str
    type_id: str
    provider: str = ""
    payload_version: int = 1
    reason: str = "Unsupported payload type"


@dataclass
class WorkspaceArchive:
    """In-memory result of reading a workspace archive."""

    label: str = ""
    owner_id: str = ""
    items: list[ArchivedWorkspaceItem] = field(default_factory=list)
    skipped: list[SkippedWorkspaceItem] = field(default_factory=list)


def split_supported_items(
        items: list[WorkspaceItem],
) -> tuple[list[WorkspaceItem], list[WorkspaceItem]]:
    """Partition items according to the currently installed archive codecs."""

    _ensure_builtin_workspace_codecs()
    from angstrompro.io.angstrom_io import has_workspace_codec

    supported = []
    unsupported = []
    for item in items:
        target = supported if has_workspace_codec(item.type_id) else unsupported
        target.append(item)
    return supported, unsupported


def _ensure_builtin_workspace_codecs() -> None:
    from angstrompro.io import scene_plot_io, uds_io  # noqa: F401


def _write_payload(group, payload: WorkspaceData) -> None:
    from angstrompro.io.angstrom_io import get_workspace_codec

    codec = get_workspace_codec(payload.type_id)
    if codec is None:
        raise TypeError(f"Unsupported workspace payload type {payload.type_id!r}")
    codec.writer(group, payload)


def _read_payload(group, type_id: str) -> WorkspaceData:
    from angstrompro.io.angstrom_io import get_workspace_codec

    codec = get_workspace_codec(type_id)
    if codec is None:
        raise TypeError(f"Unsupported workspace payload type {type_id!r}")
    return codec.reader(group)


def _annotations_to_json(annotations: dict[str, AnnotationData]) -> str:
    return json.dumps(
        {role: serialize_annotation(annotation)
         for role, annotation in annotations.items()},
        ensure_ascii=False,
    )


def _annotations_from_json(raw: str) -> dict[str, AnnotationData]:
    if not raw:
        return {}
    return {
        role: deserialize_annotation(annotation)
        for role, annotation in json.loads(raw).items()
    }


def _attr_text(value, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def save_workspace(path: Path, workspace: Workspace) -> list[WorkspaceItem]:
    """Save supported items and return the unsupported items that were skipped.

    The target is replaced atomically only after the complete archive has been
    written successfully.
    """
    import h5py
    from angstrompro.io.angstrom_io import get_workspace_codec

    path = Path(path)
    supported, unsupported = split_supported_items(workspace.list_items())
    temp_path = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        with h5py.File(temp_path, "w") as archive:
            archive.attrs["type_id"] = _TYPE_ID
            archive.attrs["version"] = _VERSION
            archive.attrs["owner_id"] = workspace.owner_id
            archive.attrs["label"] = workspace.label
            archive.attrs["item_count"] = len(supported)

            items_group = archive.create_group("items", track_order=True)
            for index, item in enumerate(supported):
                codec = get_workspace_codec(item.type_id)
                if codec is None:
                    raise TypeError(
                        f"Workspace codec disappeared for type {item.type_id!r}"
                    )
                item_group = items_group.create_group(f"{index:08d}")
                item_group.attrs["name"] = item.name
                item_group.attrs["item_id"] = item.item_id
                item_group.attrs["type_id"] = item.type_id
                item_group.attrs["payload_provider"] = codec.provider
                item_group.attrs["payload_version"] = codec.version
                item_group.attrs["alias"] = item.alias
                item_group.attrs["source_path"] = (
                    str(item.source_path) if item.source_path is not None else ""
                )
                item_group.attrs["annotations"] = _annotations_to_json(
                    item.annotations)
                _write_payload(item_group.create_group("payload"), item.payload)

        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return unsupported


def _archive_group_sort_key(name: str) -> tuple[int, int | str]:
    return (0, int(name)) if name.isdigit() else (1, name)


def load_workspace(path: Path) -> WorkspaceArchive:
    """Read a workspace archive without mutating any live Workspace."""
    import h5py
    from angstrompro.io.angstrom_io import get_workspace_codec

    path = Path(path)
    result = WorkspaceArchive()
    _ensure_builtin_workspace_codecs()
    with h5py.File(path, "r") as archive:
        archive_type = _attr_text(archive.attrs.get("type_id"))
        if archive_type != _TYPE_ID:
            raise ValueError(
                f"{path.name} is not an AngstromPro workspace archive"
            )

        version = int(archive.attrs.get("version", 1))
        if version > _VERSION:
            raise ValueError(
                f"Workspace archive version {version} is newer than the "
                f"supported version {_VERSION}"
            )

        result.label = _attr_text(archive.attrs.get("label"))
        result.owner_id = _attr_text(archive.attrs.get("owner_id"))
        items_group = archive.get("items")
        if items_group is None:
            return result

        for key in sorted(items_group.keys(), key=_archive_group_sort_key):
            item_group = items_group[key]
            name = _attr_text(item_group.attrs.get("name"), key)
            type_id = _attr_text(item_group.attrs.get("type_id"))
            provider = _attr_text(item_group.attrs.get("payload_provider"))
            try:
                payload_version = int(
                    item_group.attrs.get("payload_version", 1))
            except (TypeError, ValueError):
                result.skipped.append(SkippedWorkspaceItem(
                    name,
                    type_id,
                    provider=provider,
                    reason="Invalid payload version metadata",
                ))
                continue
            codec = get_workspace_codec(type_id)
            if codec is None:
                result.skipped.append(SkippedWorkspaceItem(
                    name,
                    type_id,
                    provider=provider,
                    payload_version=payload_version,
                ))
                continue
            if provider and provider != codec.provider:
                result.skipped.append(SkippedWorkspaceItem(
                    name,
                    type_id,
                    provider=provider,
                    payload_version=payload_version,
                    reason=(
                        f"Archive provider {provider!r} does not match "
                        f"installed provider {codec.provider!r}"
                    ),
                ))
                continue
            if payload_version > codec.version:
                result.skipped.append(SkippedWorkspaceItem(
                    name,
                    type_id,
                    provider=provider or codec.provider,
                    payload_version=payload_version,
                    reason=(
                        f"Payload version {payload_version} is newer than "
                        f"installed codec version {codec.version}"
                    ),
                ))
                continue

            try:
                payload_group = item_group.get("payload")
                if payload_group is None:
                    raise ValueError("Missing payload group")
                payload = _read_payload(payload_group, type_id)
                payload.name = name
                source_text = _attr_text(item_group.attrs.get("source_path"))
                annotations = _annotations_from_json(
                    _attr_text(item_group.attrs.get("annotations"), "{}"))
                result.items.append(ArchivedWorkspaceItem(
                    name=name,
                    payload=payload,
                    item_id=_attr_text(item_group.attrs.get("item_id")),
                    source_path=Path(source_text) if source_text else None,
                    alias=_attr_text(item_group.attrs.get("alias")),
                    annotations=annotations,
                ))
            except Exception as exc:
                result.skipped.append(SkippedWorkspaceItem(
                    name=name,
                    type_id=type_id,
                    provider=provider or codec.provider,
                    payload_version=payload_version,
                    reason=str(exc),
                ))

    return result


def _next_available_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        return name
    index = 2
    while f"{name}_{index}" in used_names:
        index += 1
    return f"{name}_{index}"


def import_workspace(
        archive: WorkspaceArchive, workspace: Workspace,
) -> tuple[list[WorkspaceItem], dict[str, str]]:
    """Append loaded items, renaming collisions and preserving item metadata."""
    used_names = set(workspace.list_names())
    name_map: dict[str, str] = {}
    for archived in archive.items:
        new_name = _next_available_name(archived.name, used_names)
        name_map[archived.name] = new_name
        used_names.add(new_name)

    used_ids = {item.item_id for item in workspace.list_items()}
    imported: list[WorkspaceItem] = []
    for archived in archive.items:
        archived.payload.name = name_map[archived.name]
        for record in getattr(archived.payload, "proc_history", []):
            record.input_item_names = [
                name_map.get(input_name, input_name)
                for input_name in record.input_item_names
            ]

        item = workspace.add_item(
            payload=archived.payload,
            source_path=archived.source_path,
        )
        item.alias = archived.alias
        item.annotations = archived.annotations
        if archived.item_id and archived.item_id not in used_ids:
            item.item_id = archived.item_id
        used_ids.add(item.item_id)
        workspace.notify_changed(item.name)
        imported.append(item)

    renamed = {
        old_name: new_name for old_name, new_name in name_map.items()
        if old_name != new_name
    }
    return imported, renamed


__all__ = [
    "ArchivedWorkspaceItem",
    "SkippedWorkspaceItem",
    "WorkspaceArchive",
    "import_workspace",
    "load_workspace",
    "save_workspace",
    "split_supported_items",
]
