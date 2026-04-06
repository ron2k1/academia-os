"""Load and validate configuration files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar, overload

from pydantic import BaseModel, ValidationError

from src.config.schemas import ClassesConfig, ModelsConfig

T = TypeVar("T", bound=BaseModel)

CONFIG_TYPE_MAP: dict[str, type[BaseModel]] = {
    "classes": ClassesConfig,
    "models": ModelsConfig,
}


def _read_json(path: Path) -> dict:
    """Read and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _detect_config_type(path: Path) -> str:
    """Detect configuration type from the file name.

    Looks for 'classes' or 'models' in the filename stem.

    Args:
        path: Path to the configuration file.

    Returns:
        Config type key ('classes' or 'models').

    Raises:
        ValueError: If the config type cannot be determined.
    """
    stem = path.stem.lower()
    for key in CONFIG_TYPE_MAP:
        if key in stem:
            return key
    raise ValueError(
        f"Cannot detect config type from filename '{path.name}'. "
        f"Expected one of: {list(CONFIG_TYPE_MAP.keys())}"
    )


@overload
def load_config(path: str | Path) -> ClassesConfig | ModelsConfig: ...


@overload
def load_config(path: str | Path, schema: type[T]) -> T: ...


def load_config(
    path: str | Path,
    schema: type[T] | None = None,
) -> BaseModel:
    """Load a configuration file with Pydantic validation.

    If no schema is provided, the config type is auto-detected from
    the filename (must contain 'classes' or 'models').

    Args:
        path: Path to the JSON config file.
        schema: Optional Pydantic model class to validate against.

    Returns:
        A validated Pydantic model instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the config type cannot be detected.
        ValidationError: If the data fails schema validation.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    data = _read_json(file_path)

    if schema is not None:
        return schema.model_validate(data)

    config_type = _detect_config_type(file_path)
    model_class = CONFIG_TYPE_MAP[config_type]
    return model_class.model_validate(data)
