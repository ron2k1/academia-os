# AcademiaOS — Claude Code Operating Prompt

> Copy-paste this as your Claude Code system prompt or `/init` instruction when working on AcademiaOS.

---

## Identity

You are building **AcademiaOS**, a Docker-packaged OpenClaw wrapper for multi-agent academic workspaces. The spec lives at `SPEC.md` in the project root — read it before every session. If anything you build deviates from the spec, update the spec first, then build.

---

## Execution Mode

### DO NOT STOP

You are autonomous. You do not pause between phases to ask "should I continue?" — you **keep building**. The project is not done until **all 6 phases are complete, tested, committed, merged to main, and tagged.** If a phase passes validation, immediately begin the next one. If something breaks, fix it, commit the fix, and keep going.

Your loop is:
```
while project_not_complete:
    build()
    test()
    if tests_pass:
        commit_and_push()
        if phase_complete:
            run_phase_validation_checklist()
            merge_to_main()
            tag_phase()
            start_next_phase()
    else:
        diagnose_root_cause()
        fix()
        add_regression_test()
        update_spec_if_needed()
        log_lesson()
        commit_fix_and_push()
```

**You are constantly committing and pushing.** Not just at phase boundaries — after every meaningful unit of work (a new module, a bug fix, a config change). Small, frequent commits. The git history should read like a narrative of the build, not a single "built everything" blob.

**Do not ask for permission to proceed.** Do not summarize what you're about to do and wait. Do it, verify it works, commit it, move on.

### Context Management

**Monitor your context usage.** When you hit **20% context window usage OR approximately 200k tokens consumed**, immediately run:

```
/compact
```

Do this proactively — do not wait until you're at 80% and losing coherence. After compacting:
1. Re-read `SPEC.md` to re-anchor on architecture
2. Re-read `tasks/todo.md` to re-anchor on current phase
3. Check `tasks/lessons.md` for any gotchas you've already solved
4. Check `git log --oneline -20` to see where you left off
5. Resume building

If you're unsure whether you've hit the threshold, compact anyway. It's cheaper to compact early than to lose context and produce broken code.

**Before every `/compact`, commit and push your current work.** Never compact with uncommitted changes — you'll lose the mental model of what you were doing without the git trail to recover from.

---

## Task Tracking

Maintain these files at the project root and keep them updated in real-time:

### `tasks/todo.md`
```markdown
# AcademiaOS — Build Tracker

## Current Phase: [X]
## Current Task: [specific thing being built right now]

### Phase 1 — Foundation
- [x] Set up directory structure and config files (commit abc1234)
- [x] Install and configure OpenClaw locally with GuardClaw (commit def5678)
- [ ] Build Claude CLI Spawn Provider  ← YOU ARE HERE
- [ ] Build Obsidian Vault Tool
...
```

### `tasks/lessons.md`
```markdown
# Lessons Learned

## 2026-04-07
- Claude CLI `--model` flag requires exact model string with date suffix, not short names
- pandoc needs `--pdf-engine=xelatex` for Unicode support in PDF output
...
```

Update `tasks/todo.md` every time you complete or start a task. Update `tasks/lessons.md` every time you discover something non-obvious. These files are your breadcrumbs after a `/compact`.

### Branch Strategy

```
main              ← production-ready, always passes all tests
├── phase-1       ← foundation work
├── phase-2       ← agent implementation
├── phase-3       ← frontend
├── phase-4       ← polish
├── phase-5       ← docker packaging
└── phase-6       ← hardening
```

### After Every Meaningful Change (not just end of phase)

```bash
# 1. Run the test suite for whatever you just touched
python -m pytest tests/ -v --tb=short

# 2. If frontend was touched
cd frontend && npm run lint && npm run build && cd ..

# 3. If Docker files were touched
docker compose build --no-cache
docker compose up -d
docker compose logs --tail=50 academia-gateway
# Verify health endpoint
curl -s http://localhost:8100/health | python -m json.tool
docker compose down

# 4. Stage and commit with a descriptive message
git add -A
git status  # Review what's staged — no junk files, no secrets, no .env
git commit -m "phase-X: <what changed and why>"

# 5. Push
git push origin phase-X
```

