"""Tests for the BaseAgent abstract base class."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import BaseAgent, PROMPTS_DIR
from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool


class ConcreteAgent(BaseAgent):
    """Minimal concrete agent for testing the ABC."""

    agent_name = "test-concrete"

    def build_context(self) -> str:
        """Return a fixed test context."""
        return "test context"

    def run(self, message: str, **kwargs: object) -> dict:
        """Return a fixed test result."""
        return {"response": message}


class TestBaseAgentInit:
    """Tests for BaseAgent initialization."""

    def test_init_stores_config(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """Constructor stores all injected dependencies."""
        agent = ConcreteAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
        )
        assert agent.class_config is sample_class_config
        assert agent.vault is vault
        assert agent.spawner is mock_spawner
        assert agent.model == "test-model"

    def test_agent_name_set(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """Concrete subclass has the expected agent_name."""
        agent = ConcreteAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="m",
        )
        assert agent.agent_name == "test-concrete"


class TestBaseAgentAbstract:
    """Tests that BaseAgent cannot be instantiated directly."""

    def test_cannot_instantiate(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """BaseAgent raises TypeError when instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent(
                class_config=sample_class_config,
                vault=vault,
                spawner=mock_spawner,
                model="m",
            )


class TestLoadPrompt:
    """Tests for BaseAgent.load_prompt()."""

    def test_load_existing_prompt(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """load_prompt reads a .md file from the prompts directory."""
        agent = ConcreteAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="m",
        )
        # The tutor prompt should exist from Phase 2
        content = agent.load_prompt("tutor")
        assert len(content) > 0

    def test_load_missing_prompt_raises(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """load_prompt raises FileNotFoundError for missing prompts."""
        agent = ConcreteAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="m",
        )
        with pytest.raises(FileNotFoundError, match="Prompt not found"):
            agent.load_prompt("nonexistent-prompt-xyz")


class TestEmitEvents:
    """Tests for BaseAgent event emission methods."""

    @patch("src.agents.base.emit")
    def test_emit_spawn(
        self,
        mock_emit: MagicMock,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """emit_spawn calls emit with AGENT_SPAWN event type."""
        agent = ConcreteAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="m",
        )
        agent.emit_spawn(pid=999, context_size=512)
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0].value == "agent.spawn"
        assert call_args[1]["agent"] == "test-concrete"

    @patch("src.agents.base.emit")
    def test_emit_complete(
        self,
        mock_emit: MagicMock,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """emit_complete calls emit with AGENT_COMPLETE event type."""
        agent = ConcreteAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="m",
        )
        agent.emit_complete(wall_time_ms=150.0, exit_code=0)
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0].value == "agent.complete"
        assert call_args[0][1]["wall_time_ms"] == 150.0
