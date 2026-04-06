/**
 * Hook for loading and accessing class configuration.
 *
 * Fetches classes from the API on first use and stores in classStore.
 */
import { useEffect } from 'react';
import useClassStore from '../stores/classStore';
import { fetchClasses } from '../services/api';

export default function useClassConfig() {
  const config = useClassStore((s) => s.config);
  const loading = useClassStore((s) => s.loading);
  const error = useClassStore((s) => s.error);
  const activeClassId = useClassStore((s) => s.activeClassId);

  useEffect(() => {
    // Only fetch once
    if (config || loading) return;

    const load = async () => {
      useClassStore.getState().setLoading(true);
      try {
        const data = await fetchClasses();
        useClassStore.getState().setConfig(data);
        useClassStore.getState().setError(null);
      } catch (err) {
        useClassStore.getState().setError(
          err.message || 'Failed to load classes'
        );
      } finally {
        useClassStore.getState().setLoading(false);
      }
    };

    load();
  }, [config, loading]);

  const classes = config?.classes ?? [];
  const activeClasses = classes.filter((c) => c.active);
  const activeClass = classes.find((c) => c.id === activeClassId) ?? null;
  const semester = config?.semester ?? null;

  return {
    config,
    classes,
    activeClasses,
    activeClass,
    activeClassId,
    semester,
    loading,
    error,
  };
}
