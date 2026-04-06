"""Pydantic models for all configuration types."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Classes configuration
# ---------------------------------------------------------------------------

class ClassTool(str, Enum):
    """Tools available to a class."""

    R_STUDIO = "r-studio"
    DOCX = "docx"
    PDF = "pdf"
    PYTHON = "python"
    LATEX = "latex"


class ClassConfig(BaseModel):
    """Configuration for a single class."""

    id: str = Field(..., description="URL-safe slug, e.g. 'regression-methods'")
    name: str = Field(..., description="Human-readable class name")
    code: str = Field(..., description="Short code, e.g. 'REGM'")
    tools: list[ClassTool] = Field(default_factory=list)
    active: bool = True


class SemesterConfig(BaseModel):
    """Semester metadata."""

    name: str = Field(..., description="e.g. 'Spring 2026'")
    start: date
    end: date
    archived: bool = False


class ClassesConfig(BaseModel):
    """Top-level classes configuration file schema."""

    semester: SemesterConfig
    classes: list[ClassConfig]


# ---------------------------------------------------------------------------
# Models configuration
# ---------------------------------------------------------------------------

class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENROUTER = "openrouter"
    CLAUDE_CLI = "claude-cli"


class OrchestratorModel(BaseModel):
    """Configuration for the lead orchestrator model."""

    provider: ProviderType
    model: str
    notes: str = ""


class AgentModel(BaseModel):
    """Configuration for a sub-agent model."""

    cli_model: str
    notes: str = ""


class ModelsConfig(BaseModel):
    """Top-level models configuration file schema."""

    orchestrator: OrchestratorModel
    agents: dict[str, AgentModel]
