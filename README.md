# AcademiaOS

Docker-packaged multi-agent academic workspace. A FastAPI backend + React frontend
where a lead orchestrator routes user intent to specialized sub-agents, each running
as a fresh Claude CLI subprocess with context injected from Obsidian-style vaults.

## Architecture

```
Browser  <-->  FastAPI + WebSocket  <-->  Orchestrator
                    |                         |
               Static React              Sub-Agents (Claude CLI)
               Observability              Vault Context
               Dashboard (SSE)            Config-driven
```

**Key components:**

- **Orchestrator** -- Classifies user intent and delegates to the right sub-agent
- **Sub-Agents** -- Specialized Claude CLI subprocesses (writer, researcher, coder, etc.)
- **Vault System** -- Obsidian-style markdown vaults per class for persistent context
- **Observability** -- SQLite-backed event store with SSE dashboard at `/dashboard/`
- **Frontend** -- React + Zustand + WebSocket for real-time agent interaction

## Quick Start (Docker)

The recommended way to run AcademiaOS:

```bash
# 1. Clone and configure
git clone https://github.com/ron2k1/academia-os.git
cd academia-os
cp .env.example .env

# 2. Edit .env -- add your Anthropic API key
#    ANTHROPIC_API_KEY=sk-ant-XXXX

# 3. Optionally configure your classes
cp config/classes.example.json config/classes.json
# Edit config/classes.json with your semester schedule

# 4. Launch
docker compose up --build

# AcademiaOS is now running at http://localhost:8000
# Observability dashboard at http://localhost:8000/dashboard/
```

### Docker Compose Details

The `docker-compose.yml` provides:

| Feature | Details |
|---------|---------|
| **Build** | Multi-stage: Node 20 for frontend, Python 3.12 for runtime |
| **Ports** | `${PORT:-8000}:8000` (configurable via `.env`) |
| **Volumes** | `vaults/`, `files/`, `progress/`, `config/` persist across restarts |
| **Health check** | `curl -f http://localhost:8000/health` every 30s |
| **Restart** | `unless-stopped` policy |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Server port |
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key for Claude CLI |
| `OPENROUTER_API_KEY` | *(optional)* | Fallback LLM provider |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |

## Quick Start (Local Development)

For development without Docker:

```bash
# Backend
pip install -r requirements.txt
cp config/classes.example.json config/classes.json
cp config/models.example.json config/models.json
python scripts/init_semester.py --config config/classes.json

# Frontend
cd frontend && npm install && npm run build && cd ..

# Run server
uvicorn src.server:app --reload --port 8000

# Run tests
python -m pytest tests/ -v
```

## Project Structure

```
academia-os/
  config/          -- JSON/YAML configs (classes, models, openclaw)
  frontend/        -- React + Vite frontend
  prompts/         -- Agent system prompts (markdown templates)
  scripts/         -- CLI utilities (init_semester, archive_semester)
  src/
    agents/        -- Sub-agent definitions and Claude CLI spawner
    config/        -- Pydantic schemas and config loader
    observability/ -- Event store, emitter, SSE dashboard
    orchestrator/  -- Intent classification, context assembly, relay
    vault/         -- Obsidian-style vault read/write/search
    websocket/     -- Session management and WS message schemas
    server.py      -- FastAPI app entry point
  tasks/           -- Build tracker (todo.md)
  tests/           -- Unit and integration tests
  vaults/          -- Per-class markdown vaults (gitignored, persisted)
  files/           -- Uploaded files (gitignored, persisted)
  progress/        -- Session progress data (gitignored, persisted)
```

## Configuration

### Classes (`config/classes.json`)

Define your semester schedule. Each class gets its own vault and agent context:

```json
[
  {
    "id": "cs301",
    "name": "Algorithms",
    "professor": "Dr. Smith",
    "schedule": "MWF 10:00-10:50",
    "vault_path": "vaults/cs301"
  }
]
```

### Models (`config/models.json`)

Configure which Claude model each agent type uses:

```json
{
  "default": "claude-sonnet-4-20250514",
  "orchestrator": "claude-sonnet-4-20250514",
  "writer": "claude-sonnet-4-20250514"
}
```

### OpenClaw (`config/openclaw.yaml`)

Safety guardrails configuration for content filtering and rate limiting.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Current configuration |
| `GET` | `/api/vaults` | List all vaults |
| `GET` | `/api/vaults/{vault_id}` | List vault files |
| `POST` | `/api/files/upload` | Upload a file |
| `WS` | `/ws` | WebSocket for agent interaction |
| `GET` | `/dashboard/` | Observability dashboard |
| `GET` | `/dashboard/stream` | SSE event stream |

## License

MIT
