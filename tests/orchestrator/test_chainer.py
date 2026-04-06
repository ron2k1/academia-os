"""Tests for the agent chainer module."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from src.agents.spawner import SpawnResult
from src.config.schemas import ClassConfig
from src.orchestrator.chainer import (
    ChainResult,
    ChainStep,
    run_test_creation_chain,
)
from src.tools.vault import VaultTool


class TestChainStep:
    """Tests for the ChainStep dataclass."""

    def test_defaults(self) -> None:
        """ChainStep has sensible defaults."""
        step = ChainStep(
            agent_name="test", input_summary="input"
        )
        assert step.output_summary == ""
        assert step.success is True

    def test_custom_values(self) -> None:
        """ChainStep accepts custom values."""
        step = ChainStep(
            agent_name="qa",
            input_summary="10 questions",
            output_summary="Generated 10",
            success=False,
        )
        assert step.agent_name == "qa"
        assert step.success is False


class TestChainResult:
    """Tests for the ChainResult dataclass."""

    def test_defaults(self) -> None:
        """ChainResult starts with empty steps and output."""
        result = ChainResult()
        assert result.steps == []
        assert result.final_output == {}

    def test_add_steps(self) -> None:
        """Steps can be appended to the chain result."""
        result = ChainResult()
        step = ChainStep(
            agent_name="test", input_summary="in"
        )
        result.steps.append(step)
        assert len(result.steps) == 1


class TestRunTestCreationChain:
    """Tests for run_test_creation_chain (all spawner calls mocked)."""

    def test_successful_chain(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """Successful chain produces 2 steps and final output."""
        call_idx = 0

        def side_effect(**kwargs: object) -> SpawnResult:
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return SpawnResult(
                    stdout=json.dumps([
                        {"question": "Q1", "answer": "A1"},
                    ]),
                    stderr="",
                    exit_code=0,
                    wall_time_ms=100.0,
                    pid=1,
                )
            return SpawnResult(
                stdout="# Practice Test\n1. Q1",
                stderr="",
                exit_code=0,
                wall_time_ms=100.0,
                pid=2,
            )

        mock_spawner.spawn.side_effect = side_effect
        result = run_test_creation_chain(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
            topics=["calculus"],
            question_count=1,
        )
        assert len(result.steps) == 2
        assert result.steps[0].agent_name == "question-creator"
        assert result.steps[1].agent_name == "test-creator"
        assert result.final_output != {}

    def test_chain_stops_on_question_failure(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """Chain stops after step 1 if question generation fails."""
        mock_spawner.spawn.side_effect = RuntimeError("API error")
        result = run_test_creation_chain(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
            topics=["physics"],
        )
        assert len(result.steps) == 1
        assert result.steps[0].success is False
        assert result.final_output == {}

    def test_chain_records_agent_names(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """Chain steps record the correct agent names."""
        call_idx = 0

        def side_effect(**kwargs: object) -> SpawnResult:
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return SpawnResult(
                    stdout=json.dumps([{"question": "Q"}]),
                    stderr="",
                    exit_code=0,
                    wall_time_ms=50.0,
                    pid=1,
                )
            return SpawnResult(
                stdout="Test assembled",
                stderr="",
                exit_code=0,
                wall_time_ms=50.0,
                pid=2,
            )

        mock_spawner.spawn.side_effect = side_effect
        result = run_test_creation_chain(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
            topics=["algebra"],
            question_count=1,
        )
        names = [s.agent_name for s in result.steps]
        assert names == ["question-creator", "test-creator"]

    def test_empty_questions_stops_chain(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """Chain stops if question generation returns empty list."""
        mock_spawner.spawn.return_value = SpawnResult(
            stdout="not valid json",
            stderr="",
            exit_code=0,
            wall_time_ms=50.0,
            pid=1,
        )
        result = run_test_creation_chain(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
            topics=["bio"],
        )
        assert len(result.steps) == 1
        assert result.steps[0].success is False
