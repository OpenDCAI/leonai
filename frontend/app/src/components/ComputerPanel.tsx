import { ChevronRight, FileText, Folder, Loader2, Pause, Play, Terminal } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getThreadLease,
  getThreadSession,
  getThreadTerminal,
  listWorkspace,
  pauseThreadSandbox,
  readWorkspaceFile,
  resumeThreadSandbox,
  type ChatEntry,
  type LeaseStatus,
  type SessionStatus,
  type TerminalStatus,
  type ToolStep,
  type WorkspaceEntry,
} from "../api";

interface ComputerPanelProps {
  isOpen: boolean;
  onClose: () => void;
  threadId: string | null;
  sandboxType: string | null;
  chatEntries: ChatEntry[];
  width?: number;
}

function joinPath(base: string, name: string): string {
  if (base.endsWith("/")) return `${base}${name}`;
  return `${base}/${name}`;
}

/** Extract all run_command tool steps from chat entries */
function extractCommandSteps(entries: ChatEntry[]): ToolStep[] {
  const steps: ToolStep[] = [];
  for (const entry of entries) {
    if (entry.role !== "assistant") continue;
    for (const seg of entry.segments) {
      if (seg.type === "tool" && seg.step.name === "run_command") {
        steps.push(seg.step);
      }
    }
  }
  return steps;
}

function parseCommandArgs(args: unknown): { command?: string; cwd?: string; description?: string } {
  if (args && typeof args === "object") {
    const a = args as Record<string, unknown>;
    return {
      command: (a.CommandLine ?? a.command ?? a.cmd) as string | undefined,
      cwd: (a.Cwd ?? a.cwd ?? a.working_directory) as string | undefined,
      description: a.description as string | undefined,
    };
  }
  return {};
}

/* ── Terminal view ─────────────────────────────────────────── */

function TerminalView({ steps }: { steps: ToolStep[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps]);

  return (
    <div
      ref={scrollRef}
      className="h-full overflow-auto font-mono text-[13px] leading-[1.6] p-4"
      style={{ background: "#1e1e1e", color: "#d4d4d4" }}
    >
      {/* Boot banner */}
      <div style={{ color: "#6a9955" }} className="mb-3 select-none">
        <div>Leon Terminal v1.0</div>
        <div className="text-[11px]" style={{ color: "#555" }}>Type is streamed from agent tool calls</div>
        <div className="mt-1" style={{ color: "#333" }}>{"─".repeat(48)}</div>
      </div>

      {steps.length === 0 && (
        <div style={{ color: "#555" }}>
          <span style={{ color: "#6a9955" }}>leon@sandbox</span>
          <span style={{ color: "#555" }}>:</span>
          <span style={{ color: "#569cd6" }}>~</span>
          <span style={{ color: "#d4d4d4" }}>$ </span>
          <span className="animate-pulse">_</span>
        </div>
      )}

      {steps.map((step) => {
        const { command, cwd } = parseCommandArgs(step.args);
        const dir = cwd || "~";
        const shortDir = dir === "/" ? "/" : dir.split("/").pop() || dir;

        return (
          <div key={step.id} className="mb-3">
            {/* Prompt line */}
            <div className="flex flex-wrap">
              <span style={{ color: "#6a9955" }}>leon@sandbox</span>
              <span style={{ color: "#d4d4d4" }}>:</span>
              <span style={{ color: "#569cd6" }}>{shortDir}</span>
              <span style={{ color: "#d4d4d4" }}>$ </span>
              <span style={{ color: "#ce9178" }}>{command || "(empty)"}</span>
            </div>

            {/* Output */}
            {step.status === "calling" ? (
              <div className="mt-0.5" style={{ color: "#555" }}>
                <span className="animate-pulse">...</span>
              </div>
            ) : step.result ? (
              <pre
                className="mt-0.5 whitespace-pre-wrap break-words"
                style={{ color: "#cccccc" }}
              >{step.result}</pre>
            ) : (
              <div className="mt-0.5" style={{ color: "#555" }}>(no output)</div>
            )}

            {/* Exit indicator for errors */}
            {step.status === "error" && (
              <div style={{ color: "#f44747" }} className="mt-0.5">
                [exit: error]
              </div>
            )}
          </div>
        );
      })}

      {/* Cursor at bottom if last command is done */}
      {steps.length > 0 && steps[steps.length - 1].status !== "calling" && (
        <div>
          <span style={{ color: "#6a9955" }}>leon@sandbox</span>
          <span style={{ color: "#d4d4d4" }}>:</span>
          <span style={{ color: "#569cd6" }}>~</span>
          <span style={{ color: "#d4d4d4" }}>$ </span>
          <span className="animate-pulse">_</span>
        </div>
      )}
    </div>
  );
}

