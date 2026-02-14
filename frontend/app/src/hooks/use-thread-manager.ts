import { useCallback, useEffect, useState } from "react";
import {
  createThread,
  deleteThread,
  getThread,
  listSandboxTypes,
  listThreads,
  mapBackendEntries,
  type ChatEntry,
  type SandboxInfo,
  type SandboxType,
  type ThreadSummary,
} from "../api";

export interface ThreadManagerState {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  entries: ChatEntry[];
  activeSandbox: SandboxInfo | null;
  sandboxTypes: SandboxType[];
  selectedSandbox: string;
  loading: boolean;
}

export interface ThreadManagerActions {
  setActiveThreadId: (id: string | null) => void;
  setEntries: React.Dispatch<React.SetStateAction<ChatEntry[]>>;
  setActiveSandbox: React.Dispatch<React.SetStateAction<SandboxInfo | null>>;
  setSelectedSandbox: (name: string) => void;
  setThreads: React.Dispatch<React.SetStateAction<ThreadSummary[]>>;
  loadThread: (threadId: string) => Promise<void>;
  refreshThreads: () => Promise<void>;
  handleCreateThread: (sandbox?: string, cwd?: string) => Promise<void>;
  handleDeleteThread: (threadId: string) => Promise<void>;
}

export function useThreadManager(): ThreadManagerState & ThreadManagerActions {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [activeSandbox, setActiveSandbox] = useState<SandboxInfo | null>(null);
  const [sandboxTypes, setSandboxTypes] = useState<SandboxType[]>([{ name: "local", available: true }]);
  const [selectedSandbox, setSelectedSandbox] = useState("local");
  const [loading, setLoading] = useState(true);

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

  // Bootstrap: load sandbox types + threads on mount
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

  // Load thread data when active thread changes
  useEffect(() => {
    if (!activeThreadId) {
      setEntries([]);
      setActiveSandbox(null);
      return;
    }
    void loadThread(activeThreadId);
  }, [activeThreadId, loadThread]);

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

  return {
    threads, activeThreadId, entries, activeSandbox, sandboxTypes, selectedSandbox, loading,
    setActiveThreadId, setEntries, setActiveSandbox, setSelectedSandbox, setThreads,
    loadThread, refreshThreads, handleCreateThread, handleDeleteThread,
  };
}
