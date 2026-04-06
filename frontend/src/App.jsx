/**
 * App -- root component composing the full AcademiaOS layout.
 *
 * Initialises the WebSocket connection, loads class config,
 * and renders Header, TabBar, ChatWindow, SidePanel, and Toasts.
 */
import useWebSocket from './hooks/useWebSocket';
import useClassConfig from './hooks/useClassConfig';
import Header from './components/layout/Header';
import TabBar from './components/layout/TabBar';
import SidePanel from './components/layout/SidePanel';
import ChatWindow from './components/chat/ChatWindow';
import ToastContainer from './components/common/Toast';

export default function App() {
  // Establish WebSocket connection and route messages to stores
  useWebSocket();

  // Load class configuration from the API
  const { activeClasses, activeClassId, semester, loading, error } =
    useClassConfig();

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <Header semester={semester} />
      <TabBar classes={activeClasses} />

      {/* Main content area */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-cyan-400 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
            <svg
              className="w-12 h-12 text-red-400 mb-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
            <p className="text-sm text-red-400 mb-1">Failed to load classes</p>
            <p className="text-xs text-gray-500">{error}</p>
          </div>
        ) : (
          <ChatWindow />
        )}
      </main>

      <SidePanel classId={activeClassId} />
      <ToastContainer />
    </div>
  );
}
