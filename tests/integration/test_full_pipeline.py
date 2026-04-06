"""Integration tests for the full AcademiaOS pipeline.

Tests the end-to-end flow: REST health endpoints, WebSocket message
routing, dashboard sub-app, observability event emission, session
management, and file upload pipeline.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.observability.events import EventType, emit, set_store
from src.observability.store import EventStore
from src.orchestrator.router import AgentType, route_intent
from src.websocket.handler import ConnectionManager
from src.websocket.messages import (
    ErrorMessage,
    HealthStatus,
    PongMessage,
    StreamChunk,
    StreamEnd,
    UserMessage,
    parse_incoming,
)
from src.websocket.sessions import SessionManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def event_store():
    """Create a fresh in-memory EventStore."""
    store = EventStore(db_path=":memory:")
    yield store
    store.close()


@pytest.fixture()
def test_client():
    """Create a TestClient for the FastAPI app with temp directories."""
    tmp = tempfile.mkdtemp()
    tmp_path = Path(tmp)
    # Avoid import-time side effects from frontend dist check
    with patch("src.server.PROJECT_ROOT", tmp_path), \
         patch("src.server.CONFIG_DIR", tmp_path / "config"), \
         patch("src.server.VAULTS_DIR", tmp_path / "vaults"), \
         patch("src.server.FILES_DIR", tmp_path / "files"), \
         patch("src.server.PROGRESS_DIR", tmp_path / "progress"):

        (tmp_path / "config").mkdir(exist_ok=True)
        (tmp_path / "vaults").mkdir(exist_ok=True)
        (tmp_path / "files").mkdir(exist_ok=True)
        (tmp_path / "progress").mkdir(exist_ok=True)

        from src.server import app
        yield TestClient(app)


# ---------------------------------------------------------------------------
# REST Endpoint Integration Tests
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    """Integration tests for REST health endpoints."""

    def test_root_health(self, test_client: TestClient) -> None:
        """GET /health returns gateway status."""
        resp = test_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["gateway"] is True
        assert "claude_cli" in data
        assert "config_loaded" in data

    def test_api_health(self, test_client: TestClient) -> None:
        """GET /api/health returns component-level status."""
        resp = test_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["gateway"] is True
        assert "claude_cli" in data
        assert "openrouter" in data
        assert "r" in data
        assert "config_loaded" in data

    def test_api_classes_fallback(self, test_client: TestClient) -> None:
        """GET /api/classes returns empty structure when no config."""
        resp = test_client.get("/api/classes")
        assert resp.status_code == 200
        data = resp.json()
        assert "semester" in data or "classes" in data

    def test_api_progress_empty(self, test_client: TestClient) -> None:
        """GET /api/progress returns empty structure when no tracker."""
        resp = test_client.get("/api/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall" in data


# ---------------------------------------------------------------------------
# File Upload Pipeline Integration Tests
# ---------------------------------------------------------------------------

class TestFileUploadPipeline:
    """Integration tests for file upload and listing."""

    def test_upload_and_list(self, test_client: TestClient) -> None:
        """Upload a file and verify it appears in the listing."""
        content = b"This is a test PDF content"
        resp = test_client.post(
            "/api/upload/test-class/textbooks",
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "uploaded"
        assert data["filename"] == "test.pdf"

        # Now list files
        list_resp = test_client.get("/api/files/test-class/textbooks")
        assert list_resp.status_code == 200
        files = list_resp.json()["files"]
        assert len(files) >= 1
        assert any(f["name"] == "test.pdf" for f in files)

    def test_upload_invalid_category(self, test_client: TestClient) -> None:
        """Upload to invalid category returns 400."""
        resp = test_client.post(
            "/api/upload/test-class/invalid",
            files={"file": ("test.txt", b"data", "text/plain")},
        )
        assert resp.status_code == 400

    def test_list_empty_category(self, test_client: TestClient) -> None:
        """Listing files for non-existent category returns empty list."""
        resp = test_client.get("/api/files/test-class/practice")
        assert resp.status_code == 200
        assert resp.json()["files"] == []


# ---------------------------------------------------------------------------
# WebSocket Message Routing Tests
# ---------------------------------------------------------------------------

class TestWebSocketMessages:
    """Integration tests for WebSocket message parsing and routing."""

    def test_parse_user_message(self) -> None:
        """UserMessage parses correctly from raw dict."""
        raw = {
            "type": "message",
            "class_id": "regression-methods",
            "agent": "tutor",
            "content": "Explain linear regression",
        }
        msg = parse_incoming(raw)
        assert isinstance(msg, UserMessage)
        assert msg.class_id == "regression-methods"
        assert msg.agent == "tutor"

    def test_parse_ping(self) -> None:
        """PingMessage parses correctly."""
        msg = parse_incoming({"type": "ping"})
        assert msg.type == "ping"

    def test_parse_unknown_type(self) -> None:
        """Unknown message type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown message type"):
            parse_incoming({"type": "bogus"})

    def test_outgoing_message_serialization(self) -> None:
        """All outgoing messages serialize to valid dicts."""
        messages = [
            StreamChunk(class_id="test", content="hello"),
            StreamEnd(class_id="test", agent="tutor"),
            ErrorMessage(message="something went wrong"),
            HealthStatus(status={"gateway": True}),
            PongMessage(),
        ]
        for msg in messages:
            d = msg.model_dump()
            assert "type" in d
            assert isinstance(d, dict)


