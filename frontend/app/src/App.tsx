import { useCallback, useEffect, useState } from "react";
import "./App.css";
import ChatArea from "./components/ChatArea";
import ComputerPanel from "./components/ComputerPanel";
import Header from "./components/Header";
import InputBox from "./components/InputBox";
import NewThreadModal from "./components/NewThreadModal";
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
  mapBackendEntries,
  pauseThreadSandbox,
  resumeThreadSandbox,
  startRun,
  type AssistantTurn,
  type ChatEntry,
  type SandboxInfo,
  type SandboxType,
  type StreamStatus,
  type ThreadSummary,
  type ToolStep,
} from "./api";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [computerOpen, setComputerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);
  const [newThreadOpen, setNewThreadOpen] = useState(false);

  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [sandboxTypes, setSandboxTypes] = useState<SandboxType[]>([{ name: "local", available: true }]);
  const [selectedSandbox, setSelectedSandbox] = useState("local");
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeSandbox, setActiveSandbox] = useState<SandboxInfo | null>(null);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const [sandboxActionError, setSandboxActionError] = useState<string | null>(null);

  // Track the current streaming assistant turn id for appending
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);

  const refreshThreads = useCallback(async () => {
    const rows = await listThreads();
    const enriched = await Promise.all(
      rows.map(async (t) => {
        try {
          const detail = await getThread(t.thread_id);
          const msgs = Array.isArray(detail.messages) ? detail.messages : [];
          const firstUser = msgs.find((m: { type?: string }) => m.type === "HumanMessage");
          const preview = firstUser ? String((firstUser as { content?: string }).content ?? "").slice(0, 40) : "";
          return { ...t, preview };
        } catch {
          return t;
        }
      }),
    );
    setThreads(enriched);
    if (!activeThreadId && enriched.length > 0) {
      setActiveThreadId(enriched[0].thread_id);
    }
  }, [activeThreadId]);

  const loadThread = useCallback(async (threadId: string) => {
    const thread = await getThread(threadId);
    setEntries(mapBackendEntries(thread.messages));
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
      setEntries([]);
      setActiveSandbox(null);
      return;
    }
    void loadThread(activeThreadId);
  }, [activeThreadId, loadThread]);

  const handleCreateThread = useCallback(async (sandbox?: string) => {
    const type = sandbox ?? selectedSandbox;
    const thread = await createThread(type);
    setThreads((prev) => [thread, ...prev]);
    setActiveThreadId(thread.thread_id);
    setSelectedSandbox(type);
    setEntries([]);
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

      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      const turnId = makeId("turn");
      const assistantTurn: AssistantTurn = {
        id: turnId,
        role: "assistant",
        content: "",
        toolSteps: [],
        timestamp: Date.now(),
      };
      setEntries((prev) => [...prev, userEntry, assistantTurn]);
      setStreamTurnId(turnId);
      setIsStreaming(true);
      setRuntimeStatus(null);

      try {
        await startRun(threadId, message, (event) => {
          if (event.type === "text") {
            const payload = event.data as { content?: string } | string | undefined;
            const chunk = typeof payload === "string" ? payload : payload?.content ?? "";
            setEntries((prev) =>
              prev.map((e) =>
                e.id === turnId && e.role === "assistant"
                  ? { ...e, content: `${e.content}${chunk}` }
                  : e,
              ),
            );
            return;
          }

          if (event.type === "tool_call") {
            const payload = (event.data ?? {}) as { id?: string; name?: string; args?: unknown };
            const step: ToolStep = {
              id: payload.id ?? makeId("tc"),
              name: payload.name ?? "tool",
              args: payload.args ?? {},
              status: "calling",
              timestamp: Date.now(),
            };
            setEntries((prev) =>
              prev.map((e) =>
                e.id === turnId && e.role === "assistant"
                  ? { ...e, toolSteps: [...(e as AssistantTurn).toolSteps, step] }
                  : e,
              ),
            );
            return;
          }

          if (event.type === "tool_result") {
            const payload = (event.data ?? {}) as { content?: string; tool_call_id?: string; name?: string };
            setEntries((prev) =>
              prev.map((e) => {
                if (e.id !== turnId || e.role !== "assistant") return e;
                const turn = e as AssistantTurn;
                const updatedSteps = turn.toolSteps.map((s) =>
                  s.id === payload.tool_call_id
                    ? { ...s, result: payload.content ?? "", status: "done" as const }
                    : s,
                );
                return { ...turn, toolSteps: updatedSteps };
              }),
            );
            return;
          }

          if (event.type === "status") {
            const status = event.data as StreamStatus | undefined;
            if (status) setRuntimeStatus(status);
            return;
          }

          if (event.type === "error") {
            const text = typeof event.data === "string" ? event.data : JSON.stringify(event.data ?? "Unknown error");
            setEntries((prev) =>
              prev.map((e) =>
                e.id === turnId && e.role === "assistant"
                  ? { ...e, content: `${e.content}\n\nError: ${text}` }
                  : e,
              ),
            );
          }
        });
      } finally {
        setIsStreaming(false);
        setStreamTurnId(null);
        await loadThread(threadId);
        await refreshThreads();
      }
    },
    [activeThreadId, loadThread, refreshThreads, selectedSandbox],
  );

  const handlePauseSandbox = useCallback(async () => {
    if (!activeThreadId) return;
    setSandboxActionError(null);
    try {
      await pauseThreadSandbox(activeThreadId);
      await loadThread(activeThreadId);
    } catch (e) {
      setSandboxActionError(e instanceof Error ? e.message : String(e));
    }
  }, [activeThreadId, loadThread]);

  const handleResumeSandbox = useCallback(async () => {
    if (!activeThreadId) return;
    setSandboxActionError(null);
    try {
      await resumeThreadSandbox(activeThreadId);
      await loadThread(activeThreadId);
    } catch (e) {
      setSandboxActionError(e instanceof Error ? e.message : String(e));
    }
  }, [activeThreadId, loadThread]);

  return (
    <div className="h-screen w-screen bg-white flex overflow-hidden">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        collapsed={sidebarCollapsed}
        onSelectThread={setActiveThreadId}
        onCreateThread={() => setNewThreadOpen(true)}
        onDeleteThread={(id) => void handleDeleteThread(id)}
        onSearchClick={() => setSearchOpen(true)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Header
          activeThreadId={activeThreadId}
          threadPreview={threads.find((t) => t.thread_id === activeThreadId)?.preview ?? null}
          sandboxInfo={activeSandbox}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
          onToggleComputer={() => setComputerOpen((v) => !v)}
          onPauseSandbox={() => void handlePauseSandbox()}
          onResumeSandbox={() => void handleResumeSandbox()}
          computerOpen={computerOpen}
        />

        <div className="flex-1 flex min-h-0">
          <div className={`flex flex-col transition-all duration-300 ${computerOpen ? "w-1/2" : "flex-1"}`}>
            {sandboxActionError && (
              <div className="px-3 py-2 text-xs bg-red-50 text-red-600 border-b border-red-200">
                {sandboxActionError}
              </div>
            )}
            <ChatArea entries={entries} isStreaming={isStreaming} runtimeStatus={runtimeStatus} />
            {(isStreaming || activeSandbox?.status === "running" || activeSandbox?.status === "paused") && (
              <TaskProgress
                isStreaming={isStreaming}
                runtimeStatus={runtimeStatus}
                sandboxType={activeSandbox?.type ?? "local"}
                sandboxStatus={activeSandbox?.status ?? (activeSandbox?.type === "local" ? "running" : null)}
                onOpenComputer={() => setComputerOpen(true)}
              />
            )}
            <InputBox
              disabled={isStreaming}
              placeholder={activeThreadId ? "告诉 Leon 你需要什么帮助..." : "新建会话后开始对话"}
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

      <NewThreadModal
        open={newThreadOpen}
        sandboxTypes={sandboxTypes}
        onClose={() => setNewThreadOpen(false)}
        onCreate={(sandbox) => {
          setNewThreadOpen(false);
          void handleCreateThread(sandbox);
        }}
      />

      <SearchModal
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        threads={threads}
        onSelectThread={(threadId) => setActiveThreadId(threadId)}
      />

      <SandboxSessionsModal
        isOpen={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
        onSessionMutated={(threadId) => {
          if (activeThreadId === threadId) {
            void loadThread(threadId);
          }
          void refreshThreads();
        }}
      />
    </div>
  );
}
