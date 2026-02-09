import { useEffect, useState } from "react";
import {
  destroySandboxSession,
  listSandboxSessions,
  pauseSandboxSession,
  resumeSandboxSession,
  type SandboxSession,
} from "../api";

interface SandboxSessionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSessionMutated?: (threadId: string) => void;
}

export default function SandboxSessionsModal({ isOpen, onClose, onSessionMutated }: SandboxSessionsModalProps) {
  const [sessions, setSessions] = useState<SandboxSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh(opts?: { silent?: boolean }) {
    const silent = opts?.silent ?? false;
    const showInitialLoading = !hasLoaded && !silent;
    if (showInitialLoading) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    try {
      const rows = await listSandboxSessions();
      setSessions(rows);
      setHasLoaded(true);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    if (!isOpen) return;
    void refresh();
    const timer = window.setInterval(() => {
      void refresh({ silent: true });
    }, 2500);
    return () => window.clearInterval(timer);
  }, [isOpen]);

  if (!isOpen) return null;

  async function withBusy(row: SandboxSession, fn: () => Promise<void>) {
    setBusy(row.session_id);
    try {
      await fn();
      if (!row.thread_id.startsWith("(")) {
        onSessionMutated?.(row.thread_id);
      }
      await refresh();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-[860px] max-w-[95vw] max-h-[85vh] rounded-xl border border-[#333] bg-[#1f1f1f] shadow-2xl overflow-hidden">
        <div className="h-12 px-4 border-b border-[#333] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-white text-sm font-semibold">Sandbox Sessions</h3>
            {refreshing && <span className="text-xs text-gray-500">Refreshing…</span>}
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 text-xs rounded bg-[#2d2d2d] hover:bg-[#3a3a3a] text-gray-200" onClick={() => void refresh()}>
              Refresh
            </button>
            <button className="px-3 py-1 text-xs rounded bg-[#2d2d2d] hover:bg-[#3a3a3a] text-gray-200" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
        <div className="p-4 overflow-auto max-h-[calc(85vh-48px)]">
          {loading && sessions.length === 0 && <p className="text-sm text-gray-400">Loading...</p>}
          {error && sessions.length === 0 && <p className="text-sm text-red-400">{error}</p>}
          {error && sessions.length > 0 && <p className="text-xs text-red-400 mb-2">Refresh failed: {error}</p>}
          {!loading && sessions.length === 0 && !error && <p className="text-sm text-gray-400">No active sessions.</p>}
          {sessions.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-[#333]">
                  <th className="text-left py-2">Thread</th>
                  <th className="text-left py-2">Session</th>
                  <th className="text-left py-2">Provider</th>
                  <th className="text-left py-2">Status</th>
                  <th className="text-left py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((row) => (
                  <tr key={row.session_id} className="border-b border-[#2a2a2a] text-gray-200">
                    <td className="py-2 font-mono text-xs">{row.thread_id.slice(0, 16)}</td>
                    <td className="py-2 font-mono text-xs">{row.session_id.slice(0, 16)}</td>
                    <td className="py-2">{row.provider}</td>
                    <td className="py-2">
                      <span className="px-2 py-0.5 rounded bg-[#2d2d2d] text-xs">{row.status}</span>
                    </td>
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        {row.status === "running" && (
                          <button
                            className="px-2 py-1 text-xs rounded bg-[#384e8a] hover:bg-[#4560aa] disabled:opacity-50"
                            disabled={busy === row.session_id}
                            onClick={() => void withBusy(row, () => pauseSandboxSession(row.session_id, row.provider))}
                          >
                            Pause
                          </button>
                        )}
                        {row.status === "paused" && (
                          <button
                            className="px-2 py-1 text-xs rounded bg-[#2d6a4f] hover:bg-[#367d5c] disabled:opacity-50"
                            disabled={busy === row.session_id}
                            onClick={() => void withBusy(row, () => resumeSandboxSession(row.session_id, row.provider))}
                          >
                            Resume
                          </button>
                        )}
                        <button
                          className="px-2 py-1 text-xs rounded bg-[#8a3838] hover:bg-[#aa4545] disabled:opacity-50"
                          disabled={busy === row.session_id}
                          onClick={() => void withBusy(row, () => destroySandboxSession(row.session_id, row.provider))}
                        >
                          Destroy
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
