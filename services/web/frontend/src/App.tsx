import { useEffect, useMemo, useState } from "react";
import { createThread, deleteThread, getThread, listThreads, type ChatMessage, type ThreadSummary } from "./api";
import { ChatView } from "./components/ChatView";
import { ThreadList } from "./components/ThreadList";

function mapBackendMessages(payload: unknown): ChatMessage[] {
  if (!Array.isArray(payload)) {
    return [];
  }

  return payload.flatMap((item, index): ChatMessage[] => {
    if (!item || typeof item !== "object") {
      return [];
    }

    const msg = item as Record<string, unknown>;
    const msgType = typeof msg.type === "string" ? msg.type : "";
    const content = typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content ?? "", null, 2);

    if (msgType === "HumanMessage") {
      return [{ id: `hist-user-${index}`, role: "user", content }];
    }

    if (msgType === "AIMessage") {
      return [{ id: `hist-assistant-${index}`, role: "assistant", content }];
    }

    return [];
  });
}

export default function App() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessagesState] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const setMessages = (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
    setMessagesState((prev) => updater(prev));
  };

  async function loadThreads() {
    const list = await listThreads();
    setThreads(list);
    if (!activeThreadId && list.length > 0) {
      setActiveThreadId(list[0].thread_id);
    }
  }

  useEffect(() => {
    void loadThreads();
  }, []);

  useEffect(() => {
    if (!activeThreadId) {
      setMessagesState([]);
      return;
    }

    let cancelled = false;

    void (async () => {
      try {
        const thread = await getThread(activeThreadId);
        if (cancelled) {
          return;
        }
        setMessagesState(mapBackendMessages(thread.messages));
      } catch (error) {
        if (!cancelled) {
          setMessagesState([
            {
              id: "thread-load-error",
              role: "assistant",
              content: error instanceof Error ? `Failed to load thread: ${error.message}` : "Failed to load thread",
            },
          ]);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeThreadId]);

  async function handleCreateThread() {
    const thread = await createThread();
    setThreads((prev) => [thread, ...prev]);
    setActiveThreadId(thread.thread_id);
    setMessagesState([]);
  }

  async function handleDeleteThread(threadId: string) {
    await deleteThread(threadId);

    setThreads((prev) => prev.filter((thread) => thread.thread_id !== threadId));

    if (threadId === activeThreadId) {
      const remaining = threads.filter((thread) => thread.thread_id !== threadId);
      setActiveThreadId(remaining[0]?.thread_id ?? null);
      setMessagesState([]);
    }
  }

  const title = useMemo(() => {
    if (!activeThreadId) {
      return "No active thread";
    }
    return `Thread: ${activeThreadId}`;
  }, [activeThreadId]);

  return (
    <div className="app-shell">
      <ThreadList
        threads={threads}
        activeThreadId={activeThreadId}
        onSelect={setActiveThreadId}
        onCreate={() => void handleCreateThread()}
        onDelete={(id) => void handleDeleteThread(id)}
      />

      <main className="chat-area">
        <header className="chat-header">
          <h1>{title}</h1>
        </header>

        <ChatView
          threadId={activeThreadId}
          messages={messages}
          isStreaming={isStreaming}
          setMessages={setMessages}
          setIsStreaming={setIsStreaming}
        />
      </main>
    </div>
  );
}
