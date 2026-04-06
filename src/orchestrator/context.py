"""Context assembly for orchestrator-level prompt injection."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool

logger = logging.getLogger(__name__)

# Default byte budget for assembled context (50 KB)
DEFAULT_MAX_BYTES = 50_000


@dataclass
class ContextPayload:
    """Assembled context payload for an agent invocation.

    Attributes:
        class_info: Class name and code for prompt injection.
        vault_context: Assembled vault content string.
        extra: Additional key-value context from the orchestrator.
    """

    class_info: str
    vault_context: str
    extra: dict[str, str] = field(default_factory=dict)

    def to_string(self) -> str:
        """Render the full context payload as a string.

        Returns:
            Formatted context string ready for prompt injection.
        """
        parts = [self.class_info]
        if self.vault_context:
            parts.append(self.vault_context)
        for key, value in self.extra.items():
            parts.append(f"## {key}\n{value}")
        return "\n\n".join(parts)


def assemble_context(
    class_config: ClassConfig,
    vault: VaultTool,
    extra: dict[str, str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> ContextPayload:
    """Assemble a complete context payload for agent invocation.

    Reads core vault files and combines with class config metadata.
    If the assembled payload exceeds ``max_bytes``, vault content is
    intelligently truncated (newest content kept, oldest trimmed first).

    Args:
        class_config: The class configuration.
        vault: VaultTool scoped to the class.
        extra: Optional additional context key-value pairs.
        max_bytes: Maximum total byte size for the assembled context.
            Defaults to DEFAULT_MAX_BYTES (50,000). Set to 0 to disable.

    Returns:
        A ContextPayload ready for injection.
    """
    class_info = (
        f"## Class: {class_config.name} ({class_config.code})"
    )

    # Read vault files in priority order (_index first, then topics, then context)
    # Context is largest and most trimmable, so we read it last
    vault_parts: list[str] = []
    for path in ("_index.md", "topics.md", "context.md"):
        if vault.exists(path):
            vault_parts.append(
                f"### {path}\n{vault.read(path)}"
            )

    vault_context = "\n\n".join(vault_parts)

    # Build extra section
    extra_dict = extra or {}

    # Apply byte budget if enabled
    if max_bytes > 0:
        vault_context = _apply_byte_budget(
            class_info, vault_context, extra_dict, max_bytes
        )

    return ContextPayload(
        class_info=class_info,
        vault_context=vault_context,
        extra=extra_dict,
    )


def _apply_byte_budget(
    class_info: str,
    vault_context: str,
    extra: dict[str, str],
    max_bytes: int,
) -> str:
    """Truncate vault context to fit within the byte budget.

    The strategy is:
    1. Calculate fixed overhead (class_info + extra sections).
    2. Allocate remaining bytes to vault_context.
    3. If vault_context exceeds its budget, truncate from the beginning
       (oldest content) and prepend a ``[truncated]`` marker.

    Args:
        class_info: The class info header string.
        vault_context: The assembled vault content.
        extra: Additional context key-value pairs.
        max_bytes: Total byte budget.

    Returns:
        Potentially truncated vault_context string.
    """
    # Calculate bytes used by non-vault parts
    overhead = len(class_info.encode("utf-8"))
    for key, value in extra.items():
        overhead += len(f"## {key}\n{value}".encode("utf-8"))
    # Account for separators
    overhead += 20  # Buffer for \n\n separators

    available = max_bytes - overhead
    if available < 100:
        logger.warning(
            "Byte budget nearly exhausted by overhead (%d bytes), "
            "vault context will be heavily truncated.",
            overhead,
        )
        available = 100

    vault_bytes = len(vault_context.encode("utf-8"))
    if vault_bytes <= available:
        return vault_context

    # Truncate from the beginning (oldest content)
    logger.info(
        "Vault context (%d bytes) exceeds budget (%d bytes), truncating.",
        vault_bytes,
        available,
    )
    marker = "[...context truncated to fit budget...]\n\n"
    target = available - len(marker.encode("utf-8"))

    # Encode, slice from the end, then decode safely
    encoded = vault_context.encode("utf-8")
    truncated_bytes = encoded[-target:]

    # Decode with error handling, find first clean line break
    truncated = truncated_bytes.decode("utf-8", errors="ignore")
    first_newline = truncated.find("\n")
    if first_newline > 0:
        truncated = truncated[first_newline + 1:]

    return marker + truncated
