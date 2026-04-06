"""Observability event emitter with typed events."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from src.observability.store import EventStore

# Module-level default store (lazily initialized)
_default_store: EventStore | None = None


class EventType(str, Enum):
    """All observable event types in AcademiaOS."""

    MESSAGE_RECEIVED = "message.received"
    ORCHESTRATOR_ROUTE = "orchestrator.route"
    CONTEXT_ASSEMBLE = "context.assemble"
    AGENT_SPAWN = "agent.spawn"
    AGENT_STREAM = "agent.stream"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"
    VAULT_WRITE = "vault.write"
    TOOL_EXECUTE = "tool.execute"
    TOOL_ERROR = "tool.error"
    OPENROUTER_REQUEST = "openrouter.request"
    OPENROUTER_ERROR = "openrouter.error"
    GUARDCLAW_FILTER = "guardclaw.filter"
    RESPONSE_SENT = "response.sent"


class Event(BaseModel):
    """A single observability event."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    event_type: EventType
    project: str = "academia-os"
    class_id: str = ""
    agent: str = ""
    data: dict = Field(default_factory=dict)


def _get_store() -> EventStore:
    """Return the default module-level EventStore, creating if needed.

    Returns:
        The singleton EventStore instance.
    """
    global _default_store  # noqa: PLW0603
    if _default_store is None:
        _default_store = EventStore()
    return _default_store


def set_store(store: EventStore) -> None:
    """Replace the default event store (useful for testing).

    Args:
        store: The EventStore instance to use globally.
    """
    global _default_store  # noqa: PLW0603
    _default_store = store


def emit(
    event_type: EventType,
    data: dict,
    *,
    class_id: str = "",
    agent: str = "",
    project: str = "academia-os",
) -> Event:
    """Create, persist, and return an observability event.

    Args:
        event_type: The type of event being emitted.
        data: Arbitrary event payload.
        class_id: Optional class identifier.
        agent: Optional agent identifier.
        project: Project name (default: academia-os).

    Returns:
        The created Event instance.
    """
    event = Event(
        event_type=event_type,
        data=data,
        class_id=class_id,
        agent=agent,
        project=project,
    )
    _get_store().insert(event)
    return event


def get_recent(limit: int = 50) -> list[Event]:
    """Retrieve the most recent events.

    Args:
        limit: Maximum number of events to return.

    Returns:
        List of Event instances, most recent first.
    """
    return _get_store().get_recent(limit)
