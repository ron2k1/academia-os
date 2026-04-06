"""Shared pytest fixtures for AcademiaOS tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

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

    Returns:
        A fresh in-memory EventStore.
    """
    store = EventStore(db_path=":memory:")
    yield store
    store.close()


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
