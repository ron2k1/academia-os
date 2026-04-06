"""Observability dashboard -- FastAPI sub-app with SSE event streaming."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from src.observability.events import EventType, get_recent
from src.observability.store import EventStore

logger = logging.getLogger(__name__)

# Sub-application for the dashboard
dashboard_app = FastAPI(title="AcademiaOS Dashboard", version="1.0.0")

# Reference to the main store (set by mount_dashboard)
_store: EventStore | None = None


def set_dashboard_store(store: EventStore) -> None:
    """Set the EventStore reference for dashboard queries.

    Args:
        store: The EventStore instance to query against.
    """
    global _store  # noqa: PLW0603
    _store = store


def _get_store() -> EventStore:
    """Get the current EventStore, falling back to events module default.

    Returns:
        The active EventStore instance.
    """
    if _store is not None:
        return _store
    from src.observability.events import _get_store as _events_get_store
    return _events_get_store()


# ---------------------------------------------------------------------------
# SSE Event Stream
# ---------------------------------------------------------------------------

async def _event_generator(
    last_id: str | None = None,
    event_type: str | None = None,
    class_id: str | None = None,
):
    """Async generator that yields new events as SSE data.

    Polls the store at 1-second intervals for new events.

    Args:
        last_id: Only yield events after this event ID.
        event_type: Filter to a specific event type.
        class_id: Filter to a specific class ID.

    Yields:
        Dict with 'event', 'id', and 'data' keys for SSE.
    """
    seen_ids: set[str] = set()
    if last_id:
        seen_ids.add(last_id)

    while True:
        try:
            events = get_recent(100)
            for event in reversed(events):
                if event.id in seen_ids:
                    continue
                seen_ids.add(event.id)

                # Apply filters
                if event_type and event.event_type.value != event_type:
                    continue
                if class_id and event.class_id != class_id:
                    continue

                yield {
                    "event": "observability",
                    "id": event.id,
                    "data": json.dumps({
                        "id": event.id,
                        "timestamp": event.timestamp.isoformat(),
                        "event_type": event.event_type.value,
                        "class_id": event.class_id,
                        "agent": event.agent,
                        "data": event.data,
                    }),
                }

            # Cap seen_ids to prevent unbounded memory growth
            if len(seen_ids) > 5000:
                seen_ids.clear()

        except Exception as exc:
            logger.error("SSE generator error: %s", exc)

        await asyncio.sleep(1.0)


@dashboard_app.get("/events/stream")
async def event_stream(
    last_id: str | None = Query(None),
    event_type: str | None = Query(None),
    class_id: str | None = Query(None),
):
    """SSE endpoint streaming observability events in real time.

    Args:
        last_id: Resume from this event ID.
        event_type: Filter by event type string.
        class_id: Filter by class ID.

    Returns:
        EventSourceResponse with live event stream.
    """
    return EventSourceResponse(
        _event_generator(last_id, event_type, class_id)
    )


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@dashboard_app.get("/health")
async def dashboard_health() -> dict[str, Any]:
    """Dashboard health check.

    Returns:
        Health status with event count.
    """
    try:
        count = _get_store().count()
    except Exception:
        count = -1
    return {
        "status": "ok",
        "dashboard": True,
        "event_count": count,
    }


@dashboard_app.get("/events")
async def list_events(
    limit: int = Query(50, ge=1, le=500),
    event_type: str | None = Query(None),
    class_id: str | None = Query(None),
) -> dict[str, Any]:
    """List recent observability events with optional filtering.

    Args:
        limit: Maximum events to return (1-500).
        event_type: Filter by event type string.
        class_id: Filter by class ID.

    Returns:
        Dictionary with list of event dicts and total count.
    """
    events = get_recent(limit)

    # Apply filters
    if event_type:
        events = [e for e in events if e.event_type.value == event_type]
    if class_id:
        events = [e for e in events if e.class_id == class_id]

    return {
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type.value,
                "class_id": e.class_id,
                "agent": e.agent,
                "data": e.data,
            }
            for e in events
        ],
        "total": _get_store().count(),
    }


@dashboard_app.get("/stats")
async def event_stats() -> dict[str, Any]:
    """Compute aggregate statistics from recent events.

    Returns per-agent invocation counts, success rates, and average
    latency from AGENT_SPAWN, AGENT_COMPLETE, and AGENT_ERROR events.

    Returns:
        Dictionary with agent stats, event type breakdown, and total.
    """
    events = get_recent(500)
    total = _get_store().count()

    # Event type breakdown
    type_counts: Counter = Counter()
    for e in events:
        type_counts[e.event_type.value] += 1

    # Per-agent stats
    agent_spawns: Counter = Counter()
    agent_completes: Counter = Counter()
    agent_errors: Counter = Counter()
    agent_latencies: dict[str, list[float]] = {}

    for e in events:
        if e.event_type == EventType.AGENT_SPAWN:
            agent_spawns[e.agent] += 1
        elif e.event_type == EventType.AGENT_COMPLETE:
            agent_completes[e.agent] += 1
            latency = e.data.get("wall_time_ms", 0)
            if latency > 0:
                agent_latencies.setdefault(e.agent, []).append(latency)
        elif e.event_type == EventType.AGENT_ERROR:
            agent_errors[e.agent] += 1

    all_agents = set(agent_spawns) | set(agent_completes) | set(agent_errors)
    agents_stats = {}
    for agent in sorted(all_agents):
        spawns = agent_spawns.get(agent, 0)
        completes = agent_completes.get(agent, 0)
        errors = agent_errors.get(agent, 0)
        latencies = agent_latencies.get(agent, [])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        success_rate = (
            completes / spawns * 100 if spawns > 0 else 0
        )

        agents_stats[agent] = {
            "invocations": spawns,
            "completions": completes,
            "errors": errors,
            "success_rate": round(success_rate, 1),
            "avg_latency_ms": round(avg_latency, 1),
        }

    return {
        "total_events": total,
        "recent_window": len(events),
        "by_type": dict(type_counts),
        "agents": agents_stats,
    }


# ---------------------------------------------------------------------------
# Self-contained HTML Dashboard
# ---------------------------------------------------------------------------

@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard_page() -> str:
    """Serve the self-contained observability dashboard HTML page.

    Returns:
        Complete HTML page with embedded CSS and JavaScript.
    """
    return _build_dashboard_html()


def _build_dashboard_html() -> str:
    """Build a self-contained HTML dashboard page.

    Returns:
        Complete HTML string with embedded styles and scripts.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>AcademiaOS -- Observability Dashboard</title>
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #111118;
    --border: #1e1e2e;
    --text: #e4e4ef;
    --muted: #6b6b80;
    --accent: #22d3ee;
    --success: #34d399;
    --error: #f87171;
    --warning: #fbbf24;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    line-height: 1.5;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  header h1 { font-size: 1.25rem; font-weight: 600; }
  header h1 span { color: var(--accent); }
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    background: rgba(34, 211, 238, 0.1);
    color: var(--accent);
    border: 1px solid rgba(34, 211, 238, 0.2);
  }
  .status-badge .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin: 24px 0;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }
  .card .label { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .card .value { font-size: 1.75rem; font-weight: 700; margin-top: 4px; }
  .card .value.accent { color: var(--accent); }
  .card .value.success { color: var(--success); }
  .card .value.error { color: var(--error); }
  .event-log {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
  }
  .event-log-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
  }
  .event-log-header h2 { font-size: 1rem; font-weight: 600; }
  .event-list {
    max-height: 500px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }
  .event-item {
    display: grid;
    grid-template-columns: 180px 180px 100px 1fr;
    gap: 12px;
    padding: 10px 20px;
    border-bottom: 1px solid var(--border);
    font-size: 0.85rem;
    align-items: center;
  }
  .event-item:hover { background: rgba(255,255,255,0.02); }
  .event-item .time { color: var(--muted); font-family: monospace; font-size: 0.8rem; }
  .event-item .type {
    font-family: monospace;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
  }
  .type-spawn { background: rgba(34, 211, 238, 0.15); color: var(--accent); }
  .type-complete { background: rgba(52, 211, 153, 0.15); color: var(--success); }
  .type-error { background: rgba(248, 113, 113, 0.15); color: var(--error); }
  .type-default { background: rgba(107, 107, 128, 0.15); color: var(--muted); }
  .event-item .agent { color: var(--accent); }
  .event-item .data { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .agents-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 24px;
  }
  .agents-table th {
    text-align: left;
    padding: 12px 16px;
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border);
  }
  .agents-table td {
    padding: 12px 16px;
    font-size: 0.9rem;
    border-bottom: 1px solid var(--border);
  }
  .agents-table tr:hover td { background: rgba(255,255,255,0.02); }
  .empty-state {
    padding: 40px 20px;
    text-align: center;
    color: var(--muted);
    font-size: 0.9rem;
  }
  #connection-status { transition: color 0.3s; }
