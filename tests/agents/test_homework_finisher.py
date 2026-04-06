"""Tests for the HomeworkFinisherAgent."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.agents.homework_finisher import (
    PASSES,
    HomeworkFinisherAgent,
    HomeworkResult,
)
from src.agents.spawner import SpawnResult
from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool


class TestHomeworkResult:
    """Tests for the HomeworkResult model."""

    def test_model_fields(self) -> None:
        """HomeworkResult has the expected fields."""
        result = HomeworkResult(
            final_output="Done",
            pass_outputs={"Draft": "d", "Review": "r"},
            vault_path="homework/test.md",
        )
        assert result.final_output == "Done"
        assert len(result.pass_outputs) == 2
        assert result.vault_path == "homework/test.md"

    def test_model_dump(self) -> None:
        """model_dump returns a dict with all fields."""
        result = HomeworkResult(
            final_output="Output",
            pass_outputs={"Draft": "d"},
            vault_path="hw.md",
        )
        dumped = result.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["final_output"] == "Output"


class TestHomeworkFinisherAgent:
    """Tests for HomeworkFinisherAgent (all spawner calls mocked)."""

    def _make_agent(
        self,
        config: ClassConfig,
        vault: VaultTool,
        spawner: MagicMock,
    ) -> HomeworkFinisherAgent:
        """Create a HomeworkFinisherAgent with test dependencies."""
        return HomeworkFinisherAgent(
            class_config=config,
            vault=vault,
            spawner=spawner,
            model="test-model",
        )

    def test_run_calls_spawner_five_times(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() calls spawner.spawn exactly 5 times (one per pass)."""
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        agent.run("Write about thermodynamics")
        assert mock_spawner.spawn.call_count == 5

    def test_run_returns_all_passes(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() returns pass_outputs with all 5 pass names."""
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("Essay on quantum mechanics")
        assert "pass_outputs" in result
        for pass_name in PASSES:
            assert pass_name in result["pass_outputs"]

    def test_run_final_output_is_review_pass(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() sets final_output to the output of the last pass."""
        call_idx = 0

        def side_effect(**kwargs: object) -> SpawnResult:
            nonlocal call_idx
            call_idx += 1
            return SpawnResult(
                stdout=f"Pass {call_idx} output",
                stderr="",
                exit_code=0,
                wall_time_ms=50.0,
                pid=call_idx,
            )

        mock_spawner.spawn.side_effect = side_effect
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("Write a report")
        assert result["final_output"] == "Pass 5 output"

    def test_run_saves_to_vault(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() saves final output to vault under homework/."""
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("My homework assignment")
        assert "vault_path" in result
        assert vault.exists(result["vault_path"])
        content = vault.read(result["vault_path"])
        assert "My homework assignment" in content

    def test_each_pass_feeds_previous_output(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """Each pass receives the previous pass output as content."""
        messages: list[str] = []

        def side_effect(**kwargs: object) -> SpawnResult:
            messages.append(str(kwargs.get("message", "")))
            return SpawnResult(
                stdout="Refined output",
                stderr="",
                exit_code=0,
                wall_time_ms=30.0,
                pid=1,
            )

        mock_spawner.spawn.side_effect = side_effect
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        agent.run("Original assignment")
        # First call has "Original assignment" in message
        assert "Original assignment" in messages[0]
        # Subsequent calls have "Refined output" from prior pass
        for msg in messages[1:]:
            assert "Refined output" in msg

    def test_build_context_with_vault_files(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context loads context.md, topics.md, and homework."""
        vault.write("context.md", "Class context info")
        vault.write("topics.md", "Topic list")
        vault.write("homework/old-hw.md", "Previous homework")
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert "Class context info" in ctx
        assert "Topic list" in ctx
        assert "Previous homework" in ctx

    def test_build_context_empty(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context returns empty string with no vault files."""
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert ctx == ""
