import { Loader2, Pause, Play, Trash2, X } from "lucide-react";
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
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  function statusBadge(status: string) {
    if (status === "running") {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
          运行中
        </span>
      );
    }
    if (status === "paused") {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">
          已暂停
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-[#f5f5f5] text-[#737373] border border-[#e5e5e5]">
        {status}
      </span>
    );
  }

  const visibleSessions = sessions.filter((row) => row.inspect_visible !== false);

  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-[860px] max-w-[95vw] max-h-[85vh] rounded-2xl overflow-hidden bg-white border border-[#e5e5e5] shadow-xl animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="h-12 px-5 flex items-center justify-between border-b border-[#e5e5e5]">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-[#171717]">运行环境会话</h3>
            {refreshing && <Loader2 className="w-3.5 h-3.5 animate-spin text-[#a3a3a3]" />}
          </div>
          <div className="flex items-center gap-2">
            <button
              className="px-3 py-1.5 rounded-lg text-xs border border-[#e5e5e5] text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717]"
              onClick={() => void refresh()}
            >
              刷新
            </button>
            <button
              className="w-7 h-7 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
              onClick={onClose}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-5 overflow-auto max-h-[calc(85vh-48px)] custom-scrollbar">
          {loading && sessions.length === 0 && (
            <div className="flex items-center gap-2 py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin text-[#a3a3a3]" />
              <span className="text-sm text-[#737373]">加载中...</span>
            </div>
          )}
          {error && sessions.length === 0 && <p className="text-sm py-8 text-center text-red-500">{error}</p>}
          {error && sessions.length > 0 && <p className="text-xs mb-3 text-red-500">刷新失败: {error}</p>}
          {!loading && visibleSessions.length === 0 && !error && (
            <p className="text-sm py-8 text-center text-[#a3a3a3]">暂无活跃会话</p>
          )}
          {visibleSessions.length > 0 && (
            <div className="space-y-2">
              {visibleSessions.map((row) => (
                <div
                  key={row.session_id}
                  className="flex items-center gap-4 p-3 rounded-xl bg-[#fafafa] border border-[#e5e5e5]"
                >
                  <div className="flex-1 min-w-0 grid grid-cols-4 gap-3 items-center">
                    <div>
                      <div className="text-[10px] uppercase tracking-wider mb-0.5 text-[#a3a3a3]">对话</div>
                      <div className="text-sm font-mono truncate text-[#171717]">{row.thread_id.slice(0, 16)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider mb-0.5 text-[#a3a3a3]">会话</div>
                      <div className="text-sm font-mono truncate text-[#171717]">{row.session_id.slice(0, 16)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider mb-0.5 text-[#a3a3a3]">环境</div>
                      <div className="text-sm text-[#171717]">{row.provider}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider mb-0.5 text-[#a3a3a3]">状态</div>
                      {statusBadge(row.status)}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {row.status === "running" && (
                      <button
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f0f0f0] hover:text-[#171717] disabled:opacity-30"
                        disabled={busy === row.session_id}
                        onClick={() => void withBusy(row, () => pauseSandboxSession(row.session_id, row.provider))}
                        title="暂停"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    )}
                    {row.status === "paused" && (
                      <button
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f0f0f0] hover:text-green-600 disabled:opacity-30"
                        disabled={busy === row.session_id}
                        onClick={() => void withBusy(row, () => resumeSandboxSession(row.session_id, row.provider))}
                        title="恢复"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#fee2e2] hover:text-[#dc2626] disabled:opacity-30"
                      disabled={busy === row.session_id}
                      onClick={() => void withBusy(row, () => destroySandboxSession(row.session_id, row.provider))}
                      title="销毁"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
