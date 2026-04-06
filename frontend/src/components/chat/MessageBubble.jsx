/**
 * MessageBubble -- renders a single chat message (user, assistant, or error).
 *
 * Supports markdown rendering with LaTeX and syntax highlighting.
 */
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { AGENTS } from '../../utils/constants';
import { formatTime } from '../../utils/formatters';

function CodeBlock({ className, children, ...props }) {
  const match = /language-(\w+)/.exec(className || '');
  const code = String(children).replace(/\n$/, '');

  if (match) {
    return (
      <SyntaxHighlighter
        style={oneDark}
        language={match[1]}
        PreTag="div"
        className="rounded-lg text-sm my-2"
      >
        {code}
      </SyntaxHighlighter>
    );
  }

  return (
    <code className="bg-gray-800 px-1.5 py-0.5 rounded text-sm text-cyan-300" {...props}>
      {children}
    </code>
  );
}

function MarkdownContent({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        code: CodeBlock,
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
        li: ({ children }) => <li className="mb-0.5">{children}</li>,
        h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-3">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-bold mb-1.5 mt-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-bold mb-1 mt-2">{children}</h3>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-gray-600 pl-3 my-2 text-gray-400 italic">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="min-w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-gray-700 px-2 py-1 bg-gray-800 text-left font-medium">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-gray-700 px-2 py-1">{children}</td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default function MessageBubble({ message }) {
  const { role, content, timestamp, agent } = message;
  const agentMeta = agent ? AGENTS[agent] : null;

  if (role === 'error') {
    return (
      <div className="flex justify-center my-2" role="alert">
        <div className="bg-red-900/30 border border-red-800 rounded-lg px-4 py-2 max-w-lg">
          <p className="text-sm text-red-400">{content}</p>
        </div>
      </div>
    );
  }

  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} my-2`}>
      <div
        className={`
          max-w-[80%] rounded-lg px-4 py-2.5
          ${
            isUser
              ? 'bg-gray-700 text-gray-100'
              : 'bg-gray-800 border border-gray-700 text-gray-200'
          }
        `}
      >
        {/* Agent badge for assistant messages */}
        {!isUser && agentMeta && (
          <div className="flex items-center gap-1.5 mb-1.5">
            <span
              className={`inline-block h-2 w-2 rounded-full ${agentMeta.bgClass}`}
            />
            <span className={`text-xs font-medium ${agentMeta.textClass}`}>
              {agentMeta.label}
            </span>
          </div>
        )}

        {/* Message content */}
        <div className="text-sm leading-relaxed">
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <MarkdownContent content={content} />
          )}
        </div>

        {/* Timestamp */}
        {timestamp && (
          <div className={`text-[10px] mt-1 ${isUser ? 'text-gray-400' : 'text-gray-500'}`}>
            {formatTime(timestamp)}
          </div>
        )}
      </div>
    </div>
  );
}
