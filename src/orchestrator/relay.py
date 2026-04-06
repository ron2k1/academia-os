"""Relay module for post-processing agent responses."""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def relay_response(
    raw_response: str,
    strip_xml_blocks: bool = True,
    strip_code_fences: bool = False,
    max_length: int | None = None,
) -> str:
    """Post-process an agent response before returning to the user.

    Applies configurable transformations to clean up raw agent output.

    Args:
        raw_response: The raw text from the agent.
        strip_xml_blocks: Remove XML blocks like <memory_update>.
        strip_code_fences: Remove markdown code fences.
        max_length: Truncate to this many characters if set.

    Returns:
        Cleaned response string.
    """
    cleaned = raw_response
    if strip_xml_blocks:
        cleaned = _strip_xml_blocks(cleaned)
    if strip_code_fences:
        cleaned = _strip_code_fences(cleaned)
    cleaned = cleaned.strip()
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "\n\n[Truncated]"
    return cleaned


def _strip_xml_blocks(text: str) -> str:
    """Remove XML-style blocks from text (e.g., <memory_update>).

    Args:
        text: Input text.

    Returns:
        Text with XML blocks removed.
    """
    pattern = r"<(\w+)>.*?</\1>"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences, keeping inner content.

    Args:
        text: Input text with potential code fences.

    Returns:
        Text with fences removed but content preserved.
    """
    pattern = r"```\w*\n?(.*?)```"
    return re.sub(
        pattern, lambda m: m.group(1), text, flags=re.DOTALL
    )
