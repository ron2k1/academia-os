"""Tests for configuration loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.config.loader import load_config
from src.config.schemas import ClassesConfig, ModelsConfig


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_classes(self, sample_classes_path: Path) -> None:
        """Load and validate a classes config file."""
        cfg = load_config(sample_classes_path)
        assert isinstance(cfg, ClassesConfig)
        assert cfg.semester.name == "Spring 2026"
        assert len(cfg.classes) == 3

    def test_load_models(self, sample_models_path: Path) -> None:
        """Load and validate a models config file."""
        cfg = load_config(sample_models_path)
        assert isinstance(cfg, ModelsConfig)
        assert cfg.orchestrator.model == "google/gemini-2.5-pro"
        assert "tutor" in cfg.agents

    def test_load_with_explicit_schema(
        self, sample_classes_path: Path
    ) -> None:
        """Load with an explicitly supplied schema class."""
        cfg = load_config(sample_classes_path, ClassesConfig)
        assert isinstance(cfg, ClassesConfig)

    def test_file_not_found(self, tmp_dir: Path) -> None:
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_dir / "nope.json")

    def test_unknown_config_type(self, tmp_dir: Path) -> None:
        """Raise ValueError when config type cannot be detected."""
        bogus = tmp_dir / "unknown.json"
        bogus.write_text('{"key": "value"}', encoding="utf-8")
        with pytest.raises(ValueError, match="Cannot detect config type"):
            load_config(bogus)

    def test_invalid_json(self, tmp_dir: Path) -> None:
        """Raise JSONDecodeError for malformed JSON."""
        bad_file = tmp_dir / "classes_bad.json"
        bad_file.write_text("not json at all", encoding="utf-8")
        with pytest.raises(Exception):
            load_config(bad_file)

    def test_active_classes_filter(
        self, sample_classes_path: Path
    ) -> None:
        """Verify we can filter active classes from config."""
        cfg = load_config(sample_classes_path, ClassesConfig)
        active = [c for c in cfg.classes if c.active]
        assert len(active) == 2
