# -*- coding: utf-8 -*-
"""
ChannelManager — per-format channel configuration for multi-channel file formats.

Each file format that stores multiple channels (e.g. Nanonis .3ds, .sxm) can
register a FormatChannelConfig that declares:
  - The logical channels the app cares about (display_name shown in workspace)
  - An ordered alias list of substrings to search for in the raw file channel names
  - Whether each channel is loaded by default (pre-checked in the picker dialog)

The manager merges built-in defaults with user overrides stored in app config
under  data.channel_manager.<format_id>  and is accessible on AppContext.

User customisation
------------------
Users can:
  - Toggle load_by_default for any channel
  - Add new logical channels with custom aliases
  - Prepend aliases to existing channels so their lab's naming takes priority

These overrides are serialised as::

    config["data"]["channel_manager"]["nanonis_3ds"] = {
        "dI/dV": {
            "aliases": ["My dIdV channel", "LI Demod 1 X", ...],
            "load_by_default": true,
        },
        ...
    }
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from angstrompro.core.configs import ConfigManager

log = logging.getLogger(__name__)


@dataclass
class ChannelConfig:
    """One logical channel entry."""
    display_name:    str
    aliases:         list[str]      # ordered substrings; first match wins
    load_by_default: bool = True


@dataclass
class FormatChannelConfig:
    """All channel configs for one file format."""
    format_id: str
    channels:  list[ChannelConfig] = field(default_factory=list)
    auto_load: bool = False   # True = skip picker dialog, load default channels silently

    def resolve(self, file_channels: list[str]) -> list[tuple[ChannelConfig, int | None]]:
        """
        For each ChannelConfig return (config, file_channel_index | None).
        file_channel_index is None when no alias matched any file channel.
        """
        results: list[tuple[ChannelConfig, int | None]] = []
        for cc in self.channels:
            matched: int | None = None
            for alias in cc.aliases:
                for idx, fch in enumerate(file_channels):
                    if alias == fch:
                        matched = idx
                        break
                if matched is not None:
                    break
            results.append((cc, matched))
        return results

    def default_index(self, file_channels: list[str]) -> int:
        """
        Return the file-channel index of the first load_by_default channel
        that matched.  Falls back to 0.
        """
        for cc, idx in self.resolve(file_channels):
            if cc.load_by_default and idx is not None:
                return idx
        return 0


# ---------------------------------------------------------------------------
# Built-in format defaults — loaded from core/configs/defaults/data.py
# so the config system's diff/save logic works correctly.
# ---------------------------------------------------------------------------

def _builtin_from_defaults() -> dict[str, FormatChannelConfig]:
    from angstrompro.core.configs.defaults.data import DEFAULTS
    raw: dict = DEFAULTS.get("channel_manager", {})
    result: dict[str, FormatChannelConfig] = {}
    for fmt_id, fmt_dict in raw.items():
        auto_load = bool(fmt_dict.get("__auto_load__", False))
        channels = [
            ChannelConfig(
                display_name    = name,
                aliases         = list(info.get("aliases", [])),
                load_by_default = bool(info.get("load_by_default", False)),
            )
            for name, info in fmt_dict.items()
            if not name.startswith("__")
        ]
        result[fmt_id] = FormatChannelConfig(fmt_id, channels, auto_load)
    return result


_BUILTIN: dict[str, FormatChannelConfig] = _builtin_from_defaults()


# ---------------------------------------------------------------------------
# ChannelManager
# ---------------------------------------------------------------------------

class ChannelManager:
    """
    Singleton-style manager, held on AppContext.

    Merges built-in FormatChannelConfigs with user overrides from config.
    Call  reload(config)  after the user edits channel settings.
    """

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._cache: dict[str, FormatChannelConfig] = {}
        self._build_cache()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, format_id: str) -> FormatChannelConfig | None:
        """Return the merged FormatChannelConfig for format_id, or None."""
        return self._cache.get(format_id)

    def all_format_ids(self) -> list[str]:
        return list(self._cache.keys())

    def reload(self) -> None:
        """Rebuild cache after user edits."""
        self._cache.clear()
        self._build_cache()

    def save_format(self, format_id: str, channels: list[ChannelConfig],
                    auto_load: bool = False) -> None:
        """Persist a user-edited format config to app config and rebuild cache."""
        user_map = self._config.get("data", "channel_manager") or {}
        user_map[format_id] = {
            "__auto_load__": auto_load,
            **{
                cc.display_name: {
                    "aliases":         cc.aliases,
                    "load_by_default": cc.load_by_default,
                }
                for cc in channels
            }
        }
        self._config.set("data", "channel_manager", user_map)
        self._config.save_defaults()
        self.reload()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_cache(self) -> None:
        user_root: dict = self._config.get("data", "channel_manager") or {}

        # Start from built-ins, then overlay user overrides
        for fmt_id, builtin_cfg in _BUILTIN.items():
            user_fmt: dict = user_root.get(fmt_id, {})
            merged = self._merge(builtin_cfg, user_fmt)
            self._cache[fmt_id] = merged

        # Also include any purely user-defined formats not in _BUILTIN
        for fmt_id, user_fmt in user_root.items():
            if fmt_id not in self._cache:
                auto_load = bool(user_fmt.get("__auto_load__", False))
                channels = [
                    ChannelConfig(
                        display_name    = name,
                        aliases         = list(info.get("aliases", [])),
                        load_by_default = bool(info.get("load_by_default", False)),
                    )
                    for name, info in user_fmt.items()
                    if not name.startswith("__")
                ]
                self._cache[fmt_id] = FormatChannelConfig(fmt_id, channels, auto_load)

    @staticmethod
    def _merge(builtin: FormatChannelConfig,
               user_fmt: dict) -> FormatChannelConfig:
        """
        Merge user overrides onto a built-in FormatChannelConfig.

        User entries for existing display_names override aliases/load_by_default.
        User aliases are PREPENDED to built-in aliases so they win first.
        New user display_names are appended after built-in channels.
        The sentinel key __auto_load__ carries the auto_load flag.
        """
        auto_load = bool(user_fmt.get("__auto_load__", builtin.auto_load))
        result: list[ChannelConfig] = []
        seen: set[str] = set()

        for cc in builtin.channels:
            seen.add(cc.display_name)
            if cc.display_name in user_fmt:
                u = user_fmt[cc.display_name]
                user_aliases = list(u.get("aliases", []))
                existing = [a for a in cc.aliases if a not in user_aliases]  # exact dedup
                result.append(ChannelConfig(
                    display_name    = cc.display_name,
                    aliases         = user_aliases + existing,
                    load_by_default = bool(u.get("load_by_default", cc.load_by_default)),
                ))
            else:
                result.append(ChannelConfig(
                    display_name    = cc.display_name,
                    aliases         = list(cc.aliases),
                    load_by_default = cc.load_by_default,
                ))

        for name, info in user_fmt.items():
            if name.startswith("__"):
                continue   # skip sentinel keys
            if name not in seen:
                result.append(ChannelConfig(
                    display_name    = name,
                    aliases         = list(info.get("aliases", [])),
                    load_by_default = bool(info.get("load_by_default", False)),
                ))

        return FormatChannelConfig(builtin.format_id, result, auto_load)
