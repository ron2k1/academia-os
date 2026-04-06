/**
 * WebSocket connection manager.
 *
 * Provides a singleton WebSocket client with auto-reconnect,
 * ping/pong keepalive, and typed message dispatching.
 */
import {
  WS_URL,
  WS_STATE,
  WS_TYPES,
  PING_INTERVAL_MS,
  RECONNECT_DELAY_MS,
  MAX_RECONNECT_ATTEMPTS,
} from '../utils/constants';

/** @type {WebSocket | null} */
let socket = null;

/** @type {ReturnType<typeof setInterval> | null} */
let pingTimer = null;

/** @type {ReturnType<typeof setTimeout> | null} */
let reconnectTimer = null;

/** @type {number} */
let reconnectAttempts = 0;

/** @type {Record<string, Array<function>>} */
const listeners = {};

/**
 * Register a listener for a specific message type.
 * @param {string} type - WS message type (from WS_TYPES).
 * @param {function} callback - Handler function receiving the message data.
 * @returns {function} Unsubscribe function.
 */
export function on(type, callback) {
  if (!listeners[type]) listeners[type] = [];
  listeners[type].push(callback);
  return () => {
    listeners[type] = listeners[type].filter((fn) => fn !== callback);
  };
}

/**
 * Dispatch a message to all registered listeners for its type.
 * @param {object} data - Parsed message object with a `type` field.
 */
function dispatch(data) {
  const handlers = listeners[data.type];
  if (handlers) {
    handlers.forEach((fn) => fn(data));
  }
}

/**
 * Notify state-change listeners.
 * @param {string} state - New WS_STATE value.
 */
function notifyState(state) {
  const handlers = listeners['_state'];
  if (handlers) {
    handlers.forEach((fn) => fn(state));
  }
}

/**
 * Start the ping keepalive timer.
 */
function startPing() {
  stopPing();
  pingTimer = setInterval(() => {
    send({ type: WS_TYPES.PING });
  }, PING_INTERVAL_MS);
}

/**
 * Stop the ping keepalive timer.
 */
function stopPing() {
  if (pingTimer) {
    clearInterval(pingTimer);
    pingTimer = null;
  }
}

/**
 * Connect to the WebSocket server.
 */
export function connect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  notifyState(WS_STATE.CONNECTING);

  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    reconnectAttempts = 0;
    notifyState(WS_STATE.CONNECTED);
    startPing();
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      dispatch(data);
    } catch {
      // Ignore unparseable messages
    }
  };

  socket.onclose = () => {
    stopPing();
    notifyState(WS_STATE.DISCONNECTED);
    scheduleReconnect();
  };

  socket.onerror = () => {
    // onclose will fire after onerror
  };
}

/**
 * Schedule a reconnection attempt.
 */
function scheduleReconnect() {
  if (reconnectTimer) return;
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;

  reconnectAttempts++;
  notifyState(WS_STATE.RECONNECTING);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, RECONNECT_DELAY_MS);
}

/**
 * Disconnect from the WebSocket server.
 */
export function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  reconnectAttempts = MAX_RECONNECT_ATTEMPTS; // prevent reconnect
  stopPing();
  if (socket) {
    socket.close();
    socket = null;
  }
  notifyState(WS_STATE.DISCONNECTED);
}

/**
 * Send a JSON message through the WebSocket.
 * @param {object} data - Message payload.
 * @returns {boolean} Whether the message was sent.
 */
export function send(data) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(data));
    return true;
  }
  return false;
}

/**
 * Send a chat message to an agent.
 * @param {string} classId - Target class.
 * @param {string} agent - Agent ID.
 * @param {string} content - Message content.
 * @returns {boolean} Whether the message was sent.
 */
export function sendMessage(classId, agent, content) {
  return send({
    type: WS_TYPES.MESSAGE,
    class_id: classId,
    agent,
    content,
  });
}

/**
 * Check if the WebSocket is currently connected.
 * @returns {boolean} Connection status.
 */
export function isConnected() {
  return socket !== null && socket.readyState === WebSocket.OPEN;
}
