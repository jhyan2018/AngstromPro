"""Validate declarative startup slots without coupling core to any plugin."""

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class StartupPlan:
    slots: list[tuple[str, int]] = field(default_factory=list)
    workspaces: list[str] = field(default_factory=list)
    attachments: dict[tuple[str, int], tuple[str, str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def build_startup_plan(module_entries, workspace_entries, registered) -> StartupPlan:
    """Return valid actions plus errors. Invalid references never get retargeted.

    Slot numbers are local to this startup plan, not runtime instance suffixes.
    The same validation serves draft preferences and defensive startup loading.
    """
    plan = StartupPlan()
    counts = {}
    if not isinstance(module_entries, list):
        plan.errors.append("Startup modules must be a list.")
        module_entries = []
    duplicates = Counter(
        e.get("module_id")
        for e in module_entries
        if isinstance(e, dict) and isinstance(e.get("module_id"), str)
    )
    for entry in module_entries:
        if not isinstance(entry, dict):
            plan.errors.append("Invalid startup module entry.")
            continue
        mid, count = entry.get("module_id"), entry.get("count", 1)
        if not isinstance(mid, str) or not mid or mid == "main_workbench":
            plan.errors.append("Select a valid startup module (not Main Workbench).")
            continue
        cls = registered.get(mid)
        label = getattr(cls, "display_name", mid) or mid
        if cls is None:
            plan.errors.append(
                f"{label}: module is unavailable; enable its plugin or remove the entry."
            )
            continue
        if duplicates[mid] > 1:
            plan.errors.append(f"{label}: duplicate startup module entries.")
            continue
        limit = getattr(cls, "max_instances", None)
        limit = limit if limit is not None else 16
        if type(count) is not int or not 0 <= count <= limit:
            plan.errors.append(f"{label}: startup count must be between 0 and {limit}.")
            continue
        counts[mid] = count
        plan.slots.extend((mid, number) for number in range(1, count + 1))

    if not isinstance(workspace_entries, list):
        plan.errors.append("Startup shared workspaces must be a list.")
        return plan
    names = Counter(
        e["name"].strip().casefold()
        for e in workspace_entries
        if isinstance(e, dict) and isinstance(e.get("name"), str)
    )
    used_slots = set()
    for index, entry in enumerate(workspace_entries, 1):
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            plan.errors.append(f"Workspace {index}: enter a name.")
            continue
        name = entry["name"].strip()
        if not name:
            plan.errors.append(f"Workspace {index}: enter a name.")
            continue
        if names[name.casefold()] > 1:
            plan.errors.append(
                f"Workspace '{name}': name is already used in this startup setup."
            )
            continue
        plan.workspaces.append(name)
        attachments = entry.get("attachments", [])
        if not isinstance(attachments, list):
            plan.errors.append(f"Workspace '{name}': attachments must be a list.")
            continue
        for binding in attachments:
            if not isinstance(binding, dict):
                plan.errors.append(f"Workspace '{name}': invalid attachment.")
                continue
            mid = binding.get("module_id")
            number = binding.get("instance")
            if not isinstance(mid, str) or not mid:
                plan.errors.append(
                    f"Workspace '{name}': select a module for each attachment."
                )
                continue
            label = getattr(registered.get(mid), "display_name", mid) or mid
            prefix = f"Workspace '{name}', {label} instance {number}"
            if mid not in counts:
                plan.errors.append(
                    f"{prefix}: module is removed from startup or unavailable."
                )
                continue
            if type(number) is not int or not 1 <= number <= counts[mid]:
                plan.errors.append(
                    f"{prefix}: exceeds startup count {counts[mid]} or is invalid."
                )
                continue
            slot = (mid, number)
            if slot in used_slots:
                plan.attachments.pop(slot, None)
                plan.errors.append(f"{prefix}: instance is attached more than once.")
                continue
            used_slots.add(slot)
            destination = binding.get("active_destination", "shared")
            if destination not in ("private", "shared"):
                plan.errors.append(
                    f"{prefix}: choose Private or Shared as the active destination."
                )
                continue
            plan.attachments[slot] = (name, destination)
    return plan


class StartupWorkspaceSetup:
    """One-shot session setup. Never writes runtime changes back to config."""

    def __init__(self, context, plan: StartupPlan, report):
        self.context = context
        self.plan = plan
        self.report = report
        self.workspaces = {}

    def prepare(self):
        for error in self.plan.errors:
            self.report(error)
        for name in self.plan.workspaces:
            try:
                self.workspaces[name] = (
                    self.context.workspace_manager.create_shared_workspace(name)
                )
            except Exception as exc:
                self.report(f"Could not create startup workspace '{name}': {exc}")

    def create_slot(self, slot):
        mid, number = slot
        manager = self.context.module_manager
        existing = {item.instance_id for item in manager.list_instances()}
        try:
            instance = manager.create(mid, self.context)
        except Exception as exc:
            self.report(f"Could not create startup {mid} instance {number}: {exc}")
            return None
        binding = self.plan.attachments.get(slot)
        if binding is None:
            return instance
        if instance.instance_id in existing:
            self.report(
                f"Startup {mid} instance {number} reused an existing instance; attachment skipped."
            )
            return instance
        name, destination = binding
        workspace = self.workspaces.get(name)
        if workspace is None:
            self.report(
                f"Startup {mid} instance {number}: workspace '{name}' is unavailable."
            )
            return instance
        try:
            self.context.workspace_manager.attach_module(
                instance.instance_id, workspace.workspace_id
            )
            instance.set_active_workspace(
                instance.private_workspace.workspace_id
                if destination == "private"
                else workspace.workspace_id
            )
        except Exception as exc:
            self.report(
                f"Could not attach startup {mid} instance {number} to '{name}': {exc}"
            )
        return instance
