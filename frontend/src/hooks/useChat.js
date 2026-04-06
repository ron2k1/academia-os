/**
 * Hook for chat interactions within a class tab.
 *
 * Provides messages, streaming state, active agent, and send function.
 */
import { useCallback } from 'react';
import useChatStore from '../stores/chatStore';
import useClassStore from '../stores/classStore';
import { sendMessage } from '../services/ws';

export default function useChat() {
  const activeClassId = useClassStore((s) => s.activeClassId);
  const chats = useChatStore((s) => s.chats);
  const setActiveAgent = useChatStore((s) => s.setActiveAgent);
  const addUserMessage = useChatStore((s) => s.addUserMessage);
  const startStreaming = useChatStore((s) => s.startStreaming);
  const clearChat = useChatStore((s) => s.clearChat);

  const classChat = activeClassId
    ? chats[activeClassId] ?? { messages: [], activeAgent: 'tutor', isStreaming: false, streamBuffer: '' }
    : { messages: [], activeAgent: 'tutor', isStreaming: false, streamBuffer: '' };

  const send = useCallback(
    (content) => {
      if (!activeClassId || !content.trim()) return;
      addUserMessage(activeClassId, content.trim());
      startStreaming(activeClassId);
      sendMessage(activeClassId, classChat.activeAgent, content.trim());
    },
    [activeClassId, classChat.activeAgent, addUserMessage, startStreaming]
  );

  const switchAgent = useCallback(
    (agentId) => {
      if (activeClassId) {
        setActiveAgent(activeClassId, agentId);
      }
    },
    [activeClassId, setActiveAgent]
  );

  const clear = useCallback(() => {
    if (activeClassId) {
      clearChat(activeClassId);
    }
  }, [activeClassId, clearChat]);

  return {
    messages: classChat.messages,
    activeAgent: classChat.activeAgent,
    isStreaming: classChat.isStreaming,
    streamBuffer: classChat.streamBuffer,
    classId: activeClassId,
    send,
    switchAgent,
    clear,
  };
}
