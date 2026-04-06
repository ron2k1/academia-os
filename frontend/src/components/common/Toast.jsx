/**
 * Toast -- notification popup that auto-dismisses.
 */
import { useEffect } from 'react';
import useUiStore from '../../stores/uiStore';

const TYPE_STYLES = {
  info: 'border-cyan-500 bg-gray-800 text-gray-100',
  success: 'border-green-500 bg-gray-800 text-green-300',
  error: 'border-red-500 bg-gray-800 text-red-300',
  warning: 'border-yellow-500 bg-gray-800 text-yellow-300',
};

function ToastItem({ toast }) {
  const removeToast = useUiStore((s) => s.removeToast);

  useEffect(() => {
    if (toast.timeout > 0) {
      const timer = setTimeout(() => removeToast(toast.id), toast.timeout);
      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.timeout, removeToast]);

  const style = TYPE_STYLES[toast.type] || TYPE_STYLES.info;

  return (
    <div
      className={`border-l-4 px-4 py-3 rounded-r shadow-lg ${style} transition-all duration-300`}
      role="alert"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm">{toast.message}</p>
        <button
          onClick={() => removeToast(toast.id)}
          className="text-gray-400 hover:text-gray-200 text-lg leading-none"
          aria-label="Dismiss notification"
        >
          &times;
        </button>
      </div>
    </div>
  );
}

export default function ToastContainer() {
  const toasts = useUiStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
