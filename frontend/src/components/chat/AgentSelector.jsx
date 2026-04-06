/**
 * AgentSelector -- horizontal row of agent buttons for switching active agent.
 */
import { AGENTS, AGENT_ORDER } from '../../utils/constants';

export default function AgentSelector({ activeAgent, onSelect, disabled }) {
  return (
    <div
      className="flex items-center gap-1.5 px-3 py-2 overflow-x-auto border-b border-gray-800"
      role="radiogroup"
      aria-label="Select agent"
    >
      {AGENT_ORDER.map((agentId) => {
        const agent = AGENTS[agentId];
        const isActive = agentId === activeAgent;
        return (
          <button
            key={agentId}
            role="radio"
            aria-checked={isActive}
            disabled={disabled}
            onClick={() => onSelect(agentId)}
            title={agent.description}
            className={`
              px-3 py-1.5 rounded-full text-xs font-medium
              transition-all duration-150 whitespace-nowrap
              focus:outline-none focus:ring-2 ${agent.ringClass}
              ${
                isActive
                  ? `${agent.bgClass} text-white shadow-md`
                  : `bg-gray-800 text-gray-400 hover:text-gray-200 ${agent.hoverClass}`
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            {agent.label}
          </button>
        );
      })}
    </div>
  );
}