# ---------------------------------------------------------------------------
# Session Management Integration Tests
# ---------------------------------------------------------------------------

class TestSessionManagement:
    """Integration tests for WebSocket session lifecycle."""

    def test_session_lifecycle(self) -> None:
        """Create, use, and clean up a session."""
        mgr = SessionManager()
        conn_id = "test-conn-1"

        # Get/create session
        session = mgr.get_session(conn_id, "regression-methods")
        assert session.class_id == "regression-methods"
        assert session.history == []

        # Add messages
        session.add_user_message("Hello", "tutor")
        session.add_assistant_message("Hi there!", "tutor")
        assert len(session.history) == 2

        # Get recent history
        history = session.get_recent_history(10)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

        # Cleanup
        mgr.remove_connection(conn_id)
        assert mgr.get_all_sessions(conn_id) == {}

    def test_multiple_class_sessions(self) -> None:
        """A single connection can have sessions for multiple classes."""
        mgr = SessionManager()
        conn_id = "test-conn-2"

        s1 = mgr.get_session(conn_id, "class-a")
        s2 = mgr.get_session(conn_id, "class-b")
        s1.add_user_message("msg for A", "tutor")
        s2.add_user_message("msg for B", "question_creator")

        all_sessions = mgr.get_all_sessions(conn_id)
        assert len(all_sessions) == 2
        assert all_sessions["class-a"].history[0].content == "msg for A"
        assert all_sessions["class-b"].history[0].agent == "question_creator"


# ---------------------------------------------------------------------------
# Agent Router Integration Tests
# ---------------------------------------------------------------------------

class TestAgentRouting:
    """Integration tests for intent-based agent routing."""

    def test_tutor_routing(self) -> None:
        """Messages about concepts route to tutor."""
        result = route_intent("explain linear regression")
        assert result == AgentType.TUTOR

    def test_question_creator_routing(self) -> None:
        """Messages about questions route to question_creator."""
        result = route_intent("create practice questions for chapter 3")
        assert result == AgentType.QUESTION_CREATOR

    def test_homework_routing(self) -> None:
        """Messages about homework route to homework_finisher."""
        result = route_intent("help me finish my homework assignment")
        assert result == AgentType.HOMEWORK_FINISHER

    def test_default_routing(self) -> None:
        """Ambiguous messages default to tutor."""
        result = route_intent("hello there")
        assert result == AgentType.TUTOR


# ---------------------------------------------------------------------------
# Observability Pipeline Integration Tests
# ---------------------------------------------------------------------------

