/**
 * TopicCard -- displays progress for a single topic/concept.
 *
 * Shows topic name, mastery percentage, and a visual progress bar.
 */

function getMasteryColor(mastery) {
  if (mastery >= 80) return { bar: 'bg-green-500', text: 'text-green-400' };
  if (mastery >= 50) return { bar: 'bg-yellow-500', text: 'text-yellow-400' };
  return { bar: 'bg-red-500', text: 'text-red-400' };
}

export default function TopicCard({ topic }) {
  const mastery = topic.mastery ?? 0;
  const colors = getMasteryColor(mastery);

  return (
    <div className="px-3 py-2.5 rounded-lg bg-gray-800/50 border border-gray-800 hover:border-gray-700 transition-colors">
      <div className="flex items-center justify-between mb-1.5">
        <h4 className="text-sm font-medium text-gray-200 truncate flex-1 mr-2">
          {topic.name}
        </h4>
        <span className={`text-xs font-medium ${colors.text} flex-shrink-0`}>
          {mastery}%
        </span>
      </div>

      <div className="w-full bg-gray-700 rounded-full h-1.5">
        <div
          className={`${colors.bar} h-1.5 rounded-full transition-all duration-300`}
          style={{ width: `${mastery}%` }}
          role="progressbar"
          aria-valuenow={mastery}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${topic.name} mastery: ${mastery}%`}
        />
      </div>

      {topic.lastPracticed && (
        <p className="text-[10px] text-gray-500 mt-1.5">
          Last practiced: {new Date(topic.lastPracticed).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