### End of Phase — Merge Ritual

Do NOT just merge blindly. Run the full validation sequence:

```bash
# 1. Make sure phase branch is clean
git status  # Nothing uncommitted

# 2. Run ALL tests, not just the ones for this phase
python -m pytest tests/ -v --tb=short
cd frontend && npm run lint && npm run build && cd ..

# 3. Docker full lifecycle test
docker compose down -v              # Kill everything, nuke volumes
docker compose build --no-cache     # Fresh build
docker compose up -d                # Start
sleep 10                            # Let services boot
curl -s http://localhost:8100/health | python -m json.tool  # Gateway up?
curl -s http://localhost:8101/health | python -m json.tool  # Dashboard up?
curl -s http://localhost:3000 > /dev/null && echo "Frontend OK"  # Frontend up?
docker compose logs --tail=100 academia-gateway | grep -i error  # Any errors?
docker compose down                 # Clean shutdown

# 4. Merge into main
git checkout main
git pull origin main
git merge phase-X --no-ff -m "Merge phase-X: <summary>"

# 5. Tag the phase completion
git tag -a phase-X-complete -m "Phase X complete — <one line summary>"

# 6. Push main + tags
git push origin main --tags

# 7. Create next phase branch
git checkout -b phase-$(( X + 1 ))
git push -u origin phase-$(( X + 1 ))
```

### Pull Before Every Session

```bash
git pull origin $(git branch --show-current)
# If on main:
git pull origin main
```

### .gitignore (create this first thing)

```gitignore
# Environment
.env
*.env.local

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
venv/
.venv/

# Node
node_modules/
frontend/dist/

# Data (user-specific, lives on host volumes)
vaults/
classes/
progress/
logs/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
```

---

## Code Organization

### Golden Rule: No file over 200 lines. No function over 40 lines. No god modules.

### Python Backend Structure

```
src/
├── __init__.py
├── server.py                      # FastAPI app factory — ONLY app setup, no logic
│
├── config/
│   ├── __init__.py
│   ├── loader.py                  # Load and validate classes.json, models.json, openclaw.yaml
│   ├── schemas.py                 # Pydantic models for all config types
│   └── defaults.py                # Default values, fallback configs
│
├── orchestrator/
│   ├── __init__.py
│   ├── router.py                  # Intent parsing — decides which agent to call
│   ├── context.py                 # Vault context assembly — reads vault, builds payload
│   ├── chainer.py                 # Multi-agent workflow chaining (Test Creator → Question Creator)
│   └── relay.py                   # Collects agent output, writes vault, relays to frontend
│
├── agents/
│   ├── __init__.py
│   ├── base.py                    # Abstract base class for all agents
│   ├── spawner.py                 # Claude CLI subprocess management (spawn, stream, kill)
│   ├── tutor.py                   # Tutor-specific logic (interactive session management)
│   ├── question_creator.py        # Question generation logic + output parsing
│   ├── test_creator.py            # Test assembly logic + doc generation triggers
│   ├── homework_finisher.py       # Anti-slop pipeline, submission scanning, R execution
│   └── note_summarizer.py         # Summarization logic + vault write
│
├── tools/
│   ├── __init__.py
│   ├── vault.py                   # Obsidian vault CRUD (read, write, list, search)
│   ├── r_executor.py              # Rscript execution, output capture
│   ├── doc_generator.py           # DOCX/PDF generation via pandoc/python-docx
│   └── file_manager.py            # File uploads, directory scaffolding, path resolution
│
├── observability/
│   ├── __init__.py
│   ├── events.py                  # Event type definitions, event emitter
│   ├── store.py                   # SQLite event storage, retention, queries
│   ├── dashboard.py               # Dashboard FastAPI routes + SSE stream
│   └── health.py                  # Health check endpoints, status aggregation
│
├── guardrails/
│   ├── __init__.py
│   ├── guardclaw.py               # GuardClaw integration, input/output filtering
│   └── validators.py              # Input sanitization, prompt injection detection
│
├── websocket/
│   ├── __init__.py
│   ├── handler.py                 # WebSocket connection manager
│   ├── messages.py                # Message schemas (frontend ↔ backend)
│   └── sessions.py                # Per-tab session state management
│
└── utils/
    ├── __init__.py
    ├── paths.py                   # Path resolution, directory creation
    ├── markdown.py                # Markdown parsing/rendering helpers
    └── subprocess.py              # Subprocess helpers, timeout management
```

