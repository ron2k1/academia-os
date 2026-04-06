"""Pydantic schemas for all WebSocket message types."""
from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Outgoing messages (server -> client)
# ---------------------------------------------------------------------------

class StreamChunk(BaseModel):
    """A single chunk of streamed agent response."""

    type: Literal["stream_chunk"] = "stream_chunk"
    class_id: str
    content: str


class StreamEnd(BaseModel):
    """Signals the end of a streamed agent response."""

    type: Literal["stream_end"] = "stream_end"
    class_id: str
    agent: str


class ErrorMessage(BaseModel):
    """Error notification to the client."""

    type: Literal["error"] = "error"
    class_id: str = ""
    message: str


class FileReady(BaseModel):
    """Notification that a file is ready for download."""

    type: Literal["file_ready"] = "file_ready"
    class_id: str
    filename: str
    download_url: str


class HealthStatus(BaseModel):
    """System health status broadcast."""

    type: Literal["health"] = "health"
    status: dict[str, bool] = Field(default_factory=dict)


class PongMessage(BaseModel):
    """Pong response to client ping."""

    type: Literal["pong"] = "pong"


OutgoingMessage = Union[
    StreamChunk, StreamEnd, ErrorMessage,
    FileReady, HealthStatus, PongMessage,
]


# ---------------------------------------------------------------------------
# Incoming messages (client -> server)
# ---------------------------------------------------------------------------

class UserMessage(BaseModel):
    """A chat message from the user to an agent."""

    type: Literal["message"] = "message"
    class_id: str
    agent: str
    content: str


class PingMessage(BaseModel):
    """Client ping to keep connection alive."""

    type: Literal["ping"] = "ping"


IncomingMessage = Union[UserMessage, PingMessage]


def parse_incoming(data: dict[str, Any]) -> IncomingMessage:
    """Parse a raw JSON dict into a typed incoming message.

    Args:
        data: Raw JSON dictionary from the WebSocket.

    Returns:
        A validated IncomingMessage instance.

    Raises:
        ValueError: If the message type is unknown.
    """
    msg_type = data.get("type")
    if msg_type == "message":
        return UserMessage.model_validate(data)
    if msg_type == "ping":
        return PingMessage.model_validate(data)
    raise ValueError(f"Unknown message type: {msg_type}")
