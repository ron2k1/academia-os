"""Tests for the QuestionCreatorAgent."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from src.agents.question_creator import (
    QuestionCreatorAgent,
    QuestionSpec,
    _parse_questions_json,
)
from src.agents.spawner import SpawnResult
from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool


class TestQuestionSpec:
    """Tests for the QuestionSpec model."""

    def test_defaults(self) -> None:
        """QuestionSpec has sensible defaults."""
        spec = QuestionSpec(topics=["math"])
        assert spec.count == 5
        assert spec.difficulty == "medium"
        assert spec.format == "json"
        assert spec.include_solutions is True
        assert spec.style_reference is None

    def test_custom_values(self) -> None:
        """QuestionSpec accepts custom values."""
        spec = QuestionSpec(
            topics=["physics", "chem"],
            count=20,
            difficulty="hard",
        )
        assert spec.count == 20
        assert spec.difficulty == "hard"
        assert len(spec.topics) == 2


class TestParseQuestionsJson:
    """Tests for the _parse_questions_json helper."""

    def test_parse_bare_list(self) -> None:
        """Parses a bare JSON list of questions."""
        text = json.dumps([
            {"question": "What is 2+2?", "answer": "4"},
        ])
        result = _parse_questions_json(text)
        assert len(result) == 1
        assert result[0]["question"] == "What is 2+2?"

    def test_parse_dict_with_questions_key(self) -> None:
        """Parses a JSON dict containing a 'questions' key."""
        text = json.dumps({
            "questions": [
                {"question": "Q1"},
                {"question": "Q2"},
            ]
        })
        result = _parse_questions_json(text)
        assert len(result) == 2

    def test_parse_code_fenced_json(self) -> None:
        """Parses JSON embedded in a ```json code fence."""
        qs = [{"question": "Fenced Q"}]
        text = f"Here are questions:\n```json\n{json.dumps(qs)}\n```\n"
        result = _parse_questions_json(text)
        assert len(result) == 1
        assert result[0]["question"] == "Fenced Q"

    def test_parse_plain_code_fence(self) -> None:
        """Parses JSON embedded in a plain ``` code fence."""
        qs = [{"question": "Plain fence"}]
        text = f"```\n{json.dumps(qs)}\n```"
        result = _parse_questions_json(text)
        assert len(result) == 1

    def test_parse_invalid_json_returns_empty(self) -> None:
        """Invalid JSON returns an empty list."""
        result = _parse_questions_json("not json at all")
        assert result == []


class TestQuestionCreatorAgent:
    """Tests for QuestionCreatorAgent (all spawner calls mocked)."""

    def _make_agent(
        self,
        config: ClassConfig,
        vault: VaultTool,
        spawner: MagicMock,
    ) -> QuestionCreatorAgent:
        """Create a QuestionCreatorAgent with test dependencies."""
        return QuestionCreatorAgent(
            class_config=config,
            vault=vault,
            spawner=spawner,
            model="test-model",
        )

    def test_run_freeform(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() with a free-form message returns raw_json and questions."""
        questions = [{"question": "What is gravity?", "answer": "A force"}]
        mock_spawner.spawn.return_value = SpawnResult(
            stdout=json.dumps(questions),
            stderr="",
            exit_code=0,
            wall_time_ms=100.0,
            pid=1,
        )
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("Generate physics questions")
        assert "questions" in result
        assert len(result["questions"]) == 1

    def test_run_with_spec(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() with a QuestionSpec kwarg uses structured generation."""
        questions = [{"question": "Q1"}, {"question": "Q2"}]
        mock_spawner.spawn.return_value = SpawnResult(
            stdout=json.dumps(questions),
            stderr="",
            exit_code=0,
            wall_time_ms=100.0,
            pid=1,
        )
        spec = QuestionSpec(topics=["calculus"], count=2)
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("Make questions", spec=spec)
        assert len(result["questions"]) == 2

    def test_run_spec_returns_list(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run_spec() returns a list of question dicts."""
        questions = [{"question": "Q"}]
        mock_spawner.spawn.return_value = SpawnResult(
            stdout=json.dumps(questions),
            stderr="",
            exit_code=0,
            wall_time_ms=50.0,
            pid=2,
        )
        spec = QuestionSpec(topics=["algebra"], count=1)
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run_spec(spec)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_build_context_with_existing_questions(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context includes existing question files."""
        vault.write("questions/q1.json", '{"q": "old question"}')
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert "old question" in ctx

    def test_build_context_empty(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context returns empty string with no question files."""
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert ctx == ""
