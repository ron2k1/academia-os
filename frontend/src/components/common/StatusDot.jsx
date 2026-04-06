/**
 * StatusDot -- small colored circle indicating connection or service status.
 */
import { WS_STATE } from '../../utils/constants';

const STATE_COLORS = {
  [WS_STATE.CONNECTED]: 'bg-green-500',
  [WS_STATE.CONNECTING]: 'bg-yellow-500 animate-pulse',
  [WS_STATE.RECONNECTING]: 'bg-yellow-500 animate-pulse',
  [WS_STATE.DISCONNECTED]: 'bg-red-500',
};

const STATE_LABELS = {
  [WS_STATE.CONNECTED]: 'Connected',
  [WS_STATE.CONNECTING]: 'Connecting...',
  [WS_STATE.RECONNECTING]: 'Reconnecting...',
  [WS_STATE.DISCONNECTED]: 'Disconnected',
};

export default function StatusDot({ state, showLabel = false }) {
  const colorClass = STATE_COLORS[state] || 'bg-gray-500';
  const label = STATE_LABELS[state] || state;

  return (
    <span className="inline-flex items-center gap-1.5" role="status" aria-label={label}>
      <span className={`inline-block h-2 w-2 rounded-full ${colorClass}`} />
      {showLabel && (
        <span className="text-xs text-gray-400">{label}</span>
      )}
    </span>
  );
}
