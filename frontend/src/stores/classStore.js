/**
 * Zustand store for class/tab state.
 *
 * Thin store: state + simple setters. Business logic lives in hooks.
 */
import { create } from 'zustand';

const useClassStore = create((set) => ({
  /** @type {{ semester: object, classes: Array<object> } | null} */
  config: null,

  /** @type {string | null} Currently active class tab ID. */
  activeClassId: null,

  /** @type {boolean} Whether classes are being loaded. */
  loading: false,

  /** @type {string | null} Error message from last load attempt. */
  error: null,

  /** Replace the full classes config. */
  setConfig: (config) =>
    set((state) => ({
      config,
      // Auto-select first active class if none selected
      activeClassId:
        state.activeClassId ??
        config?.classes?.find((c) => c.active)?.id ??
        null,
    })),

  /** Set the active class tab. */
  setActiveClassId: (classId) => set({ activeClassId: classId }),

  /** Set loading state. */
  setLoading: (loading) => set({ loading }),

  /** Set error state. */
  setError: (error) => set({ error }),
}));

export default useClassStore;