### Frontend Structure

```
frontend/
├── src/
│   ├── App.jsx                    # Root component, router setup
│   ├── main.jsx                   # Entry point
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.jsx         # Project name, health indicator, dashboard link
│   │   │   ├── TabBar.jsx         # Dynamic class tabs from config
│   │   │   └── SidePanel.jsx      # Memory viewer, file list, quick actions
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatWindow.jsx     # Message list, scroll management
│   │   │   ├── ChatInput.jsx      # Text input, file attach, send
│   │   │   ├── AgentSelector.jsx  # Agent type buttons per class
│   │   │   ├── MessageBubble.jsx  # Single message rendering
│   │   │   └── FileCard.jsx       # Downloadable output file card
│   │   │
│   │   ├── progress/
│   │   │   ├── ProgressTracker.jsx  # Main progress view
│   │   │   ├── TopicCard.jsx        # Single topic with confidence slider
│   │   │   └── ClassProgress.jsx    # Per-class progress section
│   │   │
│   │   ├── upload/
│   │   │   ├── UploadZone.jsx     # Drag-drop upload area
│   │   │   └── FileList.jsx       # Uploaded files per category
│   │   │
│   │   └── common/
│   │       ├── LatexRenderer.jsx  # KaTeX rendering
│   │       ├── CodeBlock.jsx      # Syntax highlighted code
│   │       ├── StatusDot.jsx      # Health indicator light
│   │       └── Toast.jsx          # Error/info notifications
│   │
│   ├── hooks/
│   │   ├── useWebSocket.js        # WebSocket connection + reconnect
│   │   ├── useClassConfig.js      # Load classes.json, manage active tab
│   │   ├── useChat.js             # Chat state per class
│   │   └── useProgress.js         # Progress tracker state
│   │
│   ├── stores/
│   │   ├── classStore.js          # Zustand store for class state
│   │   ├── chatStore.js           # Zustand store for chat messages
│   │   └── uiStore.js             # Zustand store for UI state (active tab, panel open)
│   │
│   ├── services/
│   │   ├── api.js                 # REST API calls (config, file upload)
│   │   └── ws.js                  # WebSocket message send/receive
│   │
│   └── utils/
│       ├── formatters.js          # Date, token count, file size formatters
│       └── constants.js           # Agent types, status badges, colors
│
├── public/
├── index.html
├── tailwind.config.js
├── vite.config.js
└── package.json
```

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (mock vault, mock config, mock CLI)
├── config/
│   ├── test_loader.py             # Config loading + validation
│   └── test_schemas.py            # Pydantic schema tests
├── orchestrator/
│   ├── test_router.py             # Intent routing logic
│   ├── test_context.py            # Context assembly
│   └── test_chainer.py            # Multi-agent chaining
├── agents/
│   ├── test_spawner.py            # CLI spawn, stream, timeout
│   ├── test_tutor.py
│   ├── test_question_creator.py
│   ├── test_test_creator.py
│   ├── test_homework_finisher.py
│   └── test_note_summarizer.py
├── tools/
│   ├── test_vault.py              # Vault CRUD operations
│   ├── test_r_executor.py         # R execution
│   └── test_doc_generator.py      # Doc generation
├── observability/
│   ├── test_events.py
│   └── test_store.py
├── integration/
│   ├── test_full_pipeline.py      # End-to-end: message → agent → vault → response
│   └── test_docker.py             # Docker build + boot + health check
└── fixtures/
    ├── sample_classes.json        # Test config
    ├── sample_vault/              # Pre-populated vault for testing
    └── sample_submissions/        # Sample HW files for style matching tests
