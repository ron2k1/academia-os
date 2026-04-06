/**
 * FileList -- browsable file list organized by upload category.
 *
 * Fetches files from the API for each category and displays them.
 */
import { useState, useEffect, useCallback } from 'react';
import { UPLOAD_CATEGORIES } from '../../utils/constants';
import { listFiles } from '../../services/api';
import { capitalize, formatFileSize } from '../../utils/formatters';

function FileItem({ file }) {
  const ext = file.name?.split('.').pop()?.toLowerCase();
  const isPdf = ext === 'pdf';

  return (
    <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-gray-800/60 transition-colors group">
      <svg
        className={`w-4 h-4 flex-shrink-0 ${isPdf ? 'text-red-400' : 'text-gray-400'}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
        />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 truncate">{file.name}</p>
        {file.size != null && (
          <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
        )}
      </div>
    </div>
  );
}

function CategorySection({ category, files, loading }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="mb-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left px-1 py-1.5 text-xs font-medium text-gray-400 hover:text-gray-200 transition-colors"
        aria-expanded={expanded}
      >
        <svg
          className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="uppercase tracking-wider">{capitalize(category)}</span>
        <span className="text-gray-600 ml-auto">{files.length}</span>
      </button>

      {expanded && (
        <div className="ml-1">
          {loading ? (
            <p className="text-xs text-gray-600 px-2.5 py-2">Loading...</p>
          ) : files.length === 0 ? (
            <p className="text-xs text-gray-600 px-2.5 py-2">No files</p>
          ) : (
            files.map((file, i) => <FileItem key={file.name + i} file={file} />)
          )}
        </div>
      )}
    </div>
  );
}

export default function FileList({ classId }) {
  const [filesByCategory, setFilesByCategory] = useState({});
  const [loading, setLoading] = useState(false);

  const loadFiles = useCallback(async () => {
    if (!classId) return;
    setLoading(true);

    const results = {};
    for (const cat of UPLOAD_CATEGORIES) {
      try {
        results[cat] = await listFiles(classId, cat);
      } catch {
        results[cat] = [];
      }
    }

    setFilesByCategory(results);
    setLoading(false);
  }, [classId]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  if (!classId) {
    return (
      <p className="text-sm text-gray-500 text-center py-8">
        Select a class to view files
      </p>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">Files</h3>
        <button
          onClick={loadFiles}
          disabled={loading}
          className="text-xs text-gray-500 hover:text-cyan-400 transition-colors disabled:opacity-50"
          aria-label="Refresh file list"
        >
          <svg
            className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`}
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

      {UPLOAD_CATEGORIES.map((cat) => (
        <CategorySection
          key={cat}
          category={cat}
          files={filesByCategory[cat] || []}
          loading={loading}
        />
      ))}
    </div>
  );
}
