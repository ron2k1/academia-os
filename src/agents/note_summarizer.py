"""Note Summarizer agent for condensing academic material."""
from __future__ import annotations

import logging

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class NoteSummarizerAgent(BaseAgent):
    """Summarizes academic notes and lecture material.

    Reads existing summaries from the vault for cross-referencing,
    then produces structured study-ready notes via the Claude CLI.
    """

    agent_name = "note-summarizer"

    def build_context(self) -> str:
        """Load existing summaries and topic index for cross-referencing.

        Returns:
            Assembled context string with existing summaries.
        """
        parts: list[str] = []
        if self.vault.exists("topics.md"):
            parts.append(
                f"## topics.md\n{self.vault.read('topics.md')}"
            )
        summary_files = self.vault.list("summaries/")
        for sf in summary_files[-5:]:
            try:
                name = sf.split("/")[-1] if "/" in sf else sf
                parts.append(
                    f"## {name}\n{self.vault.read(sf)}"
                )
            except FileNotFoundError:
                continue
        if parts:
            return "\n\n".join(parts)
        return ""

    def run(self, message: str, **kwargs: object) -> dict:
        """Summarize the provided academic material.

        Args:
            message: Raw notes, lecture transcript, or topic description.

        Returns:
            Dict with summary text and vault path where it was saved.
        """
        context = self.build_context()
        system_prompt = self.load_prompt("note-summarizer")
        result = self.spawner.spawn(
            message=message,
            system_prompt=system_prompt,
            model=self.model,
            context=context,
        )
        self.emit_complete(result.wall_time_ms, result.exit_code)
        vault_path = self._save_summary(message, result.stdout)
        return {
            "summary": result.stdout,
            "vault_path": vault_path,
        }

    def _save_summary(self, source: str, summary: str) -> str:
        """Save the generated summary to the vault.

        Args:
            source: Original source text (used for title extraction).
            summary: The generated summary markdown.

        Returns:
            Vault-relative path where the summary was written.
        """
        title_line = _extract_title(source)
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        filename = (
            f"summaries/{now.strftime('%Y%m%d-%H%M%S')}"
            f"-{_slugify(title_line)}.md"
        )
        self.vault.write(filename, summary)
        return filename


def _extract_title(text: str) -> str:
    """Extract a short title from the first line of the source text.

    Args:
        text: Source text.

    Returns:
        First 50 characters of the first non-empty line.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:50]
    return "untitled"


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug.

    Args:
        text: Input text.

    Returns:
        Lowercase alphanumeric slug with hyphens.
    """
    import re

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower())
    return slug.strip("-")[:40]
