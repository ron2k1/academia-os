"""Live-server smoke tests for health, classes, dashboard, and GuardClaw.

These tests exercise the FastAPI application through ``TestClient`` with
``@pytest.mark.integration`` so they can be selected or excluded via
``pytest -m integration``.

Covers:
- Health endpoint contracts (/health, /api/health)
- Classes endpoint fallback when no config present
- Dashboard sub-app endpoints (health, events, stats, HTML page)
- GuardClaw middleware rate limiting (429 after quota)
- WebSocket health handshake and ping/pong
"""
from __future__ import annotations

import tempfile
import time
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def live_client():
    """Create a TestClient for the full FastAPI app with temp directories.

    Patches all directory constants so that the app boots cleanly without
    requiring real project config or frontend assets.
    """
    tmp = tempfile.mkdtemp()
    tmp_path = Path(tmp)

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
# Health Endpoint Smoke Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestHealthSmoke:
    """Smoke tests for health endpoints under live-server conditions."""

    def test_root_health_returns_200(self, live_client: TestClient) -> None:
        """GET /health returns 200 with required fields."""
        resp = live_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["gateway"] is True
        assert "claude_cli" in data
        assert "config_loaded" in data

    def test_api_health_returns_200(self, live_client: TestClient) -> None:
        """GET /api/health returns 200 with component statuses."""
        resp = live_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["gateway"] is True
        assert "claude_cli" in data
        assert "openrouter" in data
        assert "r" in data
        assert "config_loaded" in data

    def test_health_endpoints_consistent(
        self, live_client: TestClient
    ) -> None:
        """Both health endpoints agree on gateway status."""
        root = live_client.get("/health").json()
        api = live_client.get("/api/health").json()
        assert root["gateway"] == api["gateway"]
        assert root["claude_cli"] == api["claude_cli"]


# ---------------------------------------------------------------------------
# Classes Endpoint Smoke Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestClassesSmoke:
    """Smoke tests for the classes configuration endpoint."""

    def test_classes_returns_200(self, live_client: TestClient) -> None:
        """GET /api/classes returns 200 even without config."""
        resp = live_client.get("/api/classes")
        assert resp.status_code == 200
        data = resp.json()
        # Should return some structure (semester or classes key)
        assert isinstance(data, dict)

    def test_classes_has_expected_shape(
        self, live_client: TestClient
    ) -> None:
        """Response contains semester or classes key."""
        data = live_client.get("/api/classes").json()
        assert "semester" in data or "classes" in data

    def test_progress_returns_200(self, live_client: TestClient) -> None:
        """GET /api/progress returns 200 with overall field."""
        resp = live_client.get("/api/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall" in data


# ---------------------------------------------------------------------------
# Dashboard Sub-app Smoke Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDashboardSmoke:
    """Smoke tests for the observability dashboard sub-app."""

    def test_dashboard_health(self, live_client: TestClient) -> None:
        """GET /dashboard/health returns dashboard status."""
        resp = live_client.get("/dashboard/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dashboard"] is True
        assert "event_count" in data

    def test_dashboard_events_endpoint(
        self, live_client: TestClient
    ) -> None:
        """GET /dashboard/events returns events list."""
        resp = live_client.get("/dashboard/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_dashboard_stats_endpoint(
        self, live_client: TestClient
    ) -> None:
        """GET /dashboard/stats returns statistics."""
        resp = live_client.get("/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "total_events" in data

    def test_dashboard_html_page(self, live_client: TestClient) -> None:
        """GET /dashboard/ serves the HTML dashboard page."""
        resp = live_client.get("/dashboard/")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type
        assert "AcademiaOS" in resp.text


# ---------------------------------------------------------------------------
# GuardClaw Middleware Rate Limiting Smoke Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRateLimitingSmoke:
    """Smoke tests for GuardClawMiddleware rate limiting."""

    def test_normal_requests_allowed(
        self, live_client: TestClient
    ) -> None:
        """A handful of requests should pass without rate limiting."""
        for _ in range(5):
            resp = live_client.get("/health")
            assert resp.status_code == 200

    def test_rate_limit_returns_429(self, live_client: TestClient) -> None:
        """Exceeding MAX_REQUESTS within the window triggers 429.

        We patch the middleware limit to a small value so the test
        runs quickly.
        """
        from src.server import GuardClawMiddleware

        original_max = GuardClawMiddleware.MAX_REQUESTS
        try:
            GuardClawMiddleware.MAX_REQUESTS = 3

            # Clear existing request tracking
            for mw in live_client.app.user_middleware:
                pass  # middleware is already instantiated

            # Reset the internal state by patching
            # We need to access the middleware instance through the app
            # Instead, just make enough requests to exceed the limit
            # The TestClient shares IP so all requests count together
            responses = []
            for _ in range(10):
                responses.append(live_client.get("/health"))

            status_codes = [r.status_code for r in responses]
            # At least one should be 429 (after the 3rd request)
            assert 429 in status_codes, (
                f"Expected at least one 429 response, got: {status_codes}"
            )

            # Verify 429 response body structure
            rate_limited = [r for r in responses if r.status_code == 429]
            data = rate_limited[0].json()
            assert "error" in data
            assert "limit" in data
        finally:
            GuardClawMiddleware.MAX_REQUESTS = original_max


# ---------------------------------------------------------------------------
# WebSocket Handshake Smoke Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestWebSocketSmoke:
    """Smoke tests for WebSocket endpoint."""

    def test_websocket_connect_receives_health(
        self, live_client: TestClient
    ) -> None:
        """WebSocket connection immediately receives health status."""
        with live_client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "health"
            assert data["status"]["gateway"] is True

    def test_websocket_ping_pong(self, live_client: TestClient) -> None:
        """WebSocket responds to ping with pong."""
        with live_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # consume health message
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_websocket_invalid_message_returns_error(
        self, live_client: TestClient
    ) -> None:
        """WebSocket returns error for invalid message types."""
        with live_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # consume health message
            ws.send_json({"type": "nonexistent"})
            data = ws.receive_json()
            assert data["type"] == "error"


# ---------------------------------------------------------------------------
# File Upload Smoke Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFileUploadSmoke:
    """Smoke tests for file upload endpoint."""

    def test_upload_valid_file(self, live_client: TestClient) -> None:
        """Uploading a file to a valid category succeeds."""
        resp = live_client.post(
            "/api/upload/test-class/textbooks",
            files={"file": ("notes.pdf", b"PDF content here", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "uploaded"
        assert data["filename"] == "notes.pdf"

    def test_upload_invalid_category_rejected(
        self, live_client: TestClient
    ) -> None:
        """Uploading to an invalid category returns 400."""
        resp = live_client.post(
            "/api/upload/test-class/invalid-category",
            files={"file": ("test.txt", b"data", "text/plain")},
        )
        assert resp.status_code == 400

    def test_list_files_after_upload(self, live_client: TestClient) -> None:
        """Uploaded file appears in subsequent file listing."""
        live_client.post(
            "/api/upload/smoke-class/textbooks",
            files={"file": ("lecture.pdf", b"content", "application/pdf")},
        )
        resp = live_client.get("/api/files/smoke-class/textbooks")
        assert resp.status_code == 200
        files = resp.json()["files"]
        assert any(f["name"] == "lecture.pdf" for f in files)