/* ── Resizable file tree divider ───────────────────────────── */

function useResizable(initialWidth: number, minWidth: number, maxWidth: number) {
  const [width, setWidth] = useState(initialWidth);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = width;

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = ev.clientX - startX.current;
      const next = Math.min(maxWidth, Math.max(minWidth, startW.current + delta));
      setWidth(next);
    };

    const onMouseUp = () => {
      dragging.current = false;
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [width, minWidth, maxWidth]);

  return { width, onMouseDown };
}

/* ── Main panel ────────────────────────────────────────────── */

export default function ComputerPanel({ isOpen, onClose, threadId, sandboxType, chatEntries, width = 600 }: ComputerPanelProps) {
  const [activeTab, setActiveTab] = useState<"terminal" | "files">("terminal");
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [terminal, setTerminal] = useState<TerminalStatus | null>(null);
  const [lease, setLease] = useState<LeaseStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [currentPath, setCurrentPath] = useState<string>("");
  const [workspaceRoot, setWorkspaceRoot] = useState<string>("");
  const [fileEntries, setFileEntries] = useState<WorkspaceEntry[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const isRemote = sandboxType !== null && sandboxType !== "local";
  const commandSteps = useMemo(() => extractCommandSteps(chatEntries), [chatEntries]);
  const { width: treeWidth, onMouseDown: onDragStart } = useResizable(288, 160, 500);

  async function refreshStatus() {
    if (!threadId) return;
    setStatusError(null);
    if (!isRemote) {
      setSession(null);
      setLease(null);
      setTerminal(null);
      return;
    }
    try {
      const [s, t, l] = await Promise.all([
        getThreadSession(threadId),
        getThreadTerminal(threadId),
        getThreadLease(threadId),
      ]);
      setSession(s);
      setTerminal(t);
      setLease(l);
      if (!currentPath) setCurrentPath(t.cwd);
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : String(e));
    }
  }

  async function refreshWorkspace(pathOverride?: string) {
    if (!threadId) return;
    const target = pathOverride ?? currentPath;
    setLoadingWorkspace(true);
    setWorkspaceError(null);
    try {
      const data = await listWorkspace(threadId, target || undefined);
      setCurrentPath(data.path);
      if (!workspaceRoot) setWorkspaceRoot(data.path);
      setFileEntries(data.entries);
    } catch (e) {
      setWorkspaceError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingWorkspace(false);
    }
  }

  useEffect(() => {
    if (!isOpen) return;
    void refreshStatus();
  }, [isOpen, threadId, sandboxType]);

  useEffect(() => {
    if (!isOpen || !threadId || activeTab !== "files") return;
    void refreshWorkspace();
  }, [isOpen, threadId, activeTab]);

  const relativePath = useMemo(() => {
    if (!workspaceRoot || !currentPath) return "";
    if (currentPath === workspaceRoot) return "";
    const prefix = workspaceRoot.endsWith("/") ? workspaceRoot : workspaceRoot + "/";
    return currentPath.startsWith(prefix) ? currentPath.slice(prefix.length) : "";
  }, [currentPath, workspaceRoot]);

  const pathParts = useMemo(() => relativePath.split("/").filter(Boolean), [relativePath]);

  if (!isOpen) return null;

  return (
    <div className="h-full flex flex-col animate-fade-in bg-white border-l border-[#e5e5e5] flex-shrink-0" style={{ width }}>
      {/* Panel header */}
      <div className="h-12 flex items-center justify-between px-4 flex-shrink-0 border-b border-[#e5e5e5]">
        <div>
          <h3 className="text-sm font-semibold text-[#171717]">另一台小电脑</h3>
          <p className="text-[11px] font-mono text-[#a3a3a3]">
            {threadId ? threadId.slice(0, 20) : "无对话"}
          </p>
        </div>
        <div className="flex items-center gap-1">
          {isRemote && lease?.instance?.state === "running" && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
              onClick={() => void (threadId && pauseThreadSandbox(threadId).then(refreshStatus))}
            >
              <Pause className="w-4 h-4" />
            </button>
          )}
          {isRemote && lease?.instance?.state === "paused" && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-green-600"
              onClick={() => void (threadId && resumeThreadSandbox(threadId).then(refreshStatus))}
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          <button
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
            onClick={onClose}
            title="收起视窗"
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
              <polyline points="3,10 7,10 7,14" />
              <polyline points="13,6 9,6 9,2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="h-10 flex items-center px-2 flex-shrink-0 border-b border-[#e5e5e5]">
        <button
          onClick={() => setActiveTab("terminal")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === "terminal"
              ? "bg-[#f5f5f5] text-[#171717] font-medium"
              : "text-[#737373] hover:text-[#171717]"
          }`}
        >
          <Terminal className="w-4 h-4" />
          <span>终端</span>
        </button>
        <button
          onClick={() => setActiveTab("files")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === "files"
              ? "bg-[#f5f5f5] text-[#171717] font-medium"
              : "text-[#737373] hover:text-[#171717]"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>文件</span>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "terminal" && (
          <TerminalView steps={commandSteps} />
        )}

        {activeTab === "files" && (
          <div className="h-full flex bg-white">
            {/* File tree — resizable */}
            <div className="flex flex-col border-r border-[#e5e5e5] flex-shrink-0" style={{ width: treeWidth }}>
              <div className="px-3 py-2 border-b border-[#e5e5e5]">
                <div className="flex items-center flex-wrap gap-1 text-xs text-[#737373]">
                  <button
                    className="hover:text-[#171717] transition-colors font-medium"
                    onClick={() => void refreshWorkspace(workspaceRoot || "")}
                  >{workspaceRoot ? workspaceRoot.split("/").pop() || "/" : "/"}</button>
                  {pathParts.map((part, index) => {
                    const partial = workspaceRoot + "/" + pathParts.slice(0, index + 1).join("/");
                    return (
                      <span key={partial} className="flex items-center gap-1">
                        <ChevronRight className="w-3 h-3" />
                        <button
                          className="hover:text-[#171717] transition-colors"
                          onClick={() => void refreshWorkspace(partial)}
                        >{part}</button>
                      </span>
                    );
                  })}
                </div>
              </div>
              <div className="flex-1 overflow-auto p-2 space-y-0.5">
                {loadingWorkspace && (
                  <div className="text-xs flex items-center gap-2 px-2 py-2 text-[#737373]">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    加载中...
                  </div>
                )}
                {workspaceError && <p className="text-xs px-2 py-2 text-red-500">{workspaceError}</p>}
                {!loadingWorkspace && !workspaceError && fileEntries.map((entry) => (
                  <button
                    key={`${currentPath}-${entry.name}`}
                    className="w-full text-left px-2 py-1.5 rounded-lg text-sm flex items-center gap-2 text-[#171717] hover:bg-[#f5f5f5] transition-colors"
                    onClick={async () => {
                      const full = joinPath(currentPath || "/", entry.name);
                      if (entry.is_dir) {
                        setSelectedFilePath(null);
                        setSelectedFileContent("");
                        await refreshWorkspace(full);
                        return;
                      }
                      setSelectedFilePath(full);
                      const file = await readWorkspaceFile(threadId!, full);
                      setSelectedFileContent(file.content);
                    }}
                  >
                    {entry.is_dir
                      ? <Folder className="w-4 h-4 text-[#525252]" />
                      : <FileText className="w-4 h-4 text-[#a3a3a3]" />
                    }
                    <span className="flex-1 truncate">{entry.name}</span>
                    {!entry.is_dir && <span className="text-[10px] text-[#d4d4d4]">{entry.size}</span>}
                  </button>
                ))}
              </div>
            </div>

            {/* Drag handle */}
            <div
              className="w-1 cursor-col-resize hover:bg-blue-400 active:bg-blue-500 transition-colors flex-shrink-0"
              onMouseDown={onDragStart}
            />

            {/* File preview */}
            <div className="flex-1 overflow-auto min-w-0">
              {!selectedFilePath && (
                <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
                  选择文件以预览
                </div>
              )}
              {selectedFilePath && (
                <div className="h-full flex flex-col">
                  <div className="px-4 py-2 text-xs font-mono border-b border-[#e5e5e5] text-[#737373]">
                    {selectedFilePath}
                  </div>
                  <pre className="flex-1 p-4 text-sm whitespace-pre-wrap break-words font-mono text-[#404040]">
                    {selectedFileContent}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
