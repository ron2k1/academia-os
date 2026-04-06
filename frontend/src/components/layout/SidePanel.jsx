/**
 * SidePanel -- collapsible right panel for files, uploads, and progress.
 */
import useUiStore from '../../stores/uiStore';
import FileList from '../upload/FileList';
import UploadZone from '../upload/UploadZone';
import ClassProgress from '../progress/ClassProgress';

const TABS = [
  { id: 'files', label: 'Files' },
  { id: 'upload', label: 'Upload' },
  { id: 'progress', label: 'Progress' },
];

export default function SidePanel({ classId }) {
  const open = useUiStore((s) => s.sidePanelOpen);
  const tab = useUiStore((s) => s.sidePanelTab);
  const setSidePanelTab = useUiStore((s) => s.setSidePanelTab);
  const toggleSidePanel = useUiStore((s) => s.toggleSidePanel);

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={toggleSidePanel}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-30 bg-gray-800 border border-gray-700 border-r-0 rounded-l-md px-1.5 py-3 text-gray-400 hover:text-cyan-400 transition-colors"
        aria-label={open ? 'Close side panel' : 'Open side panel'}
      >
        <svg
          className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Panel */}
      <aside
        className={`
          fixed top-0 right-0 h-full z-20
          bg-gray-900 border-l border-gray-800 shadow-xl
          transition-transform duration-200 ease-in-out
          w-80 flex flex-col
          ${open ? 'translate-x-0' : 'translate-x-full'}
        `}
        aria-hidden={!open}
      >
        {/* Tab switcher */}
        <div className="flex border-b border-gray-800">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setSidePanelTab(t.id)}
              className={`
                flex-1 px-3 py-2.5 text-sm font-medium transition-colors
                ${
                  tab === t.id
                    ? 'text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-gray-400 hover:text-gray-200'
                }
              `}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-3">
          {tab === 'files' && <FileList classId={classId} />}
          {tab === 'upload' && <UploadZone classId={classId} />}
          {tab === 'progress' && <ClassProgress classId={classId} />}
        </div>
      </aside>
    </>
  );
}
