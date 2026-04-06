"""Tests for configuration Pydantic schemas."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from src.config.schemas import (
    AgentModel,
    ClassConfig,
    ClassesConfig,
    ClassTool,
    ModelsConfig,
    OrchestratorModel,
    ProviderType,
    SemesterConfig,
)


class TestClassTool:
    """Tests for the ClassTool enum."""

    def test_valid_values(self) -> None:
        """All expected tool values are present."""
        assert ClassTool.R_STUDIO == "r-studio"
        assert ClassTool.DOCX == "docx"
        assert ClassTool.PDF == "pdf"
        assert ClassTool.PYTHON == "python"
        assert ClassTool.LATEX == "latex"

    def test_from_string(self) -> None:
        """Enum can be constructed from a raw string."""
        assert ClassTool("r-studio") == ClassTool.R_STUDIO


class TestClassConfig:
    """Tests for ClassConfig model."""

    def test_minimal(self) -> None:
        """Construct with only required fields."""
        cfg = ClassConfig(id="test", name="Test", code="TST")
        assert cfg.id == "test"
        assert cfg.tools == []
        assert cfg.active is True

    def test_with_tools(self) -> None:
        """Construct with tool list."""
        cfg = ClassConfig(
            id="x", name="X", code="X",
            tools=["r-studio", "pdf"],
        )
        assert len(cfg.tools) == 2
        assert cfg.tools[0] == ClassTool.R_STUDIO

    def test_missing_required(self) -> None:
        """Omitting required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            ClassConfig(id="x")  # type: ignore[call-arg]


class TestSemesterConfig:
    """Tests for SemesterConfig model."""

    def test_valid(self) -> None:
        """Construct a valid semester."""
        sem = SemesterConfig(
            name="Spring 2026",
            start=date(2026, 1, 20),
            end=date(2026, 5, 15),
        )
        assert sem.archived is False

    def test_date_parsing(self) -> None:
        """String dates are coerced to date objects."""
        sem = SemesterConfig(
            name="Fall 2025",
            start="2025-09-01",
            end="2025-12-15",
        )
        assert isinstance(sem.start, date)


class TestClassesConfig:
    """Tests for the top-level ClassesConfig model."""

    def test_full(self) -> None:
        """Construct a complete classes config."""
        cfg = ClassesConfig(
            semester=SemesterConfig(
                name="Spring 2026",
                start="2026-01-20",
                end="2026-05-15",
            ),
            classes=[
                ClassConfig(id="a", name="A", code="A"),
            ],
        )
        assert len(cfg.classes) == 1


class TestModelsConfig:
    """Tests for the ModelsConfig model."""

    def test_full(self) -> None:
        """Construct a complete models config."""
        cfg = ModelsConfig(
            orchestrator=OrchestratorModel(
                provider=ProviderType.OPENROUTER,
                model="google/gemini-2.5-pro",
            ),
            agents={
                "tutor": AgentModel(cli_model="claude-sonnet-4-20250514"),
            },
        )
        assert cfg.orchestrator.provider == ProviderType.OPENROUTER
        assert "tutor" in cfg.agents

    def test_invalid_provider(self) -> None:
        """Invalid provider string raises ValidationError."""
        with pytest.raises(ValidationError):
            OrchestratorModel(provider="invalid", model="x")