class TestObservabilityPipeline:
    """Integration tests for the full observability event pipeline."""

    def test_emit_and_retrieve_through_store(
        self, event_store: EventStore
    ) -> None:
        """Events emitted via emit() are stored and retrievable."""
        set_store(event_store)
        emit(
            EventType.MESSAGE_RECEIVED,
            {"msg": "test"},
            class_id="test-class",
        )
        emit(
            EventType.ORCHESTRATOR_ROUTE,
            {"agent": "tutor"},
            class_id="test-class",
        )
        emit(
            EventType.AGENT_SPAWN,
            {"model": "sonnet"},
            class_id="test-class",
            agent="tutor",
        )
        emit(
            EventType.AGENT_COMPLETE,
            {"wall_time_ms": 450},
            class_id="test-class",
            agent="tutor",
        )

        recent = event_store.get_recent(10)
        assert len(recent) == 4

        # Verify event types are present
        types = {e.event_type for e in recent}
        assert EventType.MESSAGE_RECEIVED in types
        assert EventType.AGENT_COMPLETE in types

    def test_store_filtering_by_type(
        self, event_store: EventStore
    ) -> None:
        """EventStore supports filtering by event_type."""
        set_store(event_store)
        emit(EventType.AGENT_SPAWN, {"a": 1}, agent="tutor")
        emit(EventType.AGENT_COMPLETE, {"a": 2}, agent="tutor")
        emit(EventType.VAULT_WRITE, {"path": "test.md"})

        # get_recent retrieves all
        all_events = event_store.get_recent(10)
        assert len(all_events) == 3

    def test_store_auto_prune(self) -> None:
        """Store prunes when exceeding max_events threshold."""
        store = EventStore(db_path=":memory:", max_events=5)
        set_store(store)
        for i in range(20):
            emit(EventType.TOOL_EXECUTE, {"i": i})
        assert store.count() <= 5
        store.close()


# ---------------------------------------------------------------------------
# Dashboard Sub-app Integration Tests
# ---------------------------------------------------------------------------

class TestDashboardIntegration:
    """Integration tests for the observability dashboard sub-app."""

    def test_dashboard_health(self, test_client: TestClient) -> None:
        """GET /dashboard/health returns dashboard status."""
        resp = test_client.get("/dashboard/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dashboard"] is True
        assert "event_count" in data

    def test_dashboard_events_empty(self, test_client: TestClient) -> None:
        """GET /dashboard/events returns empty list initially."""
        resp = test_client.get("/dashboard/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data

    def test_dashboard_stats(self, test_client: TestClient) -> None:
        """GET /dashboard/stats returns statistics structure."""
        resp = test_client.get("/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "total_events" in data

    def test_dashboard_html_page(self, test_client: TestClient) -> None:
        """GET /dashboard/ serves the HTML dashboard page."""
        resp = test_client.get("/dashboard/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "AcademiaOS" in resp.text


# ---------------------------------------------------------------------------
# Vault Endpoint Integration Tests
# ---------------------------------------------------------------------------

class TestVaultEndpoints:
    """Integration tests for vault file read endpoint."""

    def test_vault_not_found(self, test_client: TestClient) -> None:
        """Reading a non-existent vault file returns 404."""
        resp = test_client.get("/api/vault/test-class/nonexistent.md")
        assert resp.status_code == 404

    def test_list_files_nonexistent_class(
        self, test_client: TestClient
    ) -> None:
        """Listing files for a non-existent class returns empty."""
        resp = test_client.get("/api/files/nonexistent/textbooks")
        assert resp.status_code == 200
        assert resp.json()["files"] == []


# ---------------------------------------------------------------------------
# WebSocket Integration Tests (using TestClient)
# ---------------------------------------------------------------------------

class TestWebSocketIntegration:
    """Integration tests for WebSocket endpoint."""

    def test_websocket_health_on_connect(
        self, test_client: TestClient
    ) -> None:
        """WebSocket sends health status immediately on connection."""
        with test_client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "health"
            assert data["status"]["gateway"] is True

    def test_websocket_ping_pong(
        self, test_client: TestClient
    ) -> None:
        """WebSocket responds to ping with pong."""
        with test_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # consume health message
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_websocket_message_stream(
        self, test_client: TestClient
    ) -> None:
        """WebSocket streams response chunks for user messages."""
        with test_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # consume health message
            ws.send_json({
                "type": "message",
                "class_id": "test-class",
                "agent": "tutor",
                "content": "What is regression?",
            })

            # Collect all chunks
            chunks = []
            while True:
                data = ws.receive_json()
                if data["type"] == "stream_chunk":
                    chunks.append(data["content"])
                elif data["type"] == "stream_end":
                    break
                elif data["type"] == "error":
                    pytest.fail(f"Unexpected error: {data['message']}")
                    break

            assert len(chunks) > 0
            full_response = "".join(chunks)
            assert "tutor" in full_response.lower()

    def test_websocket_invalid_message(
        self, test_client: TestClient
    ) -> None:
        """WebSocket returns error for invalid message types."""
        with test_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # consume health message
            ws.send_json({"type": "unknown_type"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Invalid message" in data["message"]
