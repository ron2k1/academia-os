/**
 * Hook for managing WebSocket connection lifecycle and message routing.
 *
 * Connects on mount, disconnects on unmount. Routes incoming messages
 * to the appropriate Zustand stores.
 */
import { useEffect, useRef } from 'react';
import * as ws from '../services/ws';
import { WS_TYPES } from '../utils/constants';
import useChatStore from '../stores/chatStore';
import useUiStore from '../stores/uiStore';

export default function useWebSocket() {
  const mounted = useRef(false);

  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;

    // State listener
    const offState = ws.on('_state', (state) => {
      useUiStore.getState().setWsState(state);
    });

    // Health status
    const offHealth = ws.on(WS_TYPES.HEALTH, (data) => {
      useUiStore.getState().setHealth(data.status);
    });

    // Stream chunk
    const offChunk = ws.on(WS_TYPES.STREAM_CHUNK, (data) => {
      const store = useChatStore.getState();
      const chat = store.chats[data.class_id];
      if (!chat?.isStreaming) {
        store.startStreaming(data.class_id);
      }
      store.appendChunk(data.class_id, data.content);
    });

    // Stream end
    const offEnd = ws.on(WS_TYPES.STREAM_END, (data) => {
      useChatStore.getState().endStreaming(data.class_id, data.agent);
    });

    // Error
    const offError = ws.on(WS_TYPES.ERROR, (data) => {
      const classId = data.class_id;
      if (classId) {
        useChatStore.getState().addErrorMessage(classId, data.message);
      } else {
        useUiStore.getState().addToast(data.message, 'error');
      }
    });

    // File ready
    const offFile = ws.on(WS_TYPES.FILE_READY, (data) => {
      useUiStore.getState().addToast(
        `File ready: ${data.filename}`,
        'success',
        6000
      );
    });

    // Connect
    ws.connect();

    return () => {
      offState();
      offHealth();
      offChunk();
      offEnd();
      offError();
      offFile();
      ws.disconnect();
      mounted.current = false;
    };
  }, []);
}
