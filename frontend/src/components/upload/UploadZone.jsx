/**
 * UploadZone -- drag-and-drop file upload area with category selection.
 *
 * Uses react-dropzone for drag events and the uploadFile API service.
 */
import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UPLOAD_CATEGORIES } from '../../utils/constants';
import { uploadFile } from '../../services/api';
import { capitalize } from '../../utils/formatters';
import useUiStore from '../../stores/uiStore';

function CategorySelect({ value, onChange }) {
  return (
    <div className="mb-3">
      <label htmlFor="upload-category" className="block text-xs text-gray-400 mb-1">
        Category
      </label>
      <select
        id="upload-category"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
      >
        {UPLOAD_CATEGORIES.map((cat) => (
          <option key={cat} value={cat}>
            {capitalize(cat)}
          </option>
        ))}
      </select>
    </div>
  );
}

function UploadProgress({ filename, progress }) {
  return (
    <div className="mt-3 px-1">
      <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
        <span className="truncate max-w-[70%]">{filename}</span>
        <span>{progress}%</span>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-1.5">
        <div
          className="bg-cyan-500 h-1.5 rounded-full transition-all duration-200"
          style={{ width: `${progress}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}

export default function UploadZone({ classId }) {
  const [category, setCategory] = useState(UPLOAD_CATEGORIES[0]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState(null);
  const addToast = useUiStore((s) => s.addToast);

  const onDrop = useCallback(
    async (acceptedFiles) => {
      if (!classId || acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setUploading(true);
      setProgress(0);
      setCurrentFile(file.name);

      try {
        await uploadFile(classId, category, file, (pct) => setProgress(pct));
        addToast(`Uploaded ${file.name} successfully`, 'success');
      } catch (err) {
        addToast(err.message || 'Upload failed', 'error');
      } finally {
        setUploading(false);
        setProgress(0);
        setCurrentFile(null);
      }
    },
    [classId, category, addToast]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: uploading || !classId,
    multiple: false,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
  });

  if (!classId) {
    return (
      <p className="text-sm text-gray-500 text-center py-8">
        Select a class to upload files
      </p>
    );
  }

  return (
    <div>
      <CategorySelect value={category} onChange={setCategory} />

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
          transition-colors duration-150
          ${
            isDragActive
              ? 'border-cyan-400 bg-cyan-500/10'
              : uploading
              ? 'border-gray-700 bg-gray-800/50 cursor-not-allowed opacity-60'
              : 'border-gray-700 hover:border-gray-500 hover:bg-gray-800/30'
          }
        `}
      >
        <input {...getInputProps()} aria-label="File upload input" />

        <svg
          className={`w-10 h-10 mx-auto mb-3 ${isDragActive ? 'text-cyan-400' : 'text-gray-500'}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>

        {isDragActive ? (
          <p className="text-sm text-cyan-400 font-medium">Drop the file here</p>
        ) : (
          <>
            <p className="text-sm text-gray-300 font-medium">
              Drag & drop a file here
            </p>
            <p className="text-xs text-gray-500 mt-1">
              or click to browse (PDF, DOCX, TXT, MD, images)
            </p>
          </>
        )}
      </div>

      {uploading && currentFile && (
        <UploadProgress filename={currentFile} progress={progress} />
      )}
    </div>
  );
}
