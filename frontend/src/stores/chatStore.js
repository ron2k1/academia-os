/**
 * Zustand store for chat state.
 *
 * Manages per-class chat histories, active agents, and streaming state.
 * Thin store: state + simple setters. Business logic lives in hooks.
 */
import { create } from 'zustand';
import { uid } from '../utils/formatters';

/**
 * Create a default chat state for a class.
 * @returns {object} Fresh chat state.
 */
function defaultClassChat() {
  return {
    messages: [],
    activeAgent: 'tutor',
    isStreaming: false,
    streamBuffer: '',
  };
}

const useChatStore = create((set, get) => ({
  /**
   * Per-class chat state.
   * @type {Record<string, { messages: Array, activeAgent: string, isStreaming: boolean, streamBuffer: string }>}
   */
  chats: {},

  /**
   * Get or initialize chat state for a class.
   * @param {string} classId
   * @returns {object} Chat state for the class.
   */
  getClassChat: (classId) => {
    const state = get();
    return state.chats[classId] ?? defaultClassChat();
  },

  /** Set the active agent for a class. */
  setActiveAgent: (classId, agentId) =>
    set((state) => ({
      chats: {
        ...state.chats,
        [classId]: {
          ...(state.chats[classId] ?? defaultClassChat()),
          activeAgent: agentId,
        },
      },
    })),

  /** Add a user message to a class chat. */
  addUserMessage: (classId, content) =>
    set((state) => {
      const chat = state.chats[classId] ?? defaultClassChat();
      return {
        chats: {
          ...state.chats,
          [classId]: {
            ...chat,
            messages: [
              ...chat.messages,
              {
                id: uid(),
                role: 'user',
                content,
                timestamp: Date.now(),
                agent: chat.activeAgent,
              },
            ],
          },
        },
      };
    }),

  /** Start streaming -- set isStreaming true and clear buffer. */
  startStreaming: (classId) =>
    set((state) => ({
      chats: {
        ...state.chats,
        [classId]: {
          ...(state.chats[classId] ?? defaultClassChat()),
          isStreaming: true,
          streamBuffer: '',
        },
      },
    })),

  /** Append a chunk to the stream buffer. */
  appendChunk: (classId, content) =>
    set((state) => {
      const chat = state.chats[classId] ?? defaultClassChat();
      return {
        chats: {
          ...state.chats,
          [classId]: {
            ...chat,
            streamBuffer: chat.streamBuffer + content,
          },
        },
      };
    }),

  /** Finalize streaming: convert buffer to assistant message, clear stream state. */
  endStreaming: (classId, agent) =>
    set((state) => {
      const chat = state.chats[classId] ?? defaultClassChat();
      const finalContent = chat.streamBuffer;
      return {
        chats: {
          ...state.chats,
          [classId]: {
            ...chat,
            isStreaming: false,
            streamBuffer: '',
            messages: [
              ...chat.messages,
              {
                id: uid(),
                role: 'assistant',
                content: finalContent,
                timestamp: Date.now(),
                agent: agent || chat.activeAgent,
              },
            ],
          },
        },
      };
    }),

  /** Add an error message to the chat. */
  addErrorMessage: (classId, message) =>
    set((state) => {
      const chat = state.chats[classId] ?? defaultClassChat();
      return {
        chats: {
          ...state.chats,
          [classId]: {
            ...chat,
            isStreaming: false,
            streamBuffer: '',
            messages: [
              ...chat.messages,
              {
                id: uid(),
                role: 'error',
                content: message,
                timestamp: Date.now(),
              },
            ],
          },
        },
      };
    }),

  /** Clear all messages for a class. */
  clearChat: (classId) =>
    set((state) => ({
      chats: {
        ...state.chats,
        [classId]: defaultClassChat(),
      },
    })),
}));

export default useChatStore;
