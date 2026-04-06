"""Tests for the TutorAgent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.tutor import TutorAgent, TutorResult
from src.agents.tutor_helpers import parse_memory_update, write_session
from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool


class TestParseMemoryUpdate:
    """Tests for the parse_memory_update helper."""

    def test_parses_valid_xml(self) -> None:
        """Extracts child elements from a valid memory_update block."""
        text = (
            "Hello\n"
            "<memory_update>\n"
            "  <topics_covered>Linear Algebra</topics_covered>\n"
            "  <key_concepts>Eigenvalues</key_concepts>\n"
            "</memory_update>\n"
            "Goodbye"
        )
        result = parse_memory_update(text)
        assert result is not None
        assert result["topics_covered"] == "Linear Algebra"
        assert result["key_concepts"] == "Eigenvalues"

    def test_returns_none_when_no_block(self) -> None:
        """Returns None when no memory_update block is present."""
        assert parse_memory_update("Just plain text") is None

    def test_returns_none_on_malformed_xml(self) -> None:
        """Returns None when the XML inside the block is malformed."""
        text = "<memory_update>not valid xml <<<<</memory_update>"
        assert parse_memory_update(text) is None

    def test_handles_empty_elements(self) -> None:
        """Handles elements with no text content."""
        text = (
            "<memory_update>"
            "<topics_covered></topics_covered>"
            "</memory_update>"
        )
        result = parse_memory_update(text)
        assert result is not None
        assert result["topics_covered"] == ""


class TestWriteSession:
    """Tests for the write_session helper."""

    def test_creates_session_file(self, vault: VaultTool) -> None:
        """write_session creates a file in sessions/ directory."""
        path = write_session(
            vault, "test-class", "What is calculus?", "It is math."
        )
        assert path.startswith("sessions/")
        assert path.endswith(".md")
        content = vault.read(path)
        assert "What is calculus?" in content
        assert "It is math." in content

    def test_session_has_header(self, vault: VaultTool) -> None:
        """Session file contains a formatted header."""
        path = write_session(vault, "c", "Q", "A")
        content = vault.read(path)
        assert "# Tutor Session" in content


class TestTutorAgent:
    """Tests for TutorAgent (all spawner calls mocked)."""

    def test_run_returns_result_dict(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() returns a dict with response, memory_update, session_file."""
        agent = TutorAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
        )
        result = agent.run("Explain derivatives")
        assert "response" in result
        assert "session_file" in result
        assert result["response"] == "Mock response"

    def test_run_writes_session(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() writes a session log to the vault."""
        agent = TutorAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
        )
        result = agent.run("What is entropy?")
        session_path = result["session_file"]
        assert vault.exists(session_path)

    def test_run_parses_memory_update(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """run() extracts memory_update when present in response."""
        from src.agents.spawner import SpawnResult

        mock_spawner.spawn.return_value = SpawnResult(
            stdout=(
                "Here is the answer.\n"
                "<memory_update>\n"
                "  <topics>Thermodynamics</topics>\n"
                "</memory_update>"
            ),
            stderr="",
            exit_code=0,
            wall_time_ms=200.0,
            pid=111,
        )
        agent = TutorAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="test-model",
        )
        result = agent.run("Explain heat transfer")
        assert result["memory_update"] is not None
        assert result["memory_update"]["topics"] == "Thermodynamics"

    def test_build_context_with_vault_files(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context loads _index.md, context.md, topics.md."""
        vault.write("_index.md", "Index content")
        vault.write("topics.md", "Topic list")
        agent = TutorAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="m",
        )
        ctx = agent.build_context()
        assert "Index content" in ctx
        assert "Topic list" in ctx

    def test_build_context_empty_vault(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
        mock_spawner: MagicMock,
    ) -> None:
        """build_context returns empty string with no vault files."""
        agent = TutorAgent(
            class_config=sample_class_config,
            vault=vault,
            spawner=mock_spawner,
            model="m",
        )
        ctx = agent.build_context()
        assert ctx == ""
