"""Keyword-based intent router for mapping user messages to agents."""
from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)

# Keyword sets for each agent type, ordered by priority.
# More specific keywords are checked first to avoid false positives.
_KEYWORD_MAP: dict[str, list[str]] = {
    "test_creator": [
        "practice test",
        "practice exam",
        "mock test",
        "mock exam",
        "create a test",
        "make a test",
        "generate test",
        "generate exam",
        "exam prep",
    ],
    "question_creator": [
        "practice question",
        "practice problem",
        "generate question",
        "create question",
        "make question",
        "quiz me",
        "quiz question",
        "flashcard",
    ],
    "homework_finisher": [
        "homework",
        "assignment",
        "problem set",
        "pset",
        "finish my",
        "complete my",
        "help me write",
        "write up",
        "submit",
    ],
    "note_summarizer": [
        "summarize",
        "summary",
        "condense",
        "notes from",
        "lecture notes",
        "study notes",
        "key points",
        "tldr",
        "tl;dr",
    ],
    "tutor": [
        "explain",
        "help me understand",
        "teach me",
        "tutor",
        "what is",
        "how does",
        "why does",
        "walk me through",
        "concept",
    ],
}


class AgentType(str, Enum):
    """Supported agent types for routing."""

    TUTOR = "tutor"
    QUESTION_CREATOR = "question_creator"
    NOTE_SUMMARIZER = "note_summarizer"
    TEST_CREATOR = "test_creator"
    HOMEWORK_FINISHER = "homework_finisher"


def route_intent(message: str) -> AgentType:
    """Route a user message to the appropriate agent via keyword matching.

    Checks keywords in priority order (most specific first).
    Falls back to TUTOR if no keywords match.

    Args:
        message: The user's input message.

    Returns:
        The AgentType that should handle this message.
    """
    lower = message.lower()
    for agent_key, keywords in _KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword in lower:
                matched = AgentType(agent_key)
                logger.debug(
                    "Routed '%s...' -> %s (keyword: '%s')",
                    message[:40],
                    matched.value,
                    keyword,
                )
                return matched
    logger.debug(
        "No keyword match for '%s...', defaulting to TUTOR",
        message[:40],
    )
    return AgentType.TUTOR