</style>
</head>
<body>
<header>
  <h1><span>AcademiaOS</span> Observability</h1>
  <div class="status-badge">
    <div class="dot"></div>
    <span id="connection-status">Connecting...</span>
  </div>
</header>

<div class="container">
  <!-- Stats Cards -->
  <div class="grid" id="stats-grid">
    <div class="card">
      <div class="label">Total Events</div>
      <div class="value accent" id="stat-total">--</div>
    </div>
    <div class="card">
      <div class="label">Agent Invocations</div>
      <div class="value" id="stat-invocations">--</div>
    </div>
    <div class="card">
      <div class="label">Success Rate</div>
      <div class="value success" id="stat-success">--</div>
    </div>
    <div class="card">
      <div class="label">Errors</div>
      <div class="value error" id="stat-errors">--</div>
    </div>
  </div>

  <!-- Agent Stats Table -->
  <div class="card" id="agents-section" style="margin-bottom: 24px;">
    <h2 style="font-size: 1rem; font-weight: 600; margin-bottom: 12px;">Agent Performance</h2>
    <table class="agents-table">
      <thead>
        <tr>
          <th>Agent</th>
          <th>Invocations</th>
          <th>Completions</th>
          <th>Errors</th>
          <th>Success Rate</th>
          <th>Avg Latency</th>
        </tr>
      </thead>
      <tbody id="agents-tbody">
        <tr><td colspan="6" class="empty-state">Loading...</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Live Event Log -->
  <div class="event-log">
    <div class="event-log-header">
      <h2>Live Event Stream</h2>
      <span id="event-count" style="font-size: 0.8rem; color: var(--muted);">0 events</span>
    </div>
    <div class="event-list" id="event-list">
      <div class="empty-state">Waiting for events...</div>
    </div>
  </div>
