/**
 * ChatWindow -- main chat view composing AgentSelector, message list, and input.
 */
import { useEffect, useRef } from 'react';
import useChat from '../../hooks/useChat';
import { AGENTS } from '../../utils/constants';
import AgentSelector from './AgentSelector';
import ChatInput from './ChatInput';
import MessageBubble from './MessageBubble';

function StreamingBubble({ content, agent }) {
  const agentMeta = AGENTS[agent];
  return (
    <div className="flex justify-start my-2">
      <div className="max-w-[80%] rounded-lg px-4 py-2.5 bg-gray-800 border border-gray-700 text-gray-200">
        {agentMeta && (
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className={`inline-block h-2 w-2 rounded-full ${agentMeta.bgClass}`} />
            <span className={`text-xs font-medium ${agentMeta.textClass}`}>
              {agentMeta.label}
            </span>
          </div>
        )}
        <div className="text-sm leading-relaxed">
          <span className="whitespace-pre-wrap">{content}</span>
          <span className="inline-block w-2 h-4 bg-cyan-400 animate-pulse ml-0.5 align-text-bottom" />
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
      <div className="h-16 w-16 rounded-full bg-gray-800 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
        </svg>
      </div>
      <h3 className="text-gray-300 font-medium mb-1">Start a Conversation</h3>
      <p className="text-gray-500 text-sm max-w-xs">
        Select an agent above and type a message to get started. Each agent specializes in different tasks.
      </p>
    </div>
  );
}

export default function ChatWindow() {
  const { messages, activeAgent, isStreaming, streamBuffer, classId, send, switchAgent, clear } = useChat();
  const scrollRef = useRef(null);

  // Auto-scroll to bottom on new messages or streaming
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamBuffer]);

  if (!classId) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
        Select a class to start chatting
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Agent selector */}
      <AgentSelector
        activeAgent={activeAgent}
        onSelect={switchAgent}
        disabled={isStreaming}
      />

      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2">
        {messages.length === 0 && !isStreaming ? (
          <EmptyState />
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isStreaming && streamBuffer && (
              <StreamingBubble content={streamBuffer} agent={activeAgent} />
            )}
          </>
        )}
      </div>

      {/* Clear chat button */}
      {messages.length > 0 && (
        <div className="flex justify-center py-1">
          <button
            onClick={clear}
            disabled={isStreaming}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-50"
            aria-label="Clear chat history"
          >
            Clear chat
          </button>
        </div>
      )}

      {/* Input */}
      <ChatInput onSend={send} disabled={isStreaming} />
    </div>
  );
}
