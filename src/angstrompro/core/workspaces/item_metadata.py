"""Portable, non-executable item metadata, including numerical arrays."""

from __future__ import annotations

import json
import numpy as np


def metadata_dumps(value) -> str:
    def encode(obj):
        if isinstance(obj, np.ndarray):
            if obj.dtype.hasobject:
                raise TypeError("Object arrays cannot be stored as item metadata")
            return {
                "__ndarray__": obj.tolist(),
                "dtype": str(obj.dtype),
                "shape": list(obj.shape),
            }
        if isinstance(obj, np.generic):
            return obj.item()
        raise TypeError(f"Unsupported metadata value: {type(obj).__name__}")

    return json.dumps(value, default=encode, ensure_ascii=False)


def metadata_loads(text: str):
    def decode(obj):
        if set(obj) in ({"__ndarray__", "dtype"}, {"__ndarray__", "dtype", "shape"}):
            dtype = np.dtype(obj["dtype"])
            if dtype.hasobject:
                raise ValueError("Object arrays cannot be loaded as item metadata")
            value = np.asarray(obj["__ndarray__"], dtype=dtype)
            return value.reshape(obj["shape"]) if "shape" in obj else value
        return obj

    return json.loads(text, object_hook=decode)


def remap_item_references(value, identifiers: dict[str, str]):
    """Remap explicit item-reference fields without changing ordinary strings."""
    if isinstance(value, dict):
        return {
            key: identifiers.get(child, child)
            if key == "item_id" and isinstance(child, str)
            else remap_item_references(child, identifiers)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [remap_item_references(child, identifiers) for child in value]
    if isinstance(value, tuple):
        return tuple(remap_item_references(child, identifiers) for child in value)
    return value
