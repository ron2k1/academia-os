"""Tests for observability event emitter and SQLite store."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.observability.events import (
    Event,
    EventType,
    emit,
    get_recent,
    set_store,
)
from src.observability.store import EventStore


class TestEventType:
    """Tests for the EventType enum."""

    def test_all_types_exist(self) -> None:
        """All expected event types are defined."""
        expected = [
            "message.received",
            "orchestrator.route",
            "context.assemble",
            "agent.spawn",
            "agent.stream",
            "agent.complete",
            "agent.error",
            "vault.write",
            "tool.execute",
            "tool.error",
            "openrouter.request",
            "openrouter.error",
            "guardclaw.filter",
            "response.sent",
        ]
        values = [e.value for e in EventType]
        for exp in expected:
            assert exp in values

    def test_from_value(self) -> None:
        """EventType can be constructed from string value."""
        assert EventType("agent.spawn") == EventType.AGENT_SPAWN


class TestEvent:
    """Tests for the Event model."""

    def test_defaults(self) -> None:
        """Event is constructed with sensible defaults."""
        event = Event(
            event_type=EventType.MESSAGE_RECEIVED,
            data={"msg": "hi"},
        )
        assert event.project == "academia-os"
        assert event.class_id == ""
        assert event.agent == ""
        assert event.id  # UUID generated
        assert event.timestamp  # timestamp generated

    def test_custom_fields(self) -> None:
        """Event accepts custom class_id and agent."""
        event = Event(
            event_type=EventType.AGENT_SPAWN,
            data={"model": "sonnet"},
            class_id="regression-methods",
            agent="tutor",
        )
        assert event.class_id == "regression-methods"
        assert event.agent == "tutor"


class TestEventStore:
    """Tests for the SQLite EventStore."""

    def test_insert_and_retrieve(
        self, event_store: EventStore
    ) -> None:
        """Inserted events can be retrieved."""
        event = Event(
            event_type=EventType.MESSAGE_RECEIVED,
            data={"msg": "test"},
        )
        event_store.insert(event)
        recent = event_store.get_recent(10)
        assert len(recent) == 1
        assert recent[0].id == event.id

    def test_count(self, event_store: EventStore) -> None:
        """Count returns correct number of events."""
        for i in range(5):
            event_store.insert(
                Event(
                    event_type=EventType.TOOL_EXECUTE,
                    data={"i": i},
                )
            )
        assert event_store.count() == 5

    def test_ordering(self, event_store: EventStore) -> None:
        """Events are returned most recent first."""
        e1 = Event(
            event_type=EventType.AGENT_SPAWN,
            data={"order": 1},
            timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        e2 = Event(
            event_type=EventType.AGENT_COMPLETE,
            data={"order": 2},
            timestamp=datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        )
        event_store.insert(e1)
        event_store.insert(e2)
        recent = event_store.get_recent(10)
        assert recent[0].data["order"] == 2

    def test_auto_prune(self) -> None:
        """Store prunes old events when limit exceeded."""
        store = EventStore(db_path=":memory:", max_events=10)
        for i in range(25):
            store.insert(
                Event(
                    event_type=EventType.TOOL_EXECUTE,
                    data={"i": i},
                )
            )
        assert store.count() <= 10
        store.close()


class TestEmitAndGetRecent:
    """Tests for module-level emit() and get_recent()."""

    def test_emit_and_retrieve(
        self, event_store: EventStore
    ) -> None:
        """emit() persists and get_recent() retrieves events."""
        set_store(event_store)
        event = emit(
            EventType.MESSAGE_RECEIVED,
            {"msg": "test"},
            class_id="test-class",
        )
        assert isinstance(event, Event)
        recent = get_recent(5)
        assert len(recent) >= 1
        assert recent[0].class_id == "test-class"

    def test_emit_multiple(self, event_store: EventStore) -> None:
        """Multiple emits accumulate in the store."""
        set_store(event_store)
        emit(EventType.AGENT_SPAWN, {"a": 1})
        emit(EventType.AGENT_COMPLETE, {"a": 2})
        emit(EventType.RESPONSE_SENT, {"a": 3})
        recent = get_recent(10)
        assert len(recent) == 3
