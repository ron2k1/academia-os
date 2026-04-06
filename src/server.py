"""AcademiaOS Gateway -- FastAPI server with REST + WebSocket endpoints."""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.observability.dashboard import dashboard_app, set_dashboard_store
from src.observability.store import EventStore
from src.websocket.handler import ConnectionManager
from src.websocket.messages import (
    ErrorMessage,
    HealthStatus,
    PongMessage,
    StreamChunk,
    StreamEnd,
    parse_incoming,
)
from src.websocket.sessions import SessionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="AcademiaOS Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
manager = ConnectionManager()
sessions = SessionManager()

# Project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
VAULTS_DIR = PROJECT_ROOT / "vaults"
FILES_DIR = PROJECT_ROOT / "files"
PROGRESS_DIR = PROJECT_ROOT / "progress"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_classes_config() -> dict[str, Any]:
    """Load classes configuration, falling back to example file.

    Returns:
        Parsed classes configuration dictionary.
    """
    classes_path = CONFIG_DIR / "classes.json"
    if not classes_path.exists():
        classes_path = CONFIG_DIR / "classes.example.json"
    if not classes_path.exists():
        return {"semester": {}, "classes": []}
    with open(classes_path, encoding="utf-8") as f:
        return json.load(f)


def _check_claude_cli() -> bool:
    """Check if the claude CLI binary is available on PATH.

    Returns:
        True if claude is found, False otherwise.
    """
    return shutil.which("claude") is not None


def _ensure_dir(path: Path) -> None:
    """Create directory if it does not exist.

    Args:
        path: Directory path to ensure.
    """
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, Any]:
    """Top-level health check endpoint.

    Returns:
        Health status dictionary.
    """
    config_ok = (
        (CONFIG_DIR / "classes.json").exists()
        or (CONFIG_DIR / "classes.example.json").exists()
    )
    return {
        "status": "ok",
        "gateway": True,
        "claude_cli": _check_claude_cli(),
        "config_loaded": config_ok,
    }


@app.get("/api/health")
async def api_health() -> dict[str, Any]:
    """API health check with component statuses.

    Returns:
        Component-level health status dictionary.
    """
    config_ok = (
        (CONFIG_DIR / "classes.json").exists()
        or (CONFIG_DIR / "classes.example.json").exists()
    )
    return {
        "gateway": True,
        "claude_cli": _check_claude_cli(),
        "openrouter": True,
        "r": shutil.which("Rscript") is not None,
        "config_loaded": config_ok,
    }


@app.get("/api/classes")
async def get_classes() -> dict[str, Any]:
    """Return loaded class configuration.

    Returns:
        Classes configuration dictionary.
    """
    return _load_classes_config()


@app.get("/api/progress")
async def get_progress() -> dict[str, Any]:
    """Return progress tracker data.

    Returns:
        Progress data dictionary, or empty structure if not found.
    """
    tracker_path = PROGRESS_DIR / "tracker.json"
    if not tracker_path.exists():
        return {"classes": {}, "topics": [], "overall": 0.0}
    with open(tracker_path, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/upload/{class_id}/{category}")
async def upload_file(
    class_id: str, category: str, file: UploadFile
) -> dict[str, str]:
    """Upload a file to a class bin.

    Args:
        class_id: Target class identifier.
        category: File category (textbooks, practice, submissions, rubrics).
        file: The uploaded file.

    Returns:
        Upload confirmation with file path.
    """
    valid_categories = {"textbooks", "practice", "submissions", "rubrics"}
    if category not in valid_categories:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Invalid category. Must be one of: {valid_categories}"
            },
        )

    upload_dir = FILES_DIR / class_id / category
    _ensure_dir(upload_dir)

    filename = file.filename or "unnamed"
    dest = upload_dir / filename
    content = await file.read()
    dest.write_bytes(content)

    logger.info("Uploaded %s to %s/%s", filename, class_id, category)
    return {
        "status": "uploaded",
        "path": f"{class_id}/{category}/{filename}",
        "filename": filename,
    }


@app.get("/api/files/{class_id}/{category}")
async def list_files(class_id: str, category: str) -> dict[str, Any]:
    """List files in a class category directory.

    Args:
        class_id: The class identifier.
        category: File category.

    Returns:
        Dictionary with list of file info dicts.
    """
    files_path = FILES_DIR / class_id / category
    if not files_path.exists():
        return {"files": []}

    file_list = []
    for item in sorted(files_path.iterdir()):
        if item.is_file():
            stat = item.stat()
            file_list.append({
                "name": item.name,
                "size": stat.st_size,
                "download_url": f"/api/files/{class_id}/{category}/{item.name}",
            })
    return {"files": file_list}


