"""AcademiaOS Gateway -- FastAPI server with REST + WebSocket endpoints."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from src.agents.homework_finisher import HomeworkFinisherAgent
from src.agents.note_summarizer import NoteSummarizerAgent
from src.agents.question_creator import QuestionCreatorAgent
from src.agents.spawner import ClaudeSpawner
from src.agents.test_creator import TestCreatorAgent
from src.agents.tutor import TutorAgent
from src.config.defaults import DEFAULT_AGENT_MODEL
from src.config.loader import load_config
from src.config.schemas import ClassesConfig, ModelsConfig
from src.guardrails import GuardClaw, validate_agent_type, validate_class_id, validate_message
from src.guardrails.guardclaw import FilterVerdict
from src.observability.dashboard import dashboard_app, set_dashboard_store
from src.observability.events import EventType, emit
from src.observability.store import EventStore
from src.orchestrator.router import AgentType, route_intent
from src.tools.vault import VaultTool
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


# ---------------------------------------------------------------------------
# GuardClaw rate-limiting middleware
# ---------------------------------------------------------------------------

class GuardClawMiddleware(BaseHTTPMiddleware):
    """Request-level rate limiter for REST endpoints.

    Tracks request counts per client IP and returns HTTP 429 when
    the session limit is exceeded.  WebSocket upgrades are excluded
    since they have their own connection management.

    Attributes:
        MAX_REQUESTS: Maximum requests allowed per session window.
        WINDOW_SECONDS: Sliding window length in seconds.
    """

    MAX_REQUESTS: int = 200
    WINDOW_SECONDS: int = 3600  # 1-hour window

    def __init__(self, app: FastAPI) -> None:  # noqa: D107
        super().__init__(app)
        # Map of client_key -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next
    ) -> StarletteResponse:
        """Check rate limit before forwarding the request.

        Args:
            request: The incoming HTTP request.
            call_next: ASGI chain continuation callable.

        Returns:
            The downstream response, or a 429 JSON error.
        """
        # Skip rate limiting for WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        client_key = self._client_key(request)
        now = time.time()
        cutoff = now - self.WINDOW_SECONDS

        # Prune expired timestamps
        timestamps = self._requests[client_key]
        self._requests[client_key] = [
            ts for ts in timestamps if ts > cutoff
        ]

        if len(self._requests[client_key]) >= self.MAX_REQUESTS:
            logger.warning(
                "GuardClawMiddleware rate limit hit for %s (%d reqs)",
                client_key,
                len(self._requests[client_key]),
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded. Please try again later.",
                    "limit": self.MAX_REQUESTS,
                    "window_seconds": self.WINDOW_SECONDS,
                },
            )

        self._requests[client_key].append(now)
        return await call_next(request)

    @staticmethod
    def _client_key(request: Request) -> str:
        """Derive a rate-limit key from the request.

        Uses X-Forwarded-For when behind a proxy, otherwise falls
        back to the direct client IP.

        Args:
            request: The incoming request.

        Returns:
            String key identifying the client session.
        """
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


app.add_middleware(GuardClawMiddleware)

# Singletons
manager = ConnectionManager()
sessions = SessionManager()
guard = GuardClaw()

# Agent class registry keyed by AgentType enum value
_AGENT_CLASSES: dict[str, type] = {
    "tutor": TutorAgent,
    "question_creator": QuestionCreatorAgent,
    "note_summarizer": NoteSummarizerAgent,
    "test_creator": TestCreatorAgent,
    "homework_finisher": HomeworkFinisherAgent,
}

# Response text keys differ per agent
_RESPONSE_KEYS: dict[str, str] = {
    "tutor": "response",
    "question_creator": "raw_json",
    "note_summarizer": "summary",
    "test_creator": "test_markdown",
    "homework_finisher": "final_output",
}

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

    Pipeline: GuardClaw filter -> validate -> route -> config -> vault
    -> agent.run() -> filter output -> stream -> session log.

    Args:
        connection_id: The sender's connection ID.
        msg: The validated UserMessage.
    """
    session = sessions.get_session(connection_id, msg.class_id)
    session.add_user_message(msg.content, msg.agent)
    session.is_streaming = True

    try:
        # -- 1. Emit message received event --------------------------------
        emit(
            EventType.MESSAGE_RECEIVED,
            {"content_length": len(msg.content), "agent_hint": msg.agent},
            class_id=msg.class_id,
            agent=msg.agent,
        )

        # -- 2. GuardClaw input filter -------------------------------------
        verdict = guard.filter_input(msg.content)
        if verdict == FilterVerdict.BLOCK:
            logger.warning(
                "GuardClaw BLOCKED message from %s for class %s",
                connection_id,
                msg.class_id,
            )
            await manager.send_message(
                connection_id,
                ErrorMessage(
                    class_id=msg.class_id,
                    message=(
                        "Your message was blocked by our safety filter. "
                        "Please rephrase and try again."
                    ),
                ),
            )
            return
        if verdict == FilterVerdict.WARN:
            logger.warning(
                "GuardClaw WARN on message from %s for class %s",
                connection_id,
                msg.class_id,
            )

        # -- 3. Validate inputs -------------------------------------------
        msg_error = validate_message(msg.content)
        if msg_error:
            await manager.send_message(
                connection_id,
                ErrorMessage(class_id=msg.class_id, message=msg_error),
            )
            return

        cid_error = validate_class_id(msg.class_id)
        if cid_error:
            await manager.send_message(
                connection_id,
                ErrorMessage(class_id=msg.class_id, message=cid_error),
            )
            return

        agent_error = validate_agent_type(msg.agent)
        if agent_error:
            # Fall back to router-based detection instead of hard fail
            logger.info(
                "Agent type '%s' not in validators, will use router",
                msg.agent,
            )

        # -- 4. Route intent ----------------------------------------------
        routed_type: AgentType = route_intent(msg.content)
        agent_type = routed_type.value

        # If the client explicitly requested a valid agent, honour it
        if msg.agent and msg.agent in _AGENT_CLASSES:
            agent_type = msg.agent

        emit(
            EventType.ORCHESTRATOR_ROUTE,
            {"routed": routed_type.value, "effective": agent_type},
            class_id=msg.class_id,
            agent=agent_type,
        )

        # -- 5. Load class config -----------------------------------------
        classes_path = CONFIG_DIR / "classes.json"
        if not classes_path.exists():
            classes_path = CONFIG_DIR / "classes.example.json"

        classes_config: ClassesConfig = load_config(classes_path)
        class_config = None
        for cc in classes_config.classes:
            if cc.id == msg.class_id:
                class_config = cc
                break

        if class_config is None:
            await manager.send_message(
                connection_id,
                ErrorMessage(
                    class_id=msg.class_id,
                    message=f"Unknown class '{msg.class_id}'.",
                ),
            )
            return

        # -- 6. Load model config -----------------------------------------
        model = DEFAULT_AGENT_MODEL
        models_path = CONFIG_DIR / "models.json"
        if not models_path.exists():
            models_path = CONFIG_DIR / "models.example.json"
        if models_path.exists():
            try:
                models_config: ModelsConfig = load_config(models_path)
                # Agent keys in models config may use hyphens or underscores
                agent_model_key = agent_type.replace("_", "-")
                if agent_type in models_config.agents:
                    model = models_config.agents[agent_type].cli_model
                elif agent_model_key in models_config.agents:
                    model = models_config.agents[agent_model_key].cli_model
            except Exception as exc:
                logger.warning("Failed to load models config: %s", exc)

        # -- 7. Create vault + spawner + agent ----------------------------
        vault = VaultTool(class_id=msg.class_id, vaults_root=str(VAULTS_DIR))
        spawner = ClaudeSpawner()
        agent_cls = _AGENT_CLASSES[agent_type]
        agent = agent_cls(
            class_config=class_config,
            vault=vault,
            spawner=spawner,
            model=model,
        )

        # -- 8. Run agent (sync -> async via to_thread) -------------------
        result: dict = await asyncio.to_thread(agent.run, msg.content)

        # -- 9. Extract response text -------------------------------------
        response_key = _RESPONSE_KEYS.get(agent_type, "response")
        response_text = str(result.get(response_key, result.get("response", "")))

        # -- 10. Filter output through GuardClaw --------------------------
        response_text = guard.filter_output(response_text)

        # -- 11. Stream to client in chunks --------------------------------
        chunk_size = 80
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            await manager.send_message(
                connection_id,
                StreamChunk(class_id=msg.class_id, content=chunk),
            )

        await manager.send_message(
            connection_id,
            StreamEnd(class_id=msg.class_id, agent=agent_type),
        )

        # -- 12. Log to session -------------------------------------------
        session.add_assistant_message(response_text, agent_type)

        emit(
            EventType.RESPONSE_SENT,
            {"agent": agent_type, "length": len(response_text)},
            class_id=msg.class_id,
            agent=agent_type,
        )

    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        emit(
            EventType.AGENT_ERROR,
            {"error": str(exc)},
            class_id=msg.class_id,
            agent=msg.agent,
        )
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
