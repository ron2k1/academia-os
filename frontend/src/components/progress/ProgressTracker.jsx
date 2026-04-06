/**
 * ProgressTracker -- overall progress summary with aggregate stats.
 *
 * Shows total topics, average mastery, and visual breakdown.
 */

function StatBox({ label, value, color }) {
  return (
    <div className="flex flex-col items-center p-3 rounded-lg bg-gray-800/60 border border-gray-800">
      <span className={`text-lg font-bold ${color}`}>{value}</span>
      <span className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">
        {label}
      </span>
    </div>
  );
}

export default function ProgressTracker({ progress }) {
  if (!progress || !progress.topics) {
    return null;
  }

  const topics = progress.topics;
  const totalTopics = topics.length;
  const avgMastery =
    totalTopics > 0
      ? Math.round(topics.reduce((sum, t) => sum + (t.mastery ?? 0), 0) / totalTopics)
      : 0;
  const masteredCount = topics.filter((t) => (t.mastery ?? 0) >= 80).length;
  const needsWorkCount = topics.filter((t) => (t.mastery ?? 0) < 50).length;

  return (
    <div className="mb-4">
      <h3 className="text-sm font-medium text-gray-300 mb-3">Overview</h3>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <StatBox label="Topics" value={totalTopics} color="text-gray-200" />
        <StatBox label="Avg Mastery" value={`${avgMastery}%`} color="text-cyan-400" />
        <StatBox label="Mastered" value={masteredCount} color="text-green-400" />
        <StatBox label="Needs Work" value={needsWorkCount} color="text-red-400" />
      </div>

      {/* Overall progress bar */}
      <div className="px-1">
        <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
          <span>Overall Progress</span>
          <span>{avgMastery}%</span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-2">
          <div
            className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${avgMastery}%` }}
            role="progressbar"
            aria-valuenow={avgMastery}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Overall mastery: ${avgMastery}%`}
          />
        </div>
      </div>
    </div>
  );
}
