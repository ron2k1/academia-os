"""Shared pytest fixtures for AcademiaOS tests."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.agents.spawner import ClaudeSpawner, SpawnResult
from src.config.schemas import ClassConfig
from src.observability import events as _events_module
from src.observability.store import EventStore
from src.tools.vault import VaultTool

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CLASSES_PATH = FIXTURES_DIR / "sample_classes.json"
SAMPLE_MODELS_PATH = FIXTURES_DIR / "sample_models.json"
SAMPLE_VAULT_DIR = FIXTURES_DIR / "sample_vault"


@pytest.fixture()
def tmp_dir() -> Path:
    """Create and yield a temporary directory, cleaned up after test.

    Yields:
        Path to a fresh temporary directory.
    """
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def vault(tmp_dir: Path) -> VaultTool:
    """Create a VaultTool rooted in a temporary directory.

    Args:
        tmp_dir: Temporary directory fixture.

    Returns:
        A VaultTool instance for the 'test-class' vault.
    """
    return VaultTool("test-class", str(tmp_dir))


@pytest.fixture()
def event_store() -> EventStore:
    """Create an in-memory EventStore for testing.

    Sets the module-level default store so emit() works,
    and resets it after the test to avoid closed-db errors.

    Returns:
        A fresh in-memory EventStore.
    """
    store = EventStore(db_path=":memory:")
    _events_module.set_store(store)
    yield store
    store.close()
    _events_module._default_store = None


@pytest.fixture(autouse=True)
def _reset_event_store() -> None:
    """Reset the module-level event store after every test.

    Prevents 'Cannot operate on a closed database' errors when
    a test closes the store but the module-level singleton still
    references it.
    """
    yield
    _events_module._default_store = None


@pytest.fixture()
def sample_classes_path() -> Path:
    """Return the path to the sample classes fixture.

    Returns:
        Path to sample_classes.json.
    """
    return SAMPLE_CLASSES_PATH


@pytest.fixture()
def sample_models_path() -> Path:
    """Return the path to the sample models fixture.

    Returns:
        Path to sample_models.json.
    """
    return SAMPLE_MODELS_PATH


@pytest.fixture()
def sample_class_config() -> ClassConfig:
    """Create a sample ClassConfig for testing agents.

    Returns:
        A ClassConfig with test values.
    """
    return ClassConfig(
        id="test-class",
        name="Test Class",
        code="TEST",
    )


@pytest.fixture()
def mock_spawner() -> MagicMock:
    """Create a mock ClaudeSpawner that returns canned responses.

    The mock's spawn method returns a SpawnResult with configurable
    stdout. Default stdout is 'Mock response'.

    Returns:
        A MagicMock spec'd to ClaudeSpawner.
    """
    spawner = MagicMock(spec=ClaudeSpawner)
    spawner.spawn.return_value = SpawnResult(
        stdout="Mock response",
        stderr="",
        exit_code=0,
        wall_time_ms=100.0,
        pid=12345,
    )
    return spawner
