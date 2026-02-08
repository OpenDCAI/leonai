import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../api";

interface MessageProps {
  message: ChatMessage;
}

function truncateText(value: string, maxLength = 1800): string {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength)}\n\n... [truncated]`;
}

export function Message({ message }: MessageProps) {
  if (message.role === "tool_call") {
    const args = typeof message.args === "string" ? message.args : JSON.stringify(message.args ?? {}, null, 2);
    return (
      <details className="tool-card">
        <summary>🛠 Tool Call: {message.name ?? "unknown"}</summary>
        <pre>{args}</pre>
      </details>
    );
  }

  if (message.role === "tool_result") {
    return (
      <details className="tool-card tool-result">
        <summary>📦 Tool Result</summary>
        <pre>{truncateText(message.content)}</pre>
      </details>
    );
  }

  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className={`message-bubble ${isUser ? "user" : "assistant"}`}>
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ""}</ReactMarkdown>
        )}
      </div>
    </div>
  );
}
