import { useCallback, useEffect, useState } from "react";
import "./App.css";
import ChatArea from "./components/ChatArea";
import ComputerPanel from "./components/ComputerPanel";
import Header from "./components/Header";
import InputBox from "./components/InputBox";
import SandboxSessionsModal from "./components/SandboxSessionsModal";
import SearchModal from "./components/SearchModal";
import Sidebar from "./components/Sidebar";
import TaskProgress from "./components/TaskProgress";
import {
  createThread,
  deleteThread,
  getThread,
  listSandboxTypes,
  listThreads,
  mapBackendMessages,
  pauseThreadSandbox,
  resumeThreadSandbox,
  startRun,
  type ChatMessage,
  type SandboxInfo,
  type SandboxType,
  type ThreadSummary,
} from "./api";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [computerOpen, setComputerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);

  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [sandboxTypes, setSandboxTypes] = useState<SandboxType[]>([{ name: "local", available: true }]);
  const [selectedSandbox, setSelectedSandbox] = useState("local");
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeSandbox, setActiveSandbox] = useState<SandboxInfo | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const refreshThreads = useCallback(async () => {
    const rows = await listThreads();
    setThreads(rows);
    if (!activeThreadId && rows.length > 0) {
      setActiveThreadId(rows[0].thread_id);
    }
  }, [activeThreadId]);

  const loadThread = useCallback(async (threadId: string) => {
    const thread = await getThread(threadId);
    setMessages(mapBackendMessages(thread.messages));
    setActiveSandbox(thread.sandbox);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const [types] = await Promise.all([listSandboxTypes(), refreshThreads()]);
        setSandboxTypes(types);
        const preferred = types.find((t) => t.available)?.name ?? "local";
        setSelectedSandbox(preferred);
      } catch {
        // ignore bootstrap errors in UI; user can retry by action
      }
    })();
  }, [refreshThreads]);

  useEffect(() => {
    if (!activeThreadId) {
      setMessages([]);
      setActiveSandbox(null);
      return;
    }
    void loadThread(activeThreadId);
  }, [activeThreadId, loadThread]);

  const handleCreateThread = useCallback(async () => {
    const thread = await createThread(selectedSandbox);
    setThreads((prev) => [thread, ...prev]);
    setActiveThreadId(thread.thread_id);
    setMessages([]);
  }, [selectedSandbox]);

  const handleDeleteThread = useCallback(
    async (threadId: string) => {
      await deleteThread(threadId);
      const remaining = threads.filter((t) => t.thread_id !== threadId);
      setThreads(remaining);
      if (activeThreadId === threadId) {
        setActiveThreadId(remaining[0]?.thread_id ?? null);
      }
    },
    [activeThreadId, threads],
  );

  const handleSendMessage = useCallback(
    async (message: string) => {
      let threadId = activeThreadId;
      if (!threadId) {
        const created = await createThread(selectedSandbox);
        setThreads((prev) => [created, ...prev]);
        setActiveThreadId(created.thread_id);
        threadId = created.thread_id;
      }
      if (!threadId) return;

      const user: ChatMessage = { id: makeId("user"), role: "user", content: message };
      const assistantId = makeId("assistant");
      setMessages((prev) => [...prev, user, { id: assistantId, role: "assistant", content: "" }]);
      setIsStreaming(true);

      try {
        await startRun(threadId, message, (event) => {
          if (event.type === "text") {
            const payload = event.data as { content?: string } | string | undefined;
            const chunk = typeof payload === "string" ? payload : payload?.content ?? "";
            setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content: `${m.content}${chunk}` } : m)));
            return;
          }
          if (event.type === "tool_call") {
            const payload = (event.data ?? {}) as { id?: string; name?: string; args?: unknown };
            setMessages((prev) => [
              ...prev,
              {
                id: payload.id ?? makeId("tool-call"),
                role: "tool_call",
                content: "",
                name: payload.name ?? "tool",
                args: payload.args ?? {},
              },
            ]);
            return;
          }
          if (event.type === "tool_result") {
            const payload = (event.data ?? {}) as { content?: string; tool_call_id?: string };
            setMessages((prev) => [
              ...prev,
              {
                id: makeId("tool-result"),
                role: "tool_result",
                content: typeof payload.content === "string" ? payload.content : JSON.stringify(payload, null, 2),
                toolCallId: payload.tool_call_id ?? null,
              },
            ]);
            return;
          }
          if (event.type === "error") {
            const text = typeof event.data === "string" ? event.data : JSON.stringify(event.data ?? "Unknown error");
            setMessages((prev) => [...prev, { id: makeId("run-error"), role: "assistant", content: `Error: ${text}` }]);
          }
        });
      } finally {
        setIsStreaming(false);
        await loadThread(threadId);
        await refreshThreads();
      }
    },
    [activeThreadId, loadThread, refreshThreads, selectedSandbox],
  );

  const handlePauseSandbox = useCallback(async () => {
    if (!activeThreadId) return;
    await pauseThreadSandbox(activeThreadId);
    await loadThread(activeThreadId);
  }, [activeThreadId, loadThread]);

  const handleResumeSandbox = useCallback(async () => {
    if (!activeThreadId) return;
    await resumeThreadSandbox(activeThreadId);
    await loadThread(activeThreadId);
  }, [activeThreadId, loadThread]);

  return (
    <div className="h-screen w-screen bg-[#1a1a1a] flex overflow-hidden">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        sandboxTypes={sandboxTypes}
        selectedSandbox={selectedSandbox}
        collapsed={sidebarCollapsed}
        onSelectThread={setActiveThreadId}
        onCreateThread={() => void handleCreateThread()}
        onDeleteThread={(id) => void handleDeleteThread(id)}
        onSelectSandboxType={setSelectedSandbox}
        onSearchClick={() => setSearchOpen(true)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Header
          activeThreadId={activeThreadId}
          sandboxInfo={activeSandbox}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
          onToggleComputer={() => setComputerOpen((v) => !v)}
          onOpenSandboxSessions={() => setSessionsOpen(true)}
          onPauseSandbox={() => void handlePauseSandbox()}
          onResumeSandbox={() => void handleResumeSandbox()}
          computerOpen={computerOpen}
        />

        <div className="flex-1 flex min-h-0">
          <div className={`flex flex-col transition-all duration-300 ${computerOpen ? "w-1/2" : "flex-1"}`}>
            <ChatArea messages={messages} isStreaming={isStreaming} />
            <TaskProgress messages={messages} isStreaming={isStreaming} onOpenComputer={() => setComputerOpen(true)} />
            <InputBox
              disabled={isStreaming}
              placeholder={activeThreadId ? "发送消息给 Leon" : "先创建一个会话"}
              onSendMessage={handleSendMessage}
            />
          </div>

          {computerOpen && (
            <ComputerPanel
              isOpen={computerOpen}
              onClose={() => setComputerOpen(false)}
              threadId={activeThreadId}
              sandboxType={activeSandbox?.type ?? null}
            />
          )}
        </div>
      </div>

      <SearchModal
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        threads={threads}
        onSelectThread={(threadId) => setActiveThreadId(threadId)}
      />

      <SandboxSessionsModal isOpen={sessionsOpen} onClose={() => setSessionsOpen(false)} />
    </div>
  );
}
