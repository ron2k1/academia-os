/**
 * Application-wide constants.
 */

/** Agent definitions with display metadata. */
export const AGENTS = {
  tutor: {
    id: 'tutor',
    label: 'Tutor',
    color: 'indigo',
    bgClass: 'bg-indigo-600',
    textClass: 'text-indigo-400',
    borderClass: 'border-indigo-500',
    hoverClass: 'hover:bg-indigo-700',
    ringClass: 'ring-indigo-500',
    description: 'Explain concepts and walk through problems step by step',
  },
  question_creator: {
    id: 'question_creator',
    label: 'Question Creator',
    color: 'purple',
    bgClass: 'bg-purple-600',
    textClass: 'text-purple-400',
    borderClass: 'border-purple-500',
    hoverClass: 'hover:bg-purple-700',
    ringClass: 'ring-purple-500',
    description: 'Generate practice questions and quiz problems',
  },
  test_creator: {
    id: 'test_creator',
    label: 'Test Creator',
    color: 'blue',
    bgClass: 'bg-blue-600',
    textClass: 'text-blue-400',
    borderClass: 'border-blue-500',
    hoverClass: 'hover:bg-blue-700',
    ringClass: 'ring-blue-500',
    description: 'Create full practice exams and mock tests',
  },
  homework_finisher: {
    id: 'homework_finisher',
    label: 'Homework Finisher',
    color: 'orange',
    bgClass: 'bg-orange-600',
    textClass: 'text-orange-400',
    borderClass: 'border-orange-500',
    hoverClass: 'hover:bg-orange-700',
    ringClass: 'ring-orange-500',
    description: 'Help complete assignments and problem sets',
  },
  note_summarizer: {
    id: 'note_summarizer',
    label: 'Note Summarizer',
    color: 'teal',
    bgClass: 'bg-teal-600',
    textClass: 'text-teal-400',
    borderClass: 'border-teal-500',
    hoverClass: 'hover:bg-teal-700',
    ringClass: 'ring-teal-500',
    description: 'Summarize lectures and create study notes',
  },
};

/** Ordered list of agent IDs for UI rendering. */
export const AGENT_ORDER = [
  'tutor',
  'question_creator',
  'test_creator',
  'homework_finisher',
  'note_summarizer',
];

/** Valid file upload categories. */
export const UPLOAD_CATEGORIES = ['textbooks', 'practice', 'submissions', 'rubrics'];

/** WebSocket message types. */
export const WS_TYPES = {
  // Outgoing from server
  STREAM_CHUNK: 'stream_chunk',
  STREAM_END: 'stream_end',
  ERROR: 'error',
  FILE_READY: 'file_ready',
  HEALTH: 'health',
  PONG: 'pong',
  // Incoming to server
  MESSAGE: 'message',
  PING: 'ping',
};

/** WebSocket connection states. */
export const WS_STATE = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  RECONNECTING: 'reconnecting',
};

/** Backend API base URL (proxied in dev). */
export const API_BASE = '/api';

/** WebSocket URL. */
export const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

/** Ping interval in milliseconds. */
export const PING_INTERVAL_MS = 25000;

/** Reconnect delay in milliseconds. */
export const RECONNECT_DELAY_MS = 3000;

/** Maximum reconnect attempts. */
export const MAX_RECONNECT_ATTEMPTS = 10;
