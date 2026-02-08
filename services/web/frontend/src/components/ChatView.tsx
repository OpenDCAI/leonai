import { useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage } from "../api";
import { startRun } from "../api";
import { Message } from "./Message";

interface ChatViewProps {
  threadId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  setMessages: (updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
  setIsStreaming: (value: boolean) => void;
  onRunFinished?: () => void | Promise<void>;
}

function generateId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ChatView({
  threadId,
  messages,
  isStreaming,
  setMessages,
  setIsStreaming,
  onRunFinished,
}: ChatViewProps) {
  const [input, setInput] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);

  const canSend = useMemo(() => Boolean(threadId) && !isStreaming && input.trim().length > 0, [threadId, isStreaming, input]);

  useEffect(() => {
    const node = scrollerRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [messages]);

  async function sendMessage() {
    if (!threadId || isStreaming) {
      return;
    }

    const text = input.trim();
    if (!text) {
      return;
    }

    setInput("");

    const userMessage: ChatMessage = {
      id: generateId("user"),
      role: "user",
      content: text,
    };

    const assistantId = generateId("assistant");

    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: assistantId,
        role: "assistant",
        content: "",
      },
    ]);

    setIsStreaming(true);

    try {
      await startRun(threadId, text, (event) => {
        if (event.type === "text") {
          const payload = event.data as { content?: string } | string | undefined;
          const chunk = typeof payload === "string" ? payload : (payload?.content ?? "");
          setMessages((prev) =>
            prev.map((msg) => (msg.id === assistantId ? { ...msg, content: `${msg.content}${chunk}` } : msg)),
          );
          return;
        }

        if (event.type === "tool_call") {
          const payload = (event.data ?? {}) as { name?: string; args?: unknown; id?: string };
          setMessages((prev) => [
            ...prev,
            {
              id: payload.id ?? generateId("tool-call"),
              role: "tool_call",
              content: "",
              name: payload.name ?? "tool",
              args: payload.args ?? payload,
            },
          ]);
          return;
        }

        if (event.type === "tool_result") {
          const payload = (event.data ?? {}) as { content?: string; tool_call_id?: string };
          setMessages((prev) => [
            ...prev,
            {
              id: generateId("tool-result"),
              role: "tool_result",
              content: typeof payload.content === "string" ? payload.content : JSON.stringify(payload, null, 2),
              toolCallId: payload.tool_call_id,
            },
          ]);
          return;
        }

        if (event.type === "error") {
          const errText = typeof event.data === "string" ? event.data : JSON.stringify(event.data ?? "Unknown error");
          setMessages((prev) => [
            ...prev,
            {
              id: generateId("error"),
              role: "assistant",
              content: `Error: ${errText}`,
            },
          ]);
          return;
        }

        if (event.type === "done") {
          setIsStreaming(false);
        }
      });
    } catch (error) {
      const errorText = error instanceof Error ? error.message : String(error);
      setMessages((prev) => [
        ...prev,
        {
          id: generateId("run-error"),
          role: "assistant",
          content: `Run failed: ${errorText}`,
        },
      ]);
    } finally {
      setIsStreaming(false);
      if (onRunFinished) {
        await onRunFinished();
      }
    }
  }

  return (
    <section className="chat-view">
      <div className="messages" ref={scrollerRef}>
        {messages.map((message) => (
          <div key={message.id} className="message-enter">
            <Message message={message} />
          </div>
        ))}

        {isStreaming && (
          <div className="typing-indicator" aria-label="Assistant is thinking">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>

      <div className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={threadId ? "Type your message..." : "Create or select a thread first"}
          disabled={!threadId || isStreaming}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void sendMessage();
            }
          }}
          rows={3}
        />
        <button onClick={() => void sendMessage()} disabled={!canSend}>
          Send
        </button>
      </div>
    </section>
  );
}
