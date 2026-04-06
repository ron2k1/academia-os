/**
 * Header -- top bar with branding, semester info, and connection status.
 */
import useUiStore from '../../stores/uiStore';
import StatusDot from '../common/StatusDot';

export default function Header({ semester }) {
  const wsState = useUiStore((s) => s.wsState);

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
        <StatusDot state={wsState} showLabel />
      </div>
    </header>
  );
}
