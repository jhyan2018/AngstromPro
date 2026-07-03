from pathlib import Path

from angstrompro.app.user_data_folder import get_user_data_folder


def get_config_dir() -> Path | None:
    """Return <UserDataFolder>/config/, or None if the folder is not yet set."""
    root = get_user_data_folder()
    if root is None:
        return None
    d = root / "config"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_config_file() -> Path | None:
    """Return the config JSON path, or None if the user data folder is not yet set."""
    d = get_config_dir()
    return (d / "config.json") if d is not None else None