</div>

<script>
(function() {
  const MAX_DISPLAY_EVENTS = 200;
  let events = [];
  let evtSource = null;

  function getTypeClass(type) {
    if (type.includes('spawn')) return 'type-spawn';
    if (type.includes('complete')) return 'type-complete';
    if (type.includes('error')) return 'type-error';
    return 'type-default';
  }

  function formatTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-US', { hour12: false, fractionalSecondDigits: 1 });
  }

  function truncateData(data) {
    const s = JSON.stringify(data);
    return s.length > 80 ? s.slice(0, 77) + '...' : s;
  }

  function renderEvents() {
    const list = document.getElementById('event-list');
    const count = document.getElementById('event-count');
    count.textContent = events.length + ' events';

    if (events.length === 0) {
      list.innerHTML = '<div class="empty-state">Waiting for events...</div>';
      return;
    }

    let html = '';
    for (let i = 0; i < Math.min(events.length, MAX_DISPLAY_EVENTS); i++) {
      const e = events[i];
      html += '<div class="event-item">'
        + '<span class="time">' + formatTime(e.timestamp) + '</span>'
        + '<span class="type ' + getTypeClass(e.event_type) + '">' + e.event_type + '</span>'
        + '<span class="agent">' + (e.agent || '-') + '</span>'
        + '<span class="data">' + truncateData(e.data) + '</span>'
        + '</div>';
    }
    list.innerHTML = html;
  }

  function renderAgents(agents) {
    const tbody = document.getElementById('agents-tbody');
    const keys = Object.keys(agents);
    if (keys.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No agent data yet</td></tr>';
      return;
    }
    let html = '';
    for (const name of keys) {
      const a = agents[name];
      html += '<tr>'
        + '<td style="color: var(--accent); font-weight: 500;">' + name + '</td>'
        + '<td>' + a.invocations + '</td>'
        + '<td>' + a.completions + '</td>'
        + '<td style="color: ' + (a.errors > 0 ? 'var(--error)' : 'inherit') + ';">' + a.errors + '</td>'
        + '<td style="color: var(--success);">' + a.success_rate + '%</td>'
        + '<td>' + (a.avg_latency_ms > 0 ? a.avg_latency_ms + 'ms' : '-') + '</td>'
        + '</tr>';
    }
    tbody.innerHTML = html;
  }

  async function fetchStats() {
    try {
      const resp = await fetch('./stats');
      const data = await resp.json();
      document.getElementById('stat-total').textContent = data.total_events;

      let totalInvocations = 0;
      let totalCompletions = 0;
      let totalErrors = 0;
      for (const a of Object.values(data.agents)) {
        totalInvocations += a.invocations;
        totalCompletions += a.completions;
        totalErrors += a.errors;
      }
      document.getElementById('stat-invocations').textContent = totalInvocations;
      document.getElementById('stat-errors').textContent = totalErrors;
      const rate = totalInvocations > 0 ? (totalCompletions / totalInvocations * 100).toFixed(1) : '0';
      document.getElementById('stat-success').textContent = rate + '%';

      renderAgents(data.agents);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }

  function connectSSE() {
    const status = document.getElementById('connection-status');
    evtSource = new EventSource('./events/stream');

    evtSource.addEventListener('observability', function(e) {
      const event = JSON.parse(e.data);
      events.unshift(event);
      if (events.length > MAX_DISPLAY_EVENTS) events.length = MAX_DISPLAY_EVENTS;
      renderEvents();
    });

    evtSource.onopen = function() {
      status.textContent = 'Connected';
      status.style.color = 'var(--success)';
    };

    evtSource.onerror = function() {
      status.textContent = 'Reconnecting...';
      status.style.color = 'var(--warning)';
    };
  }

  // Initial load
  fetchStats();
  connectSSE();

  // Refresh stats every 10 seconds
  setInterval(fetchStats, 10000);
})();
</script>
</body>
</html>"""
