"""Context assembly for orchestrator-level prompt injection."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.config.schemas import ClassConfig
from src.tools.vault import VaultTool

logger = logging.getLogger(__name__)


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
) -> ContextPayload:
    """Assemble a complete context payload for agent invocation.

    Reads core vault files and combines with class config metadata.

    Args:
        class_config: The class configuration.
        vault: VaultTool scoped to the class.
        extra: Optional additional context key-value pairs.

    Returns:
        A ContextPayload ready for injection.
    """
    class_info = (
        f"## Class: {class_config.name} ({class_config.code})"
    )
    vault_parts: list[str] = []
    for path in ("_index.md", "context.md", "topics.md"):
        if vault.exists(path):
            vault_parts.append(
                f"### {path}\n{vault.read(path)}"
            )
    vault_context = "\n\n".join(vault_parts)
    return ContextPayload(
        class_info=class_info,
        vault_context=vault_context,
        extra=extra or {},
    )
