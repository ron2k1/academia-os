"""OpenClaw gateway client — routes orchestration calls through OpenClaw."""
from __future__ import annotations

import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

_AGENT_TYPES = {
    "tutor", "question-creator", "test-creator",
    "homework-finisher", "note-summarizer",
}

_ROUTING_PROMPT = """You are the lead orchestrator for AcademiaOS, an academic workspace.
Classify which sub-agent should handle the user's message.
Respond with EXACTLY ONE of these agent IDs (no other text):
- tutor           → explain concepts, answer questions, interactive learning
- question-creator → generate practice questions, quizzes
- test-creator    → create full practice exams or tests
- homework-finisher → complete assignments, problem sets, submit-ready work
- note-summarizer → summarize notes, create study sheets, flashcards

User message: {message}

Agent ID:"""


def route_via_openclaw(message: str, class_id: str = "") -> str:
    """Ask OpenClaw's main agent (via OpenRouter) which sub-agent to use.

    Falls back to keyword routing if OpenClaw is unavailable or times out.

    Args:
        message: The user's message to route.
        class_id: The class context (for logging).

    Returns:
        One of the valid agent type strings.
    """
    try:
        return _call_openclaw_agent(message)
    except Exception as exc:
        logger.warning(
            "OpenClaw routing unavailable (%s), falling back to keyword routing", exc
        )
        return _keyword_fallback(message)


def _call_openclaw_agent(message: str) -> str:
    """Call OpenClaw's main agent via CLI for routing decision.

    Args:
        message: The user's message.

    Returns:
        Agent type string from OpenClaw.

    Raises:
        RuntimeError: If the CLI call fails or returns unexpected output.
    """
    prompt = _ROUTING_PROMPT.format(message=message[:500])

    # Use openclaw CLI to send the routing prompt to the main agent
    openclaw_bin = _find_openclaw_binary()
    result = subprocess.run(
        [openclaw_bin, "agent", "--agent", "main", "--message", prompt],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"openclaw agent returned exit code {result.returncode}: {result.stderr[:200]}"
        )

    raw = result.stdout.strip().lower()
    logger.debug("OpenClaw routing response: %r", raw[:100])

    # Extract agent type from response
    for agent in _AGENT_TYPES:
        if agent in raw:
            return agent

    raise RuntimeError(f"Could not parse agent type from response: {raw[:100]!r}")


def _find_openclaw_binary() -> str:
    """Find the openclaw CLI binary path.

    Returns:
        Resolved binary path.

    Raises:
        RuntimeError: If openclaw is not found on PATH.
    """
    import shutil
    found = shutil.which("openclaw")
    if found:
        return found
    if sys.platform == "win32":
        found = shutil.which("openclaw.cmd")
        if found:
            return found
    raise RuntimeError("openclaw binary not found on PATH")


def _keyword_fallback(message: str) -> str:
    """Keyword-based routing used when OpenClaw is unavailable.

    Args:
        message: The user's message.

    Returns:
        Best-guess agent type from keywords.
    """
    text = message.lower()
    if any(k in text for k in ("test", "exam", "mock exam", "practice test")):
        return "test-creator"
    if any(k in text for k in ("question", "quiz", "practice problem", "generate")):
        return "question-creator"
    if any(k in text for k in ("homework", "assignment", "hw", "submit", "problem set")):
        return "homework-finisher"
    if any(k in text for k in ("summarize", "summary", "notes", "tldr", "study sheet", "flashcard")):
        return "note-summarizer"
    return "tutor"


def is_openclaw_available() -> bool:
    """Check if the OpenClaw gateway is reachable.

    Returns:
        True if gateway responds to health check.
    """
    import urllib.request
    gateway_http = os.getenv("OPENCLAW_GATEWAY_HTTP", "http://localhost:18789")
    token = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
    try:
        req = urllib.request.Request(
            f"{gateway_http}/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False
