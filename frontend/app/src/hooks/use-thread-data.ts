import { useCallback, useEffect, useState } from "react";
import {
  getThread,
  mapBackendEntries,
  type ChatEntry,
  type SandboxInfo,
} from "../api";

export interface ThreadDataState {
  entries: ChatEntry[];
  activeSandbox: SandboxInfo | null;
  loading: boolean;
}

export interface ThreadDataActions {
  setEntries: React.Dispatch<React.SetStateAction<ChatEntry[]>>;
  setActiveSandbox: React.Dispatch<React.SetStateAction<SandboxInfo | null>>;
  loadThread: (threadId: string) => Promise<void>;
  refreshThread: () => Promise<void>;
}

export function useThreadData(threadId: string | undefined, skipInitialLoad = false): ThreadDataState & ThreadDataActions {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [activeSandbox, setActiveSandbox] = useState<SandboxInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const loadThread = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const thread = await getThread(id);
      const mappedEntries = mapBackendEntries(thread.messages);
      console.log('[useThreadData] Loaded thread:', id, 'messages:', thread.messages.length, 'entries:', mappedEntries.length);
      setEntries(mappedEntries);
      setActiveSandbox(thread.sandbox);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshThread = useCallback(async () => {
    if (threadId) {
      await loadThread(threadId);
    }
  }, [threadId, loadThread]);

  // Load thread data when threadId changes
  useEffect(() => {
    if (!threadId) {
      setEntries([]);
      setActiveSandbox(null);
      setLoading(false);
      return;
    }
    if (skipInitialLoad) {
      console.log('[useThreadData] Skipping initial load for new thread');
      setLoading(false);
      return;
    }
    void loadThread(threadId);
  }, [threadId, loadThread, skipInitialLoad]);

  return {
    entries,
    activeSandbox,
    loading,
    setEntries,
    setActiveSandbox,
    loadThread,
    refreshThread,
  };
}
