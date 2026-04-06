"""Input validators for WebSocket and REST payloads."""
from __future__ import annotations

import re

# Maximum allowed message length (characters).
MAX_MESSAGE_LENGTH = 10_000

# Class IDs must be lowercase alphanumeric + hyphens, 1-64 chars.
_CLASS_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,63}$")

# Must match the AgentType enum values in src.orchestrator.router.
VALID_AGENT_TYPES: frozenset[str] = frozenset({
    "tutor",
    "question_creator",
    "note_summarizer",
    "test_creator",
    "homework_finisher",
})


def validate_message(content: str) -> str | None:
    """Validate a user message.

    Args:
        content: The raw message text.

    Returns:
        An error string if invalid, otherwise ``None``.
    """
    if not content or not content.strip():
        return "Message cannot be empty."
    if len(content) > MAX_MESSAGE_LENGTH:
        return (
            f"Message too long ({len(content):,} chars). "
            f"Maximum is {MAX_MESSAGE_LENGTH:,}."
        )
    return None


def validate_class_id(class_id: str) -> str | None:
    """Validate a class identifier.

    Must be 1-64 characters, lowercase alphanumeric with hyphens,
    and must not start with a hyphen.

    Args:
        class_id: The class ID to validate.

    Returns:
        An error string if invalid, otherwise ``None``.
    """
    if not class_id:
        return "Class ID cannot be empty."
    if not _CLASS_ID_RE.match(class_id):
        return (
            f"Invalid class ID '{class_id}'. "
            "Must be 1-64 lowercase alphanumeric characters or hyphens, "
            "starting with a letter or digit."
        )
    return None


def validate_agent_type(agent: str) -> str | None:
    """Validate an agent type string.

    Must be one of the registered agent types matching the
    ``AgentType`` enum in ``src.orchestrator.router``.

    Args:
        agent: The agent type string to validate.

    Returns:
        An error string if invalid, otherwise ``None``.
    """
    if agent not in VALID_AGENT_TYPES:
        return (
            f"Unknown agent type '{agent}'. "
            f"Valid types: {sorted(VALID_AGENT_TYPES)}"
        )
    return None
