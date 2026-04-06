"""Tests for the context updater module (auto-context after interactions)."""
from __future__ import annotations

from src.orchestrator.context_updater import (
    _extract_topics,
    _parse_context_entries,
    _summarize_exchange,
    _truncate,
    update_context_after_interaction,
)
from src.tools.vault import VaultTool


class TestUpdateContextAfterInteraction:
    """Integration tests for the full context update flow."""

    def test_creates_context_file(self, vault: VaultTool) -> None:
        """Creates context.md when it doesn't exist."""
        update_context_after_interaction(
            vault, "writer", "Summarize notes", "Here is your summary."
        )
        assert vault.exists("context.md")

    def test_appends_entry(self, vault: VaultTool) -> None:
        """Appends a timestamped entry to context.md."""
        update_context_after_interaction(
            vault, "tutor", "Explain calculus", "Calculus is the study of change."
        )
        content = vault.read("context.md")
        assert "### " in content
        assert "tutor" in content
        assert "Explain calculus" in content

    def test_multiple_entries(self, vault: VaultTool) -> None:
        """Multiple interactions create multiple entries."""
        update_context_after_interaction(
            vault, "writer", "First question", "First answer."
        )
        update_context_after_interaction(
            vault, "coder", "Second question", "Second answer."
        )
        content = vault.read("context.md")
        assert content.count("### ") == 2

    def test_creates_topics_file(self, vault: VaultTool) -> None:
        """Extracts topics from response into topics.md."""
        update_context_after_interaction(
            vault,
            "researcher",
            "Tell me about ML",
            "## Machine Learning\nML is a branch of AI.\n\n**Neural Networks** are key.",
        )
        assert vault.exists("topics.md")
        topics = vault.read("topics.md")
        assert "Machine Learning" in topics

    def test_no_duplicate_topics(self, vault: VaultTool) -> None:
        """Does not add topics that already exist."""
        vault.write("topics.md", "- Machine Learning\n")
        update_context_after_interaction(
            vault,
            "tutor",
            "Tell me more about ML",
            "## Machine Learning\nMore details on ML.",
        )
        topics = vault.read("topics.md")
        count = topics.lower().count("machine learning")
        assert count == 1


class TestSummarizeExchange:
    """Tests for _summarize_exchange helper."""

    def test_basic_summary(self) -> None:
        """Extracts first paragraph as summary."""
        response = "This is the answer.\nWith more detail.\n\nSecond paragraph."
        result = _summarize_exchange("question", response)
        assert "This is the answer" in result

    def test_skips_headings(self) -> None:
        """Skips markdown headings in summary."""
        response = "# Big Heading\nActual content here."
        result = _summarize_exchange("q", response)
        assert "Big Heading" not in result
        assert "Actual content" in result

    def test_truncates_long_response(self) -> None:
        """Truncates very long summaries."""
        response = "A" * 1000
        result = _summarize_exchange("q", response)
        assert len(result) <= 503  # MAX_ENTRY_BYTES + "..."


class TestExtractTopics:
    """Tests for _extract_topics helper."""

    def test_extracts_headings(self) -> None:
        """Extracts level 2-4 headings as topics."""
        text = "## First Topic\nContent\n### Second Topic\nMore"
        topics = _extract_topics(text)
        assert "First Topic" in topics
        assert "Second Topic" in topics

    def test_extracts_bold_terms(self) -> None:
        """Extracts bold terms as topics."""
        text = "The **Neural Network** is important for **Deep Learning**."
        topics = _extract_topics(text)
        assert "Neural Network" in topics
        assert "Deep Learning" in topics

    def test_caps_at_twenty(self) -> None:
        """Caps extracted topics at 20."""
        text = "\n".join(f"## Topic {i}" for i in range(30))
        topics = _extract_topics(text)
        assert len(topics) == 20

    def test_ignores_short_bold(self) -> None:
        """Ignores bold terms shorter than 3 chars."""
        text = "This is **ab** and **ok term** here."
        topics = _extract_topics(text)
        assert "ab" not in topics
        assert "ok term" in topics

    def test_no_duplicates(self) -> None:
        """Same topic from heading and bold is not duplicated."""
        text = "## My Topic\nThe **My Topic** is great."
        topics = _extract_topics(text)
        assert topics.count("My Topic") == 1


class TestParseContextEntries:
    """Tests for _parse_context_entries helper."""

    def test_empty_content(self) -> None:
        """Returns empty list for empty content."""
        assert _parse_context_entries("") == []

    def test_single_entry(self) -> None:
        """Parses a single entry."""
        content = "# Header\n\n### 2024-01-01 -- writer\n**Query**: Hi\n"
        entries = _parse_context_entries(content)
        assert len(entries) == 1
        assert "writer" in entries[0]

    def test_multiple_entries(self) -> None:
        """Parses multiple entries."""
        content = (
            "### 2024-01-01 -- writer\nEntry 1\n"
            "### 2024-01-02 -- coder\nEntry 2\n"
        )
        entries = _parse_context_entries(content)
        assert len(entries) == 2


class TestTruncate:
    """Tests for _truncate helper."""

    def test_no_truncation_needed(self) -> None:
        """Short text is returned as-is."""
        assert _truncate("hello", 10) == "hello"

    def test_truncation_with_ellipsis(self) -> None:
        """Long text is truncated with ellipsis."""
        result = _truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_exact_length(self) -> None:
        """Text at exact max_len is not truncated."""
        assert _truncate("12345", 5) == "12345"
