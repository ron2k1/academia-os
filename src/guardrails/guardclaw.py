"""GuardClaw -- prompt-injection detection and output sanitisation."""
from __future__ import annotations

import logging
import re
from enum import Enum
from pathlib import Path

from src.observability.events import EventType, emit

logger = logging.getLogger(__name__)


class FilterVerdict(str, Enum):
    """Possible outcomes of an input filter check."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


# ---------------------------------------------------------------------------
# Injection patterns -- each regex targets a common prompt-injection vector
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(prior|previous|above)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"bypass\s+(safety|filter|content|guardrail)", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+(are|have)\s+no\s+(rules|restrictions|limits)", re.IGNORECASE),
    re.compile(r"override\s+(your|the)\s+(instructions|rules|programming)", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you\s+have\s+no\s+(guidelines|restrictions)", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all|your)\s+(you|instructions|rules)", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Output redaction patterns -- catch leaked secrets
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Generic API keys  (sk-..., key-..., api_..., etc.)
    (re.compile(r"\b(sk|key|api)[_-][A-Za-z0-9]{20,}\b"), "[REDACTED_API_KEY]"),
    # AWS-style keys
    (re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Bearer tokens in prose
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # Generic long hex secrets (32+ hex chars)
    (re.compile(r"\b[0-9a-fA-F]{32,}\b"), "[REDACTED_HEX_SECRET]"),
    # Environment variable leaks like SECRET_KEY=...
    (re.compile(r"(SECRET|TOKEN|PASSWORD|APIKEY|API_KEY)\s*=\s*\S+", re.IGNORECASE), r"\1=[REDACTED]"),
]


class GuardClaw:
    """Prompt-injection firewall for AcademiaOS.

    * ``filter_input``  -- scores an incoming message for injection patterns.
    * ``filter_output`` -- redacts secrets/keys from agent responses.
    * ``is_safe_path``  -- prevents path-traversal attacks on file operations.
    """

    # ------------------------------------------------------------------
    # Input filtering
    # ------------------------------------------------------------------

    def filter_input(self, message: str) -> FilterVerdict:
        """Score *message* for prompt-injection risk.

        Returns:
            * ``BLOCK`` if **one or more** injection patterns match.
            * ``ALLOW`` otherwise.
        """
        matches: list[str] = []
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(message):
                matches.append(pattern.pattern)

        hit_count = len(matches)

        if hit_count >= 1:
            verdict = FilterVerdict.BLOCK
        else:
            verdict = FilterVerdict.ALLOW

        # Emit observability event for every check
        emit(
            EventType.GUARDCLAW_FILTER,
            {
                "verdict": verdict.value,
                "hit_count": hit_count,
                "patterns": matches[:5],  # cap for payload size
                "message_length": len(message),
            },
        )

        if verdict != FilterVerdict.ALLOW:
            logger.warning(
                "GuardClaw %s -- %d pattern(s) matched: %s",
                verdict.value.upper(),
                hit_count,
                matches[:3],
            )

        return verdict

    # ------------------------------------------------------------------
    # Output filtering
    # ------------------------------------------------------------------

    def filter_output(self, text: str) -> str:
        """Redact API keys, tokens, and secrets from agent output.

        Args:
            text: Raw agent response text.

        Returns:
            Sanitised text with secrets replaced by placeholders.
        """
        result = text
        for pattern, replacement in _SECRET_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    # ------------------------------------------------------------------
    # Path safety
    # ------------------------------------------------------------------

    @staticmethod
    def is_safe_path(base: str | Path, user_path: str | Path) -> bool:
        """Return True if *user_path* resolves inside *base*.

        Prevents ``..`` traversal out of a vault or upload directory.

        Args:
            base: Trusted base directory.
            user_path: User-supplied (potentially hostile) path.

        Returns:
            True when the resolved path stays within *base*.
        """
        try:
            base_resolved = Path(base).resolve()
            target = (base_resolved / Path(user_path)).resolve()
            return str(target).startswith(str(base_resolved))
        except (OSError, ValueError):
            return False
