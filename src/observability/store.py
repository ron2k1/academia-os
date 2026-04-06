"""SQLite-backed event persistence with auto-pruning."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.observability.events import Event

MAX_EVENTS_DEFAULT = 10_000
PRUNE_BATCH_SIZE = 1_000


class EventStore:
    """SQLite store for observability events.

    Supports in-memory (``':memory:'``) or file-backed databases.
    Automatically prunes old events when the count exceeds a threshold.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        max_events: int = MAX_EVENTS_DEFAULT,
    ) -> None:
        """Initialize the event store and create tables.

        Args:
            db_path: Path to the SQLite database, or ':memory:'.
            max_events: Maximum events to keep before pruning.
        """
        self.db_path = db_path
        self.max_events = max_events
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the events table if it does not exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                project TEXT NOT NULL DEFAULT 'academia-os',
                class_id TEXT DEFAULT '',
                agent TEXT DEFAULT '',
                data TEXT DEFAULT '{}'
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON events(timestamp DESC)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type)
        """)
        self._conn.commit()

    def insert(self, event: Event) -> None:
        """Insert an event into the store.

        Triggers auto-pruning if the event count exceeds max_events.

        Args:
            event: The Event instance to persist.
        """
        self._conn.execute(
            """
            INSERT INTO events (id, timestamp, event_type, project,
                                class_id, agent, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.timestamp.isoformat(),
                event.event_type.value,
                event.project,
                event.class_id,
                event.agent,
                json.dumps(event.data),
            ),
        )
        self._conn.commit()
        self._auto_prune()

    def get_recent(self, limit: int = 50) -> list[Event]:
        """Retrieve the most recent events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of Event instances, most recent first.
        """
        from src.observability.events import Event, EventType

        cursor = self._conn.execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            Event(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                event_type=EventType(row["event_type"]),
                project=row["project"],
                class_id=row["class_id"],
                agent=row["agent"],
                data=json.loads(row["data"]),
            )
            for row in rows
        ]

    def count(self) -> int:
        """Return the total number of events in the store.

        Returns:
            Integer count of stored events.
        """
        cursor = self._conn.execute("SELECT COUNT(*) FROM events")
        return cursor.fetchone()[0]

    def _auto_prune(self) -> None:
        """Delete oldest events if count exceeds max_events."""
        current = self.count()
        if current <= self.max_events:
            return
        excess = current - self.max_events + PRUNE_BATCH_SIZE
        self._conn.execute(
            """
            DELETE FROM events WHERE id IN (
                SELECT id FROM events
                ORDER BY timestamp ASC
                LIMIT ?
            )
            """,
            (excess,),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
