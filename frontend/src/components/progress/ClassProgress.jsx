/**
 * ClassProgress -- progress view for a class, combining ProgressTracker and TopicCards.
 *
 * Uses the useProgress hook to load data and renders the overview and per-topic cards.
 */
import useProgress from '../../hooks/useProgress';
import ProgressTracker from './ProgressTracker';
import TopicCard from './TopicCard';

export default function ClassProgress({ classId }) {
  const { progress, loading, error, reload } = useProgress();

  if (!classId) {
    return (
      <p className="text-sm text-gray-500 text-center py-8">
        Select a class to view progress
      </p>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <svg
          className="w-6 h-6 text-cyan-400 animate-spin"
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
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-red-400 mb-2">{error}</p>
        <button
          onClick={reload}
          className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!progress || !progress.topics || progress.topics.length === 0) {
    return (
      <div className="text-center py-8">
        <svg
          className="w-10 h-10 text-gray-600 mx-auto mb-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
          />
        </svg>
        <p className="text-sm text-gray-500">No progress data yet</p>
        <p className="text-xs text-gray-600 mt-1">
          Start chatting with agents to track your learning
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">Progress</h3>
        <button
          onClick={reload}
          className="text-xs text-gray-500 hover:text-cyan-400 transition-colors"
          aria-label="Refresh progress"
        >
          <svg
            className="w-3.5 h-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
            />
          </svg>
        </button>
      </div>

      <ProgressTracker progress={progress} />

      <div className="space-y-2">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
          Topics
        </h3>
        {progress.topics.map((topic, i) => (
          <TopicCard key={topic.name || i} topic={topic} />
        ))}
      </div>
    </div>
  );
}
