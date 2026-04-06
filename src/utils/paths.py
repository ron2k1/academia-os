"""Path resolution and directory creation utilities."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return PROJECT_ROOT


def get_config_dir() -> Path:
    """Return the absolute path to the config directory."""
    return PROJECT_ROOT / "config"


def get_vaults_root() -> Path:
    """Return the absolute path to the vaults root directory."""
    return PROJECT_ROOT / "vaults"


def get_classes_root() -> Path:
    """Return the absolute path to the classes root directory."""
    return PROJECT_ROOT / "classes"


def ensure_dir(path: Path) -> Path:
    """Create a directory (and parents) if it does not exist.

    Args:
        path: The directory path to ensure exists.

    Returns:
        The same path, guaranteed to exist.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative_path(base: Path, relative: str) -> Path:
    """Resolve a relative path within a base directory safely.

    Raises ValueError if the path tries to escape the base via '..'.

    Args:
        base: The base directory that must contain the result.
        relative: The relative path string to resolve.

    Returns:
        The resolved absolute path within base.

    Raises:
        ValueError: If the relative path contains '..' components.
    """
    if ".." in Path(relative).parts:
        raise ValueError(
            f"Path traversal not allowed: '{relative}' contains '..'"
        )
    resolved = (base / relative).resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError(
            f"Path '{relative}' resolves outside base directory"
        )
    return resolved