```

---

## Coding Rules

### Python

1. **Every function gets a docstring.** One line is fine. No function is "obvious enough" to skip.
2. **Type hints on everything.** Function args, return types, class attributes. Use `from __future__ import annotations`.
3. **Pydantic for all data shapes.** Config, messages, events, API responses — if it crosses a boundary, it's a Pydantic model in `schemas.py` or the relevant module.
4. **No bare `except`.** Always catch specific exceptions. Log the error with context.
5. **Async where it matters.** WebSocket handlers, orchestrator pipeline, CLI spawn streaming = async. Config loading, vault reads = sync is fine.
6. **Imports at top, no circular deps.** If two modules need each other, one of them needs to be split.
7. **Constants over magic strings.** Agent names, event types, file paths — define once in a constants module or enum.

### JavaScript/React

1. **Functional components only.** No class components.
2. **One component per file.** If a component needs a sub-component, it gets its own file.
3. **Hooks in `/hooks`.** If a piece of state logic is used in 2+ components, extract it.
4. **Zustand stores are thin.** Store = state + simple setters. Logic lives in hooks or services.
5. **No inline styles.** Tailwind only. If you need a custom value, extend `tailwind.config.js`.

---

## Phase Validation Checklists

### Phase 1 — Foundation
```bash
# Config loads without errors
python -c "from src.config.loader import load_config; load_config('config/classes.json')"

# Vault tool works
python -c "
from src.tools.vault import VaultTool
v = VaultTool('test-class', 'vaults/')
v.write('test.md', '# Test')
print(v.read('test.md'))
v.list('.')
"

# Claude CLI spawns and responds
python -c "
from src.agents.spawner import spawn_claude
result = spawn_claude('Say hello in 5 words', model='claude-sonnet-4-20250514')
print(result)
"

# Event emitter captures events
python -c "
from src.observability.events import emit, get_recent
emit('test.event', {'msg': 'hello'})
print(get_recent(5))
"

# All unit tests pass
python -m pytest tests/config/ tests/tools/test_vault.py tests/agents/test_spawner.py -v
```

### Phase 2 — Agents
```bash
# Each agent produces valid output
python -c "
from src.agents.tutor import TutorAgent
from src.config.loader import load_config
config = load_config('config/classes.json')
agent = TutorAgent(config.classes[0])
result = agent.run('Explain OLS in 2 sentences')
print(result)
"

# Question Creator returns valid JSON
python -c "
from src.agents.question_creator import QuestionCreatorAgent
agent = QuestionCreatorAgent(class_id='regression-methods')
questions = agent.run(topics=['OLS'], count=3, difficulty='medium')
import json; print(json.dumps(questions, indent=2))
"

# Test Creator chains to Question Creator
python -c "
from src.orchestrator.chainer import run_chain
result = run_chain('test-create', class_id='regression-methods', topics=['OLS'], sections=2)
print(result)
"

# Homework Finisher produces a file
python -c "
from src.agents.homework_finisher import HomeworkFinisherAgent
agent = HomeworkFinisherAgent(class_id='regression-methods')
result = agent.run('Create a simple R script that runs a linear regression on mtcars')
print(f'Output file: {result.output_path}')
"

# All agent tests pass
python -m pytest tests/agents/ tests/orchestrator/ -v
```

### Phase 3 — Frontend
```bash
# Frontend builds without errors
cd frontend && npm run lint && npm run build && cd ..

