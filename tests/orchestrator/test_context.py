"""Tests for the context assembly module."""
from __future__ import annotations

from src.config.schemas import ClassConfig
from src.orchestrator.context import ContextPayload, assemble_context
from src.tools.vault import VaultTool


class TestContextPayload:
    """Tests for the ContextPayload dataclass."""

    def test_to_string_basic(self) -> None:
        """to_string returns class info when vault context is empty."""
        payload = ContextPayload(
            class_info="## Class: Math 101 (MATH)",
            vault_context="",
        )
        result = payload.to_string()
        assert "Math 101" in result

    def test_to_string_with_vault_context(self) -> None:
        """to_string includes vault context when present."""
        payload = ContextPayload(
            class_info="## Class: CS (CS101)",
            vault_context="### topics.md\n- Algorithms",
        )
        result = payload.to_string()
        assert "CS101" in result
        assert "Algorithms" in result

    def test_to_string_with_extra(self) -> None:
        """to_string includes extra key-value pairs."""
        payload = ContextPayload(
            class_info="## Class: Bio (BIO)",
            vault_context="",
            extra={"session_history": "Previous Q&A"},
        )
        result = payload.to_string()
        assert "session_history" in result
        assert "Previous Q&A" in result

    def test_to_string_all_parts(self) -> None:
        """to_string combines all parts with double newlines."""
        payload = ContextPayload(
            class_info="## Class: Phys (PHY)",
            vault_context="### index\nIndex data",
            extra={"note": "Extra note"},
        )
        result = payload.to_string()
        parts = result.split("\n\n")
        assert len(parts) >= 3


class TestAssembleContext:
    """Tests for the assemble_context function."""

    def test_basic_assembly(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """Returns a ContextPayload with class info."""
        payload = assemble_context(sample_class_config, vault)
        assert isinstance(payload, ContextPayload)
        assert "Test Class" in payload.class_info
        assert "TEST" in payload.class_info

    def test_reads_vault_files(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """Reads _index.md, context.md, topics.md from vault."""
        vault.write("_index.md", "Index content")
        vault.write("context.md", "Context content")
        vault.write("topics.md", "Topics content")
        payload = assemble_context(sample_class_config, vault)
        assert "Index content" in payload.vault_context
        assert "Context content" in payload.vault_context
        assert "Topics content" in payload.vault_context

    def test_empty_vault(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """Returns empty vault_context when vault has no files."""
        payload = assemble_context(sample_class_config, vault)
        assert payload.vault_context == ""

    def test_extra_passed_through(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """Extra dict is passed through to the payload."""
        extra = {"user_history": "Previous interactions"}
        payload = assemble_context(
            sample_class_config, vault, extra=extra
        )
        assert payload.extra["user_history"] == "Previous interactions"

    def test_partial_vault_files(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """Only reads vault files that exist."""
        vault.write("topics.md", "Only topics")
        payload = assemble_context(sample_class_config, vault)
        assert "Only topics" in payload.vault_context
        assert "_index.md" not in payload.vault_context
