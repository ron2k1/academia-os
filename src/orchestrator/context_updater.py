"""Auto-generate and persist context after agent interactions.

After each agent completes, this module extracts key information from the
agent's response and updates the class vault so future invocations have
richer context.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from src.tools.vault import VaultTool

logger = logging.getLogger(__name__)

# Maximum number of recent session entries to retain in context.md
MAX_CONTEXT_ENTRIES = 50

# Maximum bytes for a single context entry summary
MAX_ENTRY_BYTES = 500


def update_context_after_interaction(
    vault: VaultTool,
    agent_type: str,
    user_message: str,
    agent_response: str,
) -> None:
    """Update vault context files after a successful agent interaction.

    Appends a timestamped summary to ``context.md`` and updates
    ``topics.md`` with any newly mentioned topics.

    Args:
        vault: VaultTool scoped to the relevant class.
        agent_type: The type of agent that ran (e.g., 'writer', 'coder').
        user_message: The original user message.
        agent_response: The agent's response text.
    """
    _append_context_entry(vault, agent_type, user_message, agent_response)
    _update_topics(vault, agent_response)
    logger.info(
        "Context updated for vault %s after %s interaction",
        vault.class_id,
        agent_type,
    )


def _append_context_entry(
    vault: VaultTool,
    agent_type: str,
    user_message: str,
    agent_response: str,
) -> None:
    """Append a new interaction summary to context.md.

    Each entry is a compact summary with timestamp, agent type, and
    a truncated version of the exchange. Old entries are pruned to
    keep the file under MAX_CONTEXT_ENTRIES entries.

    Args:
        vault: VaultTool for the class.
        agent_type: Agent type identifier.
        user_message: Original user message.
        agent_response: Agent response text.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = _summarize_exchange(user_message, agent_response)

    entry = (
        f"\n### {timestamp} -- {agent_type}\n"
        f"**Query**: {_truncate(user_message, 120)}\n"
        f"**Summary**: {summary}\n"
    )

    # Read existing context.md or start fresh
    try:
        existing = vault.read("context.md")
    except FileNotFoundError:
        existing = ""

    # Parse existing entries and append new one
    entries = _parse_context_entries(existing)
    entries.append(entry)

    # Prune to keep only most recent entries
    if len(entries) > MAX_CONTEXT_ENTRIES:
        entries = entries[-MAX_CONTEXT_ENTRIES:]

    # Reconstruct the file
    header = _extract_header(existing)
    content = header + "\n".join(entries)
    vault.write("context.md", content)


def _update_topics(vault: VaultTool, agent_response: str) -> None:
    """Extract and append new topics to topics.md.

    Looks for markdown headings, bold terms, and key phrases in the
    response to identify potential topics.

    Args:
        vault: VaultTool for the class.
        agent_response: Agent response text to scan for topics.
    """
    new_topics = _extract_topics(agent_response)
    if not new_topics:
        return

    try:
        existing = vault.read("topics.md")
    except FileNotFoundError:
        existing = ""

    existing_lower = existing.lower()
    added = []
    for topic in new_topics:
        if topic.lower() not in existing_lower:
            added.append(topic)

    if added:
        topics_line = "\n".join(f"- {t}" for t in added) + "\n"
        vault.write("topics.md", topics_line, append=True)
        logger.debug("Added %d new topics to vault %s", len(added), vault.class_id)


def _summarize_exchange(user_message: str, agent_response: str) -> str:
    """Create a compact summary of the exchange.

    Takes the first meaningful sentence or paragraph from the response.

    Args:
        user_message: Original user message.
        agent_response: Agent response text.

    Returns:
        A truncated summary string.
    """
    # Take first non-empty line of the response as summary
    lines = agent_response.strip().splitlines()
    summary_lines = []
    char_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if summary_lines:
                break
            continue
        # Skip markdown headings for summary
        if stripped.startswith("#"):
            continue
        summary_lines.append(stripped)
        char_count += len(stripped)
        if char_count >= MAX_ENTRY_BYTES:
            break

    summary = " ".join(summary_lines)
    return _truncate(summary, MAX_ENTRY_BYTES)


def _extract_topics(text: str) -> list[str]:
    """Extract potential topic names from agent response text.

    Looks for:
    - Markdown headings (## Topic Name)
    - Bold terms (**term**)

    Args:
        text: Agent response text.

    Returns:
        List of unique topic strings.
    """
    topics: list[str] = []
    seen: set[str] = set()

    # Extract markdown headings (level 2-4)
    for match in re.finditer(r"^#{2,4}\s+(.+)$", text, re.MULTILINE):
        topic = match.group(1).strip()
        key = topic.lower()
        if key not in seen and len(topic) < 80:
            topics.append(topic)
            seen.add(key)

    # Extract bold terms
    for match in re.finditer(r"\*\*([^*]+)\*\*", text):
        topic = match.group(1).strip()
        key = topic.lower()
        if key not in seen and 3 <= len(topic) <= 60:
            topics.append(topic)
            seen.add(key)

    return topics[:20]  # Cap at 20 topics per interaction


def _parse_context_entries(content: str) -> list[str]:
    """Parse context.md into individual entry blocks.

    Each entry starts with ``### <timestamp>``.

    Args:
        content: Full context.md content.

    Returns:
        List of entry strings.
    """
    if not content:
        return []

    entries: list[str] = []
    current: list[str] = []
    in_entry = False

    for line in content.splitlines(keepends=True):
        if line.strip().startswith("### "):
            if current and in_entry:
                entries.append("".join(current))
            current = [line]
            in_entry = True
        elif in_entry:
            current.append(line)

    if current and in_entry:
        entries.append("".join(current))

    return entries


def _extract_header(content: str) -> str:
    """Extract the header portion of context.md (before first ### entry).

    Args:
        content: Full context.md content.

    Returns:
        Header string, or default header if empty.
    """
    if not content:
        return "# Context\n\n"

    lines = content.splitlines(keepends=True)
    header_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("### "):
            break
        header_lines.append(line)

    header = "".join(header_lines)
    if not header.strip():
        return "# Context\n\n"
    return header


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed.

    Args:
        text: Input text.
        max_len: Maximum character length.

    Returns:
        Truncated text.
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
