/**
 * Hook for loading and accessing progress tracker data.
 */
import { useState, useEffect, useCallback } from 'react';
import { fetchProgress } from '../services/api';

export default function useProgress() {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchProgress();
      setProgress(data);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load progress');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { progress, loading, error, reload: load };
}
