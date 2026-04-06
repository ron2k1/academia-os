/**
 * Zustand store for UI state.
 *
 * Manages side panel visibility, toasts, and global UI flags.
 * Thin store: state + simple setters.
 */
import { create } from 'zustand';
import { uid } from '../utils/formatters';
import { WS_STATE } from '../utils/constants';

const useUiStore = create((set) => ({
  /** Whether the side panel (file browser / upload) is open. */
  sidePanelOpen: false,

  /** Active side panel tab: 'files' | 'upload' | 'progress'. */
  sidePanelTab: 'files',

  /** WebSocket connection state. */
  wsState: WS_STATE.DISCONNECTED,

  /** Health status from the backend. */
  health: null,

  /** @type {Array<{ id: string, message: string, type: string, timeout?: number }>} */
  toasts: [],

  /** Toggle the side panel open/closed. */
  toggleSidePanel: () =>
    set((state) => ({ sidePanelOpen: !state.sidePanelOpen })),

  /** Set side panel open state. */
  setSidePanelOpen: (open) => set({ sidePanelOpen: open }),

  /** Set the active side panel tab. */
  setSidePanelTab: (tab) => set({ sidePanelTab: tab, sidePanelOpen: true }),

  /** Set WebSocket connection state. */
  setWsState: (wsState) => set({ wsState }),

  /** Set backend health status. */
  setHealth: (health) => set({ health }),

  /** Add a toast notification. Returns the toast ID. */
  addToast: (message, type = 'info', timeout = 4000) => {
    const id = uid();
    set((state) => ({
      toasts: [...state.toasts, { id, message, type, timeout }],
    }));
    return id;
  },

  /** Remove a toast by ID. */
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));

export default useUiStore;
