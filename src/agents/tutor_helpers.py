"""Helper functions for the TutorAgent."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from src.tools.vault import VaultTool


def parse_memory_update(text: str) -> dict | None:
    """Extract and parse a <memory_update> XML block from agent output.

    Args:
        text: Raw agent output that may contain a memory_update block.

    Returns:
        Dict with keys topics_covered, key_concepts, etc., or None.
    """
    pattern = r"<memory_update>(.*?)</memory_update>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    xml_str = f"<memory_update>{match.group(1)}</memory_update>"
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return None
    return {
        child.tag: (child.text or "").strip()
        for child in root
    }


def write_session(
    vault: VaultTool,
    class_id: str,
    user_message: str,
    response: str,
) -> str:
    """Write a tutor session log to the vault.

    Args:
        vault: VaultTool instance scoped to the class.
        class_id: Class identifier for naming.
        user_message: The original user message.
        response: The agent's full response.

    Returns:
        The vault-relative path where the session was written.
    """
    now = datetime.now(timezone.utc)
    filename = f"sessions/{now.strftime('%Y%m%d-%H%M%S')}.md"
    content = (
        f"# Tutor Session - {now.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"## Question\n{user_message}\n\n"
        f"## Response\n{response}\n"
    )
    vault.write(filename, content)
    return filename
