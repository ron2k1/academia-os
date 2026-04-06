/**
 * Header -- top bar with branding, semester info, connection + health status.
 *
 * Polls /api/health every 30 seconds and on mount to display backend
 * component health alongside the WebSocket connection indicator.
 */
import { useEffect } from 'react';
import useUiStore from '../../stores/uiStore';
import StatusDot from '../common/StatusDot';
import { API_BASE } from '../../utils/constants';

/** Polling interval for health checks (ms). */
const HEALTH_POLL_MS = 30_000;

/**
 * Small colored dot for a single health indicator.
 */
function HealthDot({ ok, label }) {
  return (
    <div className="flex items-center gap-1.5" title={label}>
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          ok === true
            ? 'bg-green-400'
            : ok === false
              ? 'bg-red-400'
              : 'bg-gray-600'
        }`}
      />
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  );
}

export default function Header({ semester }) {
  const wsState = useUiStore((s) => s.wsState);
  const health = useUiStore((s) => s.health);

  // Poll /api/health on mount and every 30 seconds.
  useEffect(() => {
    let cancelled = false;

    async function fetchHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          useUiStore.getState().setHealth(data);
        }
      } catch {
        // Silently ignore -- health stays at last known value or null.
      }
    }

    fetchHealth();
    const id = setInterval(fetchHealth, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="flex items-center justify-between px-4 py-2.5 bg-gray-900 border-b border-gray-800">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-full bg-cyan-500 flex items-center justify-center">
            <span className="text-white text-sm font-bold">A</span>
          </div>
          <h1 className="text-lg font-semibold text-gray-100">
            AcademiaOS
          </h1>
        </div>
        {semester && (
          <span className="text-xs text-gray-500 border-l border-gray-700 pl-3">
            {semester.name}
          </span>
        )}
      </div>
      <div className="flex items-center gap-4">
        {health && (
          <div className="hidden sm:flex items-center gap-3 border-r border-gray-700 pr-4">
            <HealthDot ok={health.gateway} label="Gateway" />
            <HealthDot ok={health.claude_cli} label="Claude" />
            <HealthDot ok={health.config_loaded} label="Config" />
          </div>
        )}
        <StatusDot state={wsState} showLabel />
      </div>
    </header>
  );
}
