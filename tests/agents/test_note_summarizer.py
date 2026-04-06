"""Tests for the NoteSummarizerAgent."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.agents.note_summarizer import (
    NoteSummarizerAgent,
    _extract_title,
    _slugify,
)
from src.agents.spawner import SpawnResult
from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool


class TestExtractTitle:
    """Tests for the _extract_title helper."""

    def test_extracts_first_line(self) -> None:
        """Returns the first 50 chars of the first non-empty line."""
        assert _extract_title("My Title\nBody") == "My Title"

    def test_truncates_long_title(self) -> None:
        """Truncates titles longer than 50 characters."""
        long_line = "A" * 100
        assert len(_extract_title(long_line)) == 50

    def test_skips_blank_lines(self) -> None:
        """Skips leading blank lines."""
        text = "\n\n\nActual title\nBody"
        assert _extract_title(text) == "Actual title"

    def test_returns_untitled_for_empty(self) -> None:
        """Returns 'untitled' for empty or whitespace-only text."""
        assert _extract_title("") == "untitled"
        assert _extract_title("   \n  \n  ") == "untitled"


class TestSlugify:
    """Tests for the _slugify helper."""

    def test_basic_slugification(self) -> None:
        """Converts text to lowercase with hyphens."""
        assert _slugify("Hello World") == "hello-world"

    def test_removes_special_chars(self) -> None:
        """Removes non-alphanumeric characters."""
        assert _slugify("Test (1) & More!") == "test-1-more"

    def test_truncates_to_40_chars(self) -> None:
        """Truncates slug to maximum 40 characters."""
        long_text = "a" * 100
        assert len(_slugify(long_text)) <= 40

    def test_strips_leading_trailing_hyphens(self) -> None:
        """Strips hyphens from start and end."""
        assert _slugify("--hello--") == "hello"


class TestNoteSummarizerAgent:
    """Tests for NoteSummarizerAgent (all spawner calls mocked)."""

    def _make_agent(
        self,
        config: ClassConfig,
        vault: VaultTool,
        spawner: MagicMock,
    ) -> NoteSummarizerAgent:
        """Create a NoteSummarizerAgent with test dependencies."""
        return NoteSummarizerAgent(
            class_config=config,
            vault=vault,
            spawner=spawner,
            model="test-model",
        )

    def test_run_returns_summary_and_path(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() returns a dict with summary text and vault_path."""
        mock_spawner.spawn.return_value = SpawnResult(
            stdout="## Key Concepts\n- Integration",
            stderr="",
            exit_code=0,
            wall_time_ms=200.0,
            pid=10,
        )
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("Lecture on calculus integration")
        assert "summary" in result
        assert "vault_path" in result
        assert result["summary"] == "## Key Concepts\n- Integration"

    def test_run_saves_to_vault(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() saves the summary to the summaries/ vault directory."""
        mock_spawner.spawn.return_value = SpawnResult(
            stdout="Summary content",
            stderr="",
            exit_code=0,
            wall_time_ms=100.0,
            pid=11,
        )
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        result = agent.run("Notes on thermodynamics")
        assert vault.exists(result["vault_path"])
        content = vault.read(result["vault_path"])
        assert content == "Summary content"

    def test_build_context_with_topics(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context includes topics.md when present."""
        vault.write("topics.md", "- Calculus\n- Algebra")
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert "Calculus" in ctx

    def test_build_context_with_existing_summaries(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context includes last 5 existing summaries."""
        vault.write("summaries/old.md", "Old summary content")
        agent = self._make_agent(
            sample_class_config, vault, mock_spawner
        )
        ctx = agent.build_context()
        assert "Old summary content" in ctx

    def test_build_context_empty_vault(
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