@app.get("/api/vault/{class_id}/{path:path}")
async def read_vault(class_id: str, path: str) -> dict[str, Any]:
    """Read a file from a class vault.

    Args:
        class_id: The class identifier.
        path: Relative file path within the vault.

    Returns:
        Dictionary with file content, or error response.
    """
    vault_path = VAULTS_DIR / class_id / path
    if not vault_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": f"Vault file not found: {path}"},
        )

    # Prevent path traversal
    try:
        vault_path.resolve().relative_to((VAULTS_DIR / class_id).resolve())
    except ValueError:
        return JSONResponse(
            status_code=403,
            content={"error": "Path traversal not allowed"},
        )

    content = vault_path.read_text(encoding="utf-8")
    return {"path": path, "content": content}


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time communication.

    Accepts connection, routes messages to agents, streams responses.

    Args:
        websocket: The incoming WebSocket connection.
    """
    connection_id = await manager.connect(websocket)

    # Send initial health status
    health_data = {
        "gateway": True,
        "claude_cli": _check_claude_cli(),
        "openrouter": True,
    }
    await manager.send_message(
        connection_id, HealthStatus(status=health_data)
    )

    try:
        while True:
            raw = await websocket.receive_json()
            await _handle_ws_message(connection_id, raw)
    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", connection_id)
    except Exception as exc:
        logger.error("WebSocket error for %s: %s", connection_id, exc)
    finally:
        manager.disconnect(connection_id)
        sessions.remove_connection(connection_id)


async def _handle_ws_message(
    connection_id: str, raw: dict[str, Any]
) -> None:
    """Handle a single incoming WebSocket message.

    Args:
        connection_id: The sender's connection ID.
        raw: Raw JSON data from the client.
    """
    try:
        msg = parse_incoming(raw)
    except (ValueError, Exception) as exc:
        await manager.send_message(
            connection_id,
            ErrorMessage(message=f"Invalid message: {exc}"),
        )
        return

    if msg.type == "ping":
        await manager.send_message(connection_id, PongMessage())
        return

    # User message -- route to agent
    if msg.type == "message":
        await _handle_user_message(connection_id, msg)


async def _handle_user_message(
    connection_id: str, msg: Any
) -> None:
    """Handle a user chat message by routing to the appropriate agent.

    For now, echoes the message back as a stream simulation.
    Full agent integration will use src.orchestrator.router.

    Args:
        connection_id: The sender's connection ID.
        msg: The validated UserMessage.
    """
    session = sessions.get_session(connection_id, msg.class_id)
    session.add_user_message(msg.content, msg.agent)
    session.is_streaming = True

    try:
        # Route to agent via orchestrator
        from src.orchestrator.router import AgentType

        agent_type = msg.agent
        if agent_type not in [e.value for e in AgentType]:
            agent_type = "tutor"

        # Simulate streamed response (real agent integration in Phase 4)
        response = (
            f"[{agent_type}] Received your message for "
            f"class '{msg.class_id}': {msg.content}\n\n"
            f"Agent integration is active. This is a placeholder "
            f"response demonstrating the streaming protocol."
        )

        # Stream in chunks to simulate real agent behavior
        chunk_size = 40
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            await manager.send_message(
                connection_id,
                StreamChunk(
                    class_id=msg.class_id,
                    content=chunk,
                ),
            )

        await manager.send_message(
            connection_id,
            StreamEnd(class_id=msg.class_id, agent=agent_type),
        )

        session.add_assistant_message(response, agent_type)

    except Exception as exc:
        logger.error("Agent error: %s", exc)
        await manager.send_message(
            connection_id,
            ErrorMessage(
                class_id=msg.class_id,
                message=f"Agent error: {exc}",
            ),
        )
    finally:
        session.is_streaming = False


# ---------------------------------------------------------------------------
# Observability Dashboard (must be mounted BEFORE static catch-all)
# ---------------------------------------------------------------------------

# Initialize the dashboard store and mount the sub-app
_dashboard_store = EventStore()
set_dashboard_store(_dashboard_store)
app.mount("/dashboard", dashboard_app)


# ---------------------------------------------------------------------------
# Static file serving (production)
# ---------------------------------------------------------------------------

_frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dist), html=True),
        name="frontend",
    )
