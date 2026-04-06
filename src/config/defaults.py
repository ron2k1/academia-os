"""Fallback default values for configuration."""
from __future__ import annotations

DEFAULT_ORCHESTRATOR_MODEL = "google/gemini-2.5-pro"
DEFAULT_ORCHESTRATOR_PROVIDER = "openrouter"

DEFAULT_AGENT_MODEL = "claude-sonnet-4-20250514"

DEFAULT_TIMEOUT_SECONDS = 120

VAULT_SUBDIRS = [
    "sessions",
    "summaries",
    "questions",
    "tests",
    "homework",
]

VAULT_TEMPLATE_FILES = [
    "_index.md",
    "topics.md",
    "context.md",
]

CLASS_SUBDIRS = [
    "textbooks",
    "practice",
    "submissions",
    "rubrics",
    "outputs",
]
