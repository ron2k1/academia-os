/**
 * TabBar -- horizontal class tabs below the header.
 */
import useClassStore from '../../stores/classStore';

export default function TabBar({ classes }) {
  const activeClassId = useClassStore((s) => s.activeClassId);
  const setActiveClassId = useClassStore((s) => s.setActiveClassId);

  if (!classes || classes.length === 0) return null;

  return (
    <nav
      className="flex items-center gap-0.5 px-2 py-1 bg-gray-900 border-b border-gray-800 overflow-x-auto"
      role="tablist"
      aria-label="Class tabs"
    >
      {classes.map((cls) => {
        const isActive = cls.id === activeClassId;
        return (
          <button
            key={cls.id}
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${cls.id}`}
            onClick={() => setActiveClassId(cls.id)}
            className={`
              px-3 py-1.5 text-sm rounded-t transition-colors whitespace-nowrap
              ${
                isActive
                  ? 'bg-gray-800 text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
              }
            `}
          >
            <span className="font-medium">{cls.name}</span>
            <span className="ml-1.5 text-xs text-gray-500">{cls.code}</span>
          </button>
        );
      })}
    </nav>
  );
}
