import { ChevronRight, FileText, Folder, Globe, Loader2, Minimize2, Pause, Play, Terminal, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  getThreadLease,
  getThreadSession,
  getThreadTerminal,
  listWorkspace,
  pauseThreadSandbox,
  readWorkspaceFile,
  resumeThreadSandbox,
  type LeaseStatus,
  type SessionStatus,
  type TerminalStatus,
  type WorkspaceEntry,
} from "../api";

interface ComputerPanelProps {
  isOpen: boolean;
  onClose: () => void;
  threadId: string | null;
  sandboxType: string | null;
}

function joinPath(base: string, name: string): string {
  if (base.endsWith("/")) return `${base}${name}`;
  return `${base}/${name}`;
}

export default function ComputerPanel({ isOpen, onClose, threadId, sandboxType }: ComputerPanelProps) {
  const [activeTab, setActiveTab] = useState<"terminal" | "browser" | "files">("terminal");
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [terminal, setTerminal] = useState<TerminalStatus | null>(null);
  const [lease, setLease] = useState<LeaseStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [currentPath, setCurrentPath] = useState<string>("");
  const [entries, setEntries] = useState<WorkspaceEntry[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const isRemote = sandboxType !== null && sandboxType !== "local";
  const instanceState = lease?.instance?.state ?? null;
  const canPause = instanceState === "running";
  const canResume = instanceState === "paused";

  async function refreshStatus() {
    if (!threadId) return;
    setStatusError(null);
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
      setEntries(data.entries);
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

  const pathParts = useMemo(() => currentPath.split("/").filter(Boolean), [currentPath]);

  if (!isOpen) return null;

  return (
    <div className="h-full bg-[#1e1e1e] border-l border-[#333] flex flex-col animate-fade-in" style={{ width: "52%", minWidth: "460px" }}>
      <div className="h-12 border-b border-[#333] flex items-center justify-between px-4 flex-shrink-0">
        <div>
          <h3 className="text-white text-sm font-medium">Workspace / Terminal</h3>
          <p className="text-[11px] text-gray-500 font-mono">{threadId ? threadId.slice(0, 20) : "no-thread"}</p>
        </div>
        <div className="flex items-center gap-1">
          {canPause && (
            <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center" onClick={() => void (threadId && pauseThreadSandbox(threadId).then(refreshStatus))}>
              <Pause className="w-4 h-4 text-gray-300" />
            </button>
          )}
          {canResume && (
            <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center" onClick={() => void (threadId && resumeThreadSandbox(threadId).then(refreshStatus))}>
              <Play className="w-4 h-4 text-gray-300" />
            </button>
          )}
          <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center" onClick={onClose}>
            <Minimize2 className="w-4 h-4 text-gray-300" />
          </button>
          <button className="w-8 h-8 rounded-lg hover:bg-red-700/30 flex items-center justify-center" onClick={onClose}>
            <X className="w-4 h-4 text-gray-300" />
          </button>
        </div>
      </div>

      <div className="h-10 border-b border-[#333] flex items-center px-2 flex-shrink-0">
        <button onClick={() => setActiveTab("terminal")} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${activeTab === "terminal" ? "bg-[#2a2a2a] text-white" : "text-gray-400 hover:text-gray-300"}`}>
          <Terminal className="w-4 h-4" />
          <span>Terminal</span>
        </button>
        <button onClick={() => setActiveTab("browser")} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${activeTab === "browser" ? "bg-[#2a2a2a] text-white" : "text-gray-400 hover:text-gray-300"}`}>
          <Globe className="w-4 h-4" />
          <span>Browser</span>
        </button>
        <button onClick={() => setActiveTab("files")} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${activeTab === "files" ? "bg-[#2a2a2a] text-white" : "text-gray-400 hover:text-gray-300"}`}>
          <FileText className="w-4 h-4" />
          <span>Workspace</span>
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === "terminal" && (
          <div className="h-full overflow-auto p-4">
            {statusError && <p className="text-sm text-red-400">{statusError}</p>}
            {!statusError && (
              <div className="space-y-3 text-sm">
                <div className="rounded-lg border border-[#333] bg-[#181818] p-3">
                  <div className="text-xs text-gray-500 mb-1">Session</div>
                  <div className="text-gray-200 font-mono">{session?.session_id ?? "local-thread"}</div>
                  {session && <div className="text-xs text-gray-500 mt-1">last active: {new Date(session.last_active_at).toLocaleString()}</div>}
                </div>
                <div className="rounded-lg border border-[#333] bg-[#181818] p-3">
                  <div className="text-xs text-gray-500 mb-1">Terminal</div>
                  <div className="text-gray-200 font-mono">cwd: {terminal?.cwd ?? "(local)"}</div>
                  {terminal && <div className="text-xs text-gray-500 mt-1">version: {terminal.version}</div>}
                </div>
                <div className="rounded-lg border border-[#333] bg-[#181818] p-3">
                  <div className="text-xs text-gray-500 mb-1">Lease</div>
                  <div className="text-gray-200">state: {lease?.instance?.state ?? (isRemote ? "detached" : "n/a")}</div>
                  {lease?.instance?.instance_id && <div className="text-xs text-gray-500 mt-1 font-mono">{lease.instance.instance_id}</div>}
                </div>
                <button className="px-3 py-2 rounded bg-[#2a2a2a] hover:bg-[#343434] text-xs text-gray-200" onClick={() => void refreshStatus()}>
                  Refresh
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === "browser" && (
          <div className="h-full flex items-center justify-center bg-[#0f0f0f] text-gray-500 text-sm">Browser view is reserved for next step.</div>
        )}

        {activeTab === "files" && (
          <div className="h-full flex bg-[#1a1a1a]">
            <div className="w-72 border-r border-[#333] flex flex-col">
              <div className="px-3 py-2 border-b border-[#333]">
                <div className="flex items-center flex-wrap gap-1 text-xs text-gray-400">
                  <button className="hover:text-gray-200" onClick={() => void refreshWorkspace("/")}>/</button>
                  {pathParts.map((part, index) => {
                    const partial = `/${pathParts.slice(0, index + 1).join("/")}`;
                    return (
                      <span key={partial} className="flex items-center gap-1">
                        <ChevronRight className="w-3 h-3" />
                        <button className="hover:text-gray-200" onClick={() => void refreshWorkspace(partial)}>{part}</button>
                      </span>
                    );
                  })}
                </div>
              </div>
              <div className="flex-1 overflow-auto p-2 space-y-1">
                {loadingWorkspace && (
                  <div className="text-xs text-gray-400 flex items-center gap-2 px-2 py-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Loading...
                  </div>
                )}
                {workspaceError && <p className="text-xs text-red-400 px-2 py-2">{workspaceError}</p>}
                {!loadingWorkspace && !workspaceError && entries.map((entry) => (
                  <button
                    key={`${currentPath}-${entry.name}`}
                    className="w-full text-left px-2 py-1.5 rounded hover:bg-[#2a2a2a] text-gray-200 text-sm flex items-center gap-2"
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
                    {entry.is_dir ? <Folder className="w-4 h-4 text-blue-400" /> : <FileText className="w-4 h-4 text-gray-400" />}
                    <span className="flex-1 truncate">{entry.name}</span>
                    {!entry.is_dir && <span className="text-[10px] text-gray-500">{entry.size}</span>}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex-1 overflow-auto">
              {!selectedFilePath && <div className="h-full flex items-center justify-center text-sm text-gray-500">Select a file to preview</div>}
              {selectedFilePath && (
                <div className="h-full flex flex-col">
                  <div className="px-4 py-2 border-b border-[#333] text-xs text-gray-400 font-mono">{selectedFilePath}</div>
                  <pre className="flex-1 p-4 text-sm text-gray-200 whitespace-pre-wrap break-words font-mono">{selectedFileContent}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