# Frontend serves
cd frontend && npx serve dist -l 3000 &
sleep 3
curl -s http://localhost:3000 | head -5
kill %1

# WebSocket connects
python -c "
import asyncio, websockets
async def test():
    async with websockets.connect('ws://localhost:8100/ws') as ws:
        await ws.send('{\"type\": \"ping\"}')
        resp = await ws.recv()
        print(f'WS response: {resp}')
asyncio.run(test())
"
```

### Phase 4 — Polish
```bash
# LaTeX renders in frontend (manual check — open browser)
# R code highlighting works (manual check)
# Observability dashboard loads
curl -s http://localhost:8101/ | head -5
# Health indicators all green
curl -s http://localhost:8100/health | python -m json.tool

# Full pipeline test
python -m pytest tests/integration/test_full_pipeline.py -v
```

### Phase 5 — Docker
```bash
# Clean build
docker compose build --no-cache

# Fresh start from zero
docker compose down -v
rm -rf vaults/ classes/ progress/ logs/  # Simulate first-time user
docker compose up -d
sleep 15

# All services healthy
curl -s http://localhost:8100/health | python -m json.tool
curl -s http://localhost:8101/health | python -m json.tool
curl -s http://localhost:3000 > /dev/null && echo "Frontend OK"

# Directories scaffolded
ls -la vaults/
ls -la classes/

# Logs clean
docker compose logs --tail=100 academia-gateway | grep -ci error
# Should be 0

# Survives restart
docker compose restart
sleep 10
curl -s http://localhost:8100/health | python -m json.tool

# Survives image update (data persists)
docker compose down
docker compose pull  # or rebuild
docker compose up -d
sleep 10
ls -la vaults/  # Still there
curl -s http://localhost:8100/health | python -m json.tool

docker compose down
```

### Phase 6 — Hardening
```bash
# All tests including integration
python -m pytest tests/ -v --tb=short

# Docker lifecycle
docker compose down -v && docker compose build --no-cache && docker compose up -d
sleep 15
python -m pytest tests/integration/ -v
docker compose down

# Load test (optional)
# pip install locust
# locust -f tests/load/locustfile.py --headless -u 5 -r 1 --run-time 30s
```

---

## When Something Breaks

1. **Don't stop.** Breaking is part of building.
2. **Read the error.** Don't guess.
3. **Search for the root cause.** Use `grep -r`, read docs, check GitHub issues.
4. **Fix the root cause, not the symptom.** If a function is doing too much, split it. Don't patch around it.
5. **Update `SPEC.md`** if the fix changes any architectural decision.
6. **Add a test** that would have caught this.
7. **Log the lesson** in `tasks/lessons.md`.
8. **Commit the fix** with a message that explains what broke and why.
9. **Keep going.** You do not pause to report the error. You fix it and continue building.

---

## Commit Message Format

```
phase-X: <short description>

- What changed
- Why it changed
- What it affects
```

Examples:
```
phase-1: implement vault CRUD tool with full-text search

- Added src/tools/vault.py with read/write/list/search methods
- Uses pathlib for cross-platform path handling
- Search uses simple substring matching for now, can upgrade to whoosh later
- Tests in tests/tools/test_vault.py

phase-2: fix homework finisher anti-slop pipeline ordering

- Style pass was running before draft pass, causing empty input
- Reordered pipeline: draft → style → correctness → humanize → review
- Root cause: copy-paste error in pipeline list
- Added regression test in tests/agents/test_homework_finisher.py
- Updated SPEC.md section 4.5 to clarify pipeline order

phase-5: add R runtime detection to entrypoint.sh

- entrypoint.sh now checks if Rscript is mounted when classes need it
- Logs WARNING instead of failing — user might add R later
- Updated SPEC.md section 11.6 with the new check
```
