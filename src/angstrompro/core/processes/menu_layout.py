"""Validation helpers for user-defined Process menu layouts."""

from __future__ import annotations

import copy


LAYOUT_VERSION = 1


def empty_process_menu_layout() -> dict:
    return {"version": LAYOUT_VERSION, "groups": []}


def normalize_process_menu_layout(raw) -> dict:
    """Return a safe, ordered layout without duplicate process entries."""
    if not isinstance(raw, dict):
        return empty_process_menu_layout()

    raw_groups = raw.get("groups", [])
    if not isinstance(raw_groups, list):
        return empty_process_menu_layout()

    groups = []
    used_processes: set[str] = set()
    used_titles: set[str] = set()
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            continue
        base_title = str(raw_group.get("title", "")).strip()
        if not base_title:
            continue

        title = base_title
        suffix = 2
        while title.casefold() in used_titles:
            title = f"{base_title} ({suffix})"
            suffix += 1
        used_titles.add(title.casefold())

        raw_processes = raw_group.get("processes", [])
        processes = []
        if isinstance(raw_processes, list):
            for raw_name in raw_processes:
                if not isinstance(raw_name, str):
                    continue
                name = raw_name.strip()
                if not name or name in used_processes:
                    continue
                used_processes.add(name)
                processes.append(name)
        groups.append({"title": title, "processes": processes})

    return {"version": LAYOUT_VERSION, "groups": groups}


def normalize_process_menu_layouts(raw) -> dict[str, dict]:
    """Validate the per-module layout mapping while preserving module IDs."""
    if not isinstance(raw, dict):
        return {}
    layouts = {}
    for raw_module_id, raw_layout in raw.items():
        module_id = str(raw_module_id).strip()
        if not module_id:
            continue
        layout = normalize_process_menu_layout(raw_layout)
        if layout["groups"]:
            layouts[module_id] = layout
    return copy.deepcopy(layouts)


__all__ = [
    "LAYOUT_VERSION",
    "empty_process_menu_layout",
    "normalize_process_menu_layout",
    "normalize_process_menu_layouts",
]
