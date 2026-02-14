import { useCallback, useState } from "react";
import {
  getThreadLease,
  getThreadSession,
  getThreadTerminal,
  type LeaseStatus,
  type SessionStatus,
  type TerminalStatus,
} from "../../api";

interface UseSandboxStatusOptions {
  threadId: string | null;
  isRemote: boolean;
}

interface SandboxStatusResult {
  session: SessionStatus | null;
  terminal: TerminalStatus | null;
  lease: LeaseStatus | null;
  statusError: string | null;
  /** Returns the terminal cwd if fetched successfully */
  refreshStatus: () => Promise<string | undefined>;
}

export function useSandboxStatus({ threadId, isRemote }: UseSandboxStatusOptions): SandboxStatusResult {
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [terminal, setTerminal] = useState<TerminalStatus | null>(null);
  const [lease, setLease] = useState<LeaseStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const refreshStatus = useCallback(async (): Promise<string | undefined> => {
    if (!threadId) return undefined;
    setStatusError(null);
    if (!isRemote) {
      setSession(null);
      setLease(null);
      setTerminal(null);
      return undefined;
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
      return t.cwd;
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : String(e));
      return undefined;
    }
  }, [threadId, isRemote]);

  return { session, terminal, lease, statusError, refreshStatus };
}
