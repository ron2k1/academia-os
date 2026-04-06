"""Tests for the TestCreatorAgent."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.agents.test_creator import (
    TestCreatorAgent,
    _format_questions_for_prompt,
)
from src.agents.spawner import SpawnResult
from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool


class TestFormatQuestionsForPrompt:
    """Tests for the _format_questions_for_prompt helper."""

    def test_formats_numbered_list(self) -> None:
        """Creates a numbered list from question dicts."""
        questions = [
            {"question": "What is 2+2?", "difficulty": "easy", "topic": "math"},
            {"question": "Explain gravity", "difficulty": "hard", "topic": "physics"},
        ]
        result = _format_questions_for_prompt(questions)
        assert "1." in result
        assert "2." in result
        assert "[easy]" in result
        assert "(math)" in result

    def test_empty_questions(self) -> None:
        """Returns placeholder text for empty question list."""
        result = _format_questions_for_prompt([])
        assert "No questions provided" in result

    def test_missing_fields_use_defaults(self) -> None:
        """Uses 'unknown' difficulty and 'general' topic when missing."""
        questions = [{"question": "Q1"}]
        result = _format_questions_for_prompt(questions)
        assert "[unknown]" in result
        assert "(general)" in result

    def test_falls_back_to_text_key(self) -> None:
        """Falls back to 'text' key when 'question' is absent."""
        questions = [{"text": "Describe mitosis"}]
        result = _format_questions_for_prompt(questions)
        assert "Describe mitosis" in result


class TestTestCreatorAgent:
    """Tests for TestCreatorAgent (all spawner calls mocked)."""

    def _make_agent(
        self,
        config: ClassConfig,
        vault: VaultTool,
        spawner: MagicMock,
    ) -> TestCreatorAgent:
        """Create a TestCreatorAgent with test dependencies."""
        return TestCreatorAgent(
            class_config=config,
            vault=vault,
            spawner=spawner,
            model="test-model",
        )

    def test_run_with_questions(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() with provided questions assembles test directly."""
        mock_spawner.spawn.return_value = SpawnResult(
            stdout="# Practice Test\n1. Q1",
            stderr="",
            exit_code=0,
            wall_time_ms=150.0,
            pid=20,
        )
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        questions = [{"question": "What is a derivative?"}]
        result = agent.run("Make a calculus test", questions=questions)
        assert "test_markdown" in result
        assert "vault_path" in result
        assert result["question_count"] == 1

    def test_run_saves_to_vault(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() saves the assembled test to the vault."""
        mock_spawner.spawn.return_value = SpawnResult(
            stdout="Test content here",
            stderr="",
            exit_code=0,
            wall_time_ms=100.0,
            pid=21,
        )
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        questions = [{"question": "Q"}]
        result = agent.run("Test", questions=questions)
        assert vault.exists(result["vault_path"])
        content = vault.read(result["vault_path"])
        assert content == "Test content here"

    def test_run_without_questions_chains(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() without questions chains to QuestionCreatorAgent."""
        call_count = 0

        def side_effect(**kwargs: object) -> SpawnResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # QuestionCreatorAgent.run_spec call
                return SpawnResult(
                    stdout=json.dumps([{"question": "Generated Q"}]),
                    stderr="",
                    exit_code=0,
                    wall_time_ms=100.0,
                    pid=30,
                )
            # TestCreatorAgent._assemble_test call
            return SpawnResult(
                stdout="# Assembled Test",
                stderr="",
                exit_code=0,
                wall_time_ms=100.0,
                pid=31,
            )

        mock_spawner.spawn.side_effect = side_effect
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("Make a test", topics=["algebra"])
        assert result["question_count"] >= 1
        assert mock_spawner.spawn.call_count == 2

    def test_build_context_with_topics(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context includes topics.md when present."""
        vault.write("topics.md", "- Linear Algebra\n- Calculus")
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert "Linear Algebra" in ctx

    def test_build_context_with_existing_tests(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context includes last 3 existing test files."""
        vault.write("tests/old-test.md", "Old test content")
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert "Old test content" in ctx

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
