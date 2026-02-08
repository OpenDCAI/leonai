import { useEffect, useMemo, useState } from "react";
import {
  createThread, deleteThread, getThread, listThreads, listSandboxTypes,
  pauseSession, resumeSession,
  type ChatMessage, type ThreadSummary, type SandboxType, type SandboxInfo,
} from "./api";
import { ChatView } from "./components/ChatView";
import { SandboxPanel } from "./components/SandboxPanel";
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
  const [sandboxTypes, setSandboxTypes] = useState<SandboxType[]>([]);
  const [activeSandbox, setActiveSandbox] = useState<SandboxInfo | null>(null);
  const [showSandboxPanel, setShowSandboxPanel] = useState(false);

  const setMessages = (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
    setMessagesState((prev) => updater(prev));
  };

  // Load sandbox types on mount
  useEffect(() => {
    void listSandboxTypes().then(setSandboxTypes).catch(() => {});
  }, []);

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

  // Load messages + sandbox info when active thread changes
  useEffect(() => {
    if (!activeThreadId) {
      setMessagesState([]);
      setActiveSandbox(null);
      return;
    }

    let cancelled = false;

    void (async () => {
      try {
        const thread = await getThread(activeThreadId);
        if (cancelled) return;
        setMessagesState(mapBackendMessages(thread.messages));
        // thread.sandbox comes from enriched GET /api/threads/{id}
        const sbx = (thread as unknown as { sandbox?: SandboxInfo }).sandbox;
        setActiveSandbox(sbx ?? null);
      } catch (error) {
        if (!cancelled) {
          setMessagesState([{
            id: "thread-load-error",
            role: "assistant",
            content: error instanceof Error ? `Failed to load thread: ${error.message}` : "Failed to load thread",
          }]);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [activeThreadId]);

// PLACEHOLDER_HANDLERS

  async function handleCreateThread(sandboxType: string) {
    const thread = await createThread(sandboxType);
    setThreads((prev) => [thread, ...prev]);
    setActiveThreadId(thread.thread_id);
    setMessagesState([]);
  }

  async function handleDeleteThread(threadId: string) {
    await deleteThread(threadId);
    setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
    if (threadId === activeThreadId) {
      const remaining = threads.filter((t) => t.thread_id !== threadId);
      setActiveThreadId(remaining[0]?.thread_id ?? null);
      setMessagesState([]);
    }
  }

  async function handlePauseSandbox() {
    if (!activeSandbox?.session_id) return;
    await pauseSession(activeSandbox.session_id);
    setActiveSandbox((prev) => prev ? { ...prev, status: "paused" } : null);
  }

  async function handleResumeSandbox() {
    if (!activeSandbox?.session_id) return;
    await resumeSession(activeSandbox.session_id);
    setActiveSandbox((prev) => prev ? { ...prev, status: "running" } : null);
  }

  const title = useMemo(() => {
    if (!activeThreadId) return "No active thread";
    const short = activeThreadId.slice(0, 12);
    return activeSandbox?.type && activeSandbox.type !== "local"
      ? `Thread: ${short}... [${activeSandbox.type}]`
      : `Thread: ${short}...`;
  }, [activeThreadId, activeSandbox]);

  return (
    <div className="app-shell">
      <ThreadList
        threads={threads}
        activeThreadId={activeThreadId}
        sandboxTypes={sandboxTypes}
        onSelect={setActiveThreadId}
        onCreate={handleCreateThread}
        onDelete={(id) => void handleDeleteThread(id)}
        onShowSandboxPanel={() => setShowSandboxPanel(true)}
      />

      <main className="chat-area">
        <header className="chat-header">
          <h1>{title}</h1>
          {activeSandbox && activeSandbox.type !== "local" && activeSandbox.session_id && (
            <div className="sandbox-controls">
              <span className={`sandbox-status ${activeSandbox.status ?? "unknown"}`}>
                {activeSandbox.status ?? "unknown"}
              </span>
              {activeSandbox.status === "running" && (
                <button className="sandbox-btn" onClick={() => void handlePauseSandbox()}>Pause</button>
              )}
              {activeSandbox.status === "paused" && (
                <button className="sandbox-btn" onClick={() => void handleResumeSandbox()}>Resume</button>
              )}
            </div>
          )}
        </header>

        <ChatView
          threadId={activeThreadId}
          messages={messages}
          isStreaming={isStreaming}
          setMessages={setMessages}
          setIsStreaming={setIsStreaming}
        />
      </main>

      {showSandboxPanel && (
        <SandboxPanel onClose={() => setShowSandboxPanel(false)} />
      )}
    </div>
  );
}
