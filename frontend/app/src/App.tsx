import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

/** Horizontal drag-to-resize hook. Set invert=true for right-side panels. */
function useResizableX(initial: number, min: number, max: number, invert = false) {
  const [width, setWidth] = useState(initial);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      startX.current = e.clientX;
      startW.current = width;

      const onMove = (ev: MouseEvent) => {
        if (!dragging.current) return;
        const delta = ev.clientX - startX.current;
        setWidth(Math.min(max, Math.max(min, startW.current + (invert ? -delta : delta))));
      };
      const onUp = () => {
        dragging.current = false;
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [width, min, max, invert],
  );

  return { width, onMouseDown };
}

function DragHandle({ onMouseDown }: { onMouseDown: (e: React.MouseEvent) => void }) {
  return (
    <div
      className="w-1 flex-shrink-0 cursor-col-resize hover:bg-blue-400 active:bg-blue-500 transition-colors"
      onMouseDown={onMouseDown}
    />
  );
}
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
  cancelRun,
  createThread,
  deleteThread,
  getThread,
  getThreadLease,
  listSandboxTypes,
  listThreads,
  mapBackendEntries,
  pauseThreadSandbox,
  resumeThreadSandbox,
  setQueueMode,
  startRun,
  steerThread,
  type AssistantTurn,
  type ChatEntry,
  type SandboxInfo,
  type SandboxType,
  type StreamStatus,
  type ThreadSummary,
  type ToolSegment,
} from "./api";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [computerOpen, setComputerOpen] = useState(false);
  const [computerTab, setComputerTab] = useState<"terminal" | "files" | "agents">("terminal");
  const [focusedAgentStepId, setFocusedAgentStepId] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);
  const [newThreadOpen, setNewThreadOpen] = useState(false);
  const [queueEnabled, setQueueEnabled] = useState(false);

  const sidebarResize = useResizableX(272, 200, 420);
  const computerResize = useResizableX(600, 360, 1200, true);

  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [sandboxTypes, setSandboxTypes] = useState<SandboxType[]>([{ name: "local", available: true }]);
  const [selectedSandbox, setSelectedSandbox] = useState("local");
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeSandbox, setActiveSandbox] = useState<SandboxInfo | null>(null);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [runtimeStatus, setRuntimeStatus] = useState<StreamStatus | null>(null);
  const [sandboxActionError, setSandboxActionError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Track the current streaming assistant turn id for appending
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);

  // AbortController for stopping streaming
  const abortControllerRef = useRef<AbortController | null>(null);

  const refreshThreads = useCallback(async () => {
    const rows = await listThreads();
    setThreads(rows);
    if (!activeThreadId && rows.length > 0) {
      setActiveThreadId(rows[0].thread_id);
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
      } finally {
        setLoading(false);
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

  useEffect(() => {
    if (!isStreaming || !activeThreadId) return;
    let cancelled = false;
    const threadId = activeThreadId;

    const refreshSandboxStatus = async () => {
      try {
        const lease = await getThreadLease(threadId);
        if (cancelled) return;
        const status = lease.instance?.state ?? null;
        setActiveSandbox((prev) => {
          if (!prev) return prev;
          if (prev.type === "local") return prev;
          if (prev.status === status) return prev;
          return { ...prev, status };
        });
      } catch {
        // ignore transient polling errors
      }
    };

    void refreshSandboxStatus();
    const timer = window.setInterval(() => {
      void refreshSandboxStatus();
    }, 1500);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [isStreaming, activeThreadId]);

  const handleCreateThread = useCallback(async (sandbox?: string, cwd?: string) => {
    const type = sandbox ?? selectedSandbox;
    const thread = await createThread(type, cwd);
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
        segments: [],
        timestamp: Date.now(),
      };
      setEntries((prev) => [...prev, userEntry, assistantTurn]);
      setStreamTurnId(turnId);
      setIsStreaming(true);
      setRuntimeStatus(null);

      // Create new AbortController for this request
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let aborted = false;
      try {
        await startRun(threadId, message, (event) => {
          if (event.type === "text") {
            const payload = event.data as { content?: string } | string | undefined;
            const chunk = typeof payload === "string" ? payload : payload?.content ?? "";
            flushSync(() => {
              setEntries((prev) =>
                prev.map((e) => {
                  if (e.id !== turnId || e.role !== "assistant") return e;
                  const turn = e as AssistantTurn;
                  const segs = [...turn.segments];
                  const last = segs[segs.length - 1];
                  if (last && last.type === "text") {
                    segs[segs.length - 1] = { type: "text", content: last.content + chunk };
                  } else {
                    segs.push({ type: "text", content: chunk });
                  }
                  return { ...turn, segments: segs };
                }),
              );
            });
            return;
          }

          if (event.type === "tool_call") {
            const payload = (event.data ?? {}) as { id?: string; name?: string; args?: unknown };
            const seg: ToolSegment = {
              type: "tool",
              step: {
                id: payload.id ?? makeId("tc"),
                name: payload.name ?? "tool",
                args: payload.args ?? {},
                status: "calling",
                timestamp: Date.now(),
              },
            };
            setEntries((prev) =>
              prev.map((e) =>
                e.id === turnId && e.role === "assistant"
                  ? { ...e, segments: [...(e as AssistantTurn).segments, seg] }
                  : e,
              ),
            );
            return;
          }

          if (event.type === "tool_result") {
            const payload = (event.data ?? {}) as { content?: string; tool_call_id?: string; name?: string };

            // Ensure "calling" state is visible for at least 200ms before showing result
            const updateResult = () => {
              setEntries((prev) =>
                prev.map((e) => {
                  if (e.id !== turnId || e.role !== "assistant") return e;
                  const turn = e as AssistantTurn;
                  const updatedSegs = turn.segments.map((s) => {
                    if (s.type !== "tool" || s.step.id !== payload.tool_call_id) return s;
                    return { ...s, step: { ...s.step, result: payload.content ?? "", status: "done" as const } };
                  });
                  return { ...turn, segments: updatedSegs };
                })
              );
            };

            // Check if tool call was just created (within last 200ms)
            setEntries((prev) => {
              const turn = prev.find((e) => e.id === turnId && e.role === "assistant") as AssistantTurn | undefined;
              if (turn) {
                const toolSeg = turn.segments.find(
                  (s) => s.type === "tool" && s.step.id === payload.tool_call_id,
                ) as ToolSegment | undefined;
                if (toolSeg) {
                  const elapsed = Date.now() - toolSeg.step.timestamp;
                  if (elapsed < 200) {
          // Delay the result update to ensure "calling" state is visible
                    setTimeout(updateResult, 200 - elapsed);
                    return prev; // Don't update yet
                  }
                }
              }
              // Tool call is old enough, update immediately
              return prev.map((e) => {
                if (e.id !== turnId || e.role !== "assistant") return e;
                const turn = e as AssistantTurn;
                const updatedSegs = turn.segments.map((s) => {
                  if (s.type !== "tool" || s.step.id !== payload.tool_call_id) return s;
                  return { ...s, step: { ...s.step, result: payload.content ?? "", status: "done" as const } };
                });
                return { ...turn, segments: updatedSegs };
              });
            });
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
              prev.map((e) => {
                if (e.id !== turnId || e.role !== "assistant") return e;
                const turn = e as AssistantTurn;
                const segs = [...turn.segments];
                segs.push({ type: "text", content: `\n\nError: ${text}` });
                return { ...turn, segments: segs };
              }),
            );
          }

          if (event.type === "cancelled") {
            setIsStreaming(false);
            // Mark cancelled tool calls
            const cancelledToolCallIds = (event.data as any)?.cancelled_tool_call_ids || [];

            setEntries((prev) =>
              prev.map((e) => {
                if (e.id !== turnId || e.role !== "assistant") return e;
                const turn = e as AssistantTurn;
                const updatedSegs = turn.segments.map((seg) => {
                  if (seg.type === "tool") {
                    const step = seg.step;
                    if (cancelledToolCallIds.includes(step.id)) {
                      return {
                        ...seg,
                        step: {
                          ...step,
                          status: "cancelled" as const,
                          result: "任务被用户取消",
                        },
                      };
                    }
                  }
                  return seg;
                });
                return { ...turn, segments: updatedSegs };
              }),
            );
          }

          // Handle sub-agent events
          if (event.type.startsWith("subagent_")) {
            const data = event.data as any;
            const parentToolCallId = data?.parent_tool_call_id;

            if (!parentToolCallId) return;

            // Find the parent tool call and update its streaming state
            setEntries((prev) =>
              prev.map((e) => {
                if (e.id !== turnId || e.role !== "assistant") return e;
                const turn = e as AssistantTurn;
                const updatedSegs = turn.segments.map((s) => {
                  if (s.type !== "tool" || s.step.id !== parentToolCallId) return s;

                  // Initialize subagent_stream if not present
                  const step = s.step;
                  if (!step.subagent_stream) {
                    step.subagent_stream = {
                      task_id: "",
                      thread_id: "",
                      text: "",
                      tool_calls: [],
                      status: "running",
                    };
                  }

                  const stream = step.subagent_stream;

                  // Handle different sub-agent event types
                  if (event.type === "subagent_task_start") {
                    stream.task_id = data.task_id || "";
                    stream.thread_id = data.thread_id || "";
                    stream.status = "running";
                  } else if (event.type === "subagent_task_text") {
                    stream.text += data.content || "";
                  } else if (event.type === "subagent_task_tool_call") {
                    stream.tool_calls.push({
                      id: data.tool_call_id || "",
                      name: data.name || "",
                      args: data.args || {},
                    });
                  } else if (event.type === "subagent_task_done") {
                    stream.status = "completed";
                  } else if (event.type === "subagent_task_error") {
                    stream.status = "error";
                    stream.error = data.error || "Unknown error";
                  }

                  return { ...s, step: { ...step } };
                });
                return { ...turn, segments: updatedSegs };
              }),
            );
          }
        }, abortController.signal);
      } catch (error) {
        // Handle abort
        if (error instanceof Error && error.name === "AbortError") {
          aborted = true;
          // Just stop streaming, keep existing content as-is
        } else {
          throw error;
        }
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
        setStreamTurnId(null);
        if (!aborted) {
          await loadThread(threadId);
        }
        await refreshThreads();
      }
    },
    [activeThreadId, loadThread, refreshThreads, selectedSandbox],
  );

  const handleStopStreaming = useCallback(async () => {
    // 1. Notify backend to cancel the run (do this first so backend stops before we abort)
    if (activeThreadId) {
      try {
        await cancelRun(activeThreadId);
      } catch (e) {
        console.error("Failed to cancel run:", e);
      }
    }

    // 2. Delay abort to give backend time to send the cancelled event
    setTimeout(() => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }, 500);
  }, [activeThreadId]);

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

  const handleFocusAgent = useCallback((stepId: string) => {
    setFocusedAgentStepId(stepId);
    setComputerTab("agents");
    setComputerOpen(true);
  }, []);

  const handleSendQueueMessage = useCallback(
    async (message: string) => {
      if (!activeThreadId) return;
      // Add user message to UI so it's visible
      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      setEntries((prev) => [...prev, userEntry]);
      await steerThread(activeThreadId, message);
    },
    [activeThreadId],
  );

  const handleToggleQueue = useCallback(async () => {
    const next = !queueEnabled;
    setQueueEnabled(next);
    if (activeThreadId) {
      try {
        await setQueueMode(activeThreadId, next ? "followup" : "steer");
      } catch {
        // ignore — backend may not support this yet
      }
    }
  }, [activeThreadId, queueEnabled]);

  return (
    <div className="h-screen w-screen bg-white flex overflow-hidden">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        collapsed={sidebarCollapsed}
        loading={loading}
        width={sidebarResize.width}
        onSelectThread={setActiveThreadId}
        onCreateThread={() => setNewThreadOpen(true)}
        onDeleteThread={(id) => void handleDeleteThread(id)}
        onSearchClick={() => setSearchOpen(true)}
      />
      {!sidebarCollapsed && <DragHandle onMouseDown={sidebarResize.onMouseDown} />}

      <div className="flex-1 flex flex-col min-w-0">
        <Header
          activeThreadId={activeThreadId}
          threadPreview={threads.find((t) => t.thread_id === activeThreadId)?.preview ?? null}
          sandboxInfo={activeSandbox}
          queueEnabled={queueEnabled}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
          onPauseSandbox={() => void handlePauseSandbox()}
          onResumeSandbox={() => void handleResumeSandbox()}
          onToggleQueue={() => void handleToggleQueue()}
        />

        <div className="flex-1 flex min-h-0">
          <div className="flex-1 flex flex-col min-w-0">
            {sandboxActionError && (
              <div className="px-3 py-2 text-xs bg-red-50 text-red-600 border-b border-red-200">
                {sandboxActionError}
              </div>
            )}
            <ChatArea entries={entries} isStreaming={isStreaming} streamTurnId={streamTurnId} runtimeStatus={runtimeStatus} loading={loading} onFocusAgent={handleFocusAgent} />
            {activeThreadId && (
              <TaskProgress
                isStreaming={isStreaming}
                runtimeStatus={runtimeStatus}
                sandboxType={activeSandbox?.type ?? "local"}
                sandboxStatus={activeSandbox?.status ?? (activeSandbox?.type === "local" ? "running" : null)}
                computerOpen={computerOpen}
                onToggleComputer={() => setComputerOpen((v) => !v)}
              />
            )}
            <InputBox
              disabled={isStreaming}
              isStreaming={isStreaming}
              queueEnabled={queueEnabled}
              placeholder={activeThreadId ? "告诉 Leon 你需要什么帮助..." : "新建会话后开始对话"}
              onSendMessage={handleSendMessage}
              onSendQueueMessage={activeThreadId ? handleSendQueueMessage : undefined}
              onStop={handleStopStreaming}
            />
          </div>

          {computerOpen && (
            <>
              <DragHandle onMouseDown={computerResize.onMouseDown} />
              <ComputerPanel
                isOpen={computerOpen}
                onClose={() => setComputerOpen(false)}
                threadId={activeThreadId}
                sandboxType={activeSandbox?.type ?? null}
                chatEntries={entries}
                width={computerResize.width}
                activeTab={computerTab}
                onTabChange={setComputerTab}
                focusedAgentStepId={focusedAgentStepId}
                onFocusAgent={setFocusedAgentStepId}
              />
            </>
          )}
        </div>
      </div>

      <NewThreadModal
        open={newThreadOpen}
        sandboxTypes={sandboxTypes}
        onClose={() => setNewThreadOpen(false)}
        onCreate={(sandbox, cwd) => {
          setNewThreadOpen(false);
          void handleCreateThread(sandbox, cwd);
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
