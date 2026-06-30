from __future__ import annotations
from dataclasses import dataclass, field

_WIDGET_REGISTRY: dict[str, type] = {}


def register_widget_type(name: str, cls: type) -> None:
    """Register a custom control class for use in preferences schemas."""
    _WIDGET_REGISTRY[name] = cls


def get_widget_class(name: str) -> type | None:
    return _WIDGET_REGISTRY.get(name)


@dataclass
class PrefItem:
    key: str            # dot-path into config dict, e.g. "colormap.cmap_palette_list"
    label: str          # row label (ignored when full_width=True)
    widget: str         # "checkbox" | "number" | registered custom type name
    desc: str = ""      # optional muted subtitle under the label
    full_width: bool = False  # True → widget fills the whole section body (no label row)
    kwargs: dict = field(default_factory=dict)  # passed to the widget constructor


@dataclass
class PrefSection:
    title: str
    icon: str           # Tabler icon name without "ti-", e.g. "palette"
    items: list[PrefItem]
