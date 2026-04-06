"""Per-tab session state for WebSocket connections."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single chat message in a session.

    Attributes:
        role: 'user' or 'assistant'.
        content: The message text.
        agent: The agent that handled/will handle this message.
        timestamp: When the message was created.
    """

    role: str
    content: str
    agent: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class TabSession:
    """Session state for a single class tab.

    Attributes:
        class_id: The class this session belongs to.
        active_agent: Currently selected agent type.
        history: Chat message history.
        is_streaming: Whether the agent is currently streaming.
    """

    class_id: str
    active_agent: str = "tutor"
    history: list[ChatMessage] = field(default_factory=list)
    is_streaming: bool = False

    def add_user_message(self, content: str, agent: str) -> None:
        """Add a user message to the session history.

        Args:
            content: The message text.
            agent: The agent type selected.
        """
        self.active_agent = agent
        self.history.append(
            ChatMessage(role="user", content=content, agent=agent)
        )

    def add_assistant_message(self, content: str, agent: str) -> None:
        """Add an assistant response to the session history.

        Args:
            content: The full response text.
            agent: The agent that generated the response.
        """
        self.history.append(
            ChatMessage(role="assistant", content=content, agent=agent)
        )

    def get_recent_history(self, limit: int = 20) -> list[dict]:
        """Get recent chat history as dicts for context.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            List of message dicts with role and content.
        """
        recent = self.history[-limit:]
        return [
            {"role": m.role, "content": m.content}
            for m in recent
        ]


class SessionManager:
    """Manages per-tab sessions across all WebSocket connections.

    Each connection can have multiple tab sessions (one per class).
    """

    def __init__(self) -> None:
        """Initialize the session manager."""
        self._sessions: dict[str, dict[str, TabSession]] = {}

    def get_session(
        self, connection_id: str, class_id: str
    ) -> TabSession:
        """Get or create a tab session.

        Args:
            connection_id: Unique identifier for the WS connection.
            class_id: The class identifier.

        Returns:
            The TabSession for this connection and class.
        """
        if connection_id not in self._sessions:
            self._sessions[connection_id] = {}
        if class_id not in self._sessions[connection_id]:
            self._sessions[connection_id][class_id] = TabSession(
                class_id=class_id
            )
        return self._sessions[connection_id][class_id]

    def remove_connection(self, connection_id: str) -> None:
        """Remove all sessions for a disconnected connection.

        Args:
            connection_id: The connection to clean up.
        """
        self._sessions.pop(connection_id, None)
        logger.info("Cleaned up sessions for connection %s", connection_id)

    def get_all_sessions(
        self, connection_id: str
    ) -> dict[str, TabSession]:
        """Get all tab sessions for a connection.

        Args:
            connection_id: The connection identifier.

        Returns:
            Dict mapping class_id to TabSession.
        """
        return self._sessions.get(connection_id, {})
