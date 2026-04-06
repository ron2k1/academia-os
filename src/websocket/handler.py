"""WebSocket connection manager for tracking active connections."""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import WebSocket

from src.websocket.messages import OutgoingMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage active WebSocket connections.

    Tracks connections by unique ID and provides methods for
    broadcasting and targeted message delivery.
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection.

        Args:
            websocket: The incoming WebSocket connection.

        Returns:
            A unique connection ID for this client.
        """
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self._connections[connection_id] = websocket
        logger.info(
            "WebSocket connected: %s (total: %d)",
            connection_id,
            len(self._connections),
        )
        return connection_id

    def disconnect(self, connection_id: str) -> None:
        """Remove a disconnected WebSocket.

        Args:
            connection_id: The connection to remove.
        """
        self._connections.pop(connection_id, None)
        logger.info(
            "WebSocket disconnected: %s (total: %d)",
            connection_id,
            len(self._connections),
        )

    async def send_message(
        self, connection_id: str, message: OutgoingMessage
    ) -> None:
        """Send a typed message to a specific connection.

        Args:
            connection_id: Target connection ID.
            message: The outgoing message to send.
        """
        ws = self._connections.get(connection_id)
        if ws is None:
            logger.warning(
                "Cannot send to disconnected client: %s", connection_id
            )
            return
        await ws.send_json(message.model_dump())

    async def send_json(
        self, connection_id: str, data: dict
    ) -> None:
        """Send raw JSON to a specific connection.

        Args:
            connection_id: Target connection ID.
            data: Dictionary to send as JSON.
        """
        ws = self._connections.get(connection_id)
        if ws is None:
            return
        await ws.send_json(data)

    async def broadcast(self, message: OutgoingMessage) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: The outgoing message to broadcast.
        """
        data = message.model_dump()
        disconnected: list[str] = []
        for cid, ws in self._connections.items():
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(cid)
        for cid in disconnected:
            self.disconnect(cid)

    @property
    def active_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)
