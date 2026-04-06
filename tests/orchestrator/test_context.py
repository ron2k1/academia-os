"""Tests for the context assembly module."""
from __future__ import annotations

from src.config.schemas import ClassConfig
from src.orchestrator.context import (
    DEFAULT_MAX_BYTES,
    ContextPayload,
    _apply_byte_budget,
    assemble_context,
)
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


class TestByteBudget:
    """Tests for byte-budget truncation in assemble_context."""

    def test_within_budget_no_truncation(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """Small vault content is not truncated."""
        vault.write("_index.md", "Small index")
        vault.write("context.md", "Small context")
        payload = assemble_context(sample_class_config, vault)
        assert "[...context truncated" not in payload.vault_context

    def test_exceeds_budget_truncated(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """Large vault content is truncated with marker."""
        big_content = "Line {i}: " + "x" * 80 + "\n"
        vault.write("context.md", "".join(
            f"Line {i}: " + "x" * 80 + "\n" for i in range(1000)
        ))
        payload = assemble_context(
            sample_class_config, vault, max_bytes=2000
        )
        assert "[...context truncated to fit budget...]" in payload.vault_context
        total_bytes = len(payload.to_string().encode("utf-8"))
        # Should be within budget (may be slightly under due to truncation)
        assert total_bytes <= 2000 + 100  # small tolerance for separators

    def test_max_bytes_zero_disables_budget(
        self,
        sample_class_config: ClassConfig,
        vault: VaultTool,
    ) -> None:
        """max_bytes=0 disables the byte budget entirely."""
        vault.write("context.md", "x" * 100_000)
        payload = assemble_context(
            sample_class_config, vault, max_bytes=0
        )
        assert "[...context truncated" not in payload.vault_context
        assert len(payload.vault_context) > 100_000

    def test_default_max_bytes_is_50k(self) -> None:
        """The default budget constant is 50,000 bytes."""
        assert DEFAULT_MAX_BYTES == 50_000

    def test_apply_byte_budget_preserves_newest(self) -> None:
        """Truncation removes from the beginning (oldest content)."""
        old_content = "### _index.md\n" + ("OLD LINE HERE\n" * 20) + "\n"
        new_content = "### context.md\nNEW LINE HERE\n"
        vault_text = old_content + new_content
        result = _apply_byte_budget(
            class_info="## Class: Test (T)",
            vault_context=vault_text,
            extra={},
            max_bytes=120,
        )
        # Newest content should be retained
        assert "NEW LINE HERE" in result
        # Marker should be present
        assert "[...context truncated" in result
