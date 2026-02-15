import { Activity, RefreshCcw, Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  getDpRunEvents,
  listDpThreadRuns,
  operatorDashboardsOverview,
  operatorSandboxes,
  operatorSearch,
  operatorThreadDiagnostics,
  type DpRun,
  type DpRunEvent,
  type OperatorSandboxSession,
  type OperatorSearchHit,
} from "../api";

type Tab = "overview" | "search" | "sandboxes" | "thread";

function JsonBox({ value }: { value: unknown }) {
  return (
    <pre className="p-3 rounded-xl text-xs overflow-auto max-h-[360px] font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function OperatorConsoleModal({
  isOpen,
  onClose,
  activeThreadId,
}: {
  isOpen: boolean;
  onClose: () => void;
  activeThreadId: string | null;
}) {
  const [tab, setTab] = useState<Tab>("overview");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<unknown>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchHits, setSearchHits] = useState<OperatorSearchHit[]>([]);

  const [sandboxes, setSandboxes] = useState<OperatorSandboxSession[]>([]);

  const [threadRuns, setThreadRuns] = useState<DpRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRunEvents, setSelectedRunEvents] = useState<DpRunEvent[]>([]);
  const [diagnostics, setDiagnostics] = useState<unknown>(null);

  const threadId = activeThreadId;

  useEffect(() => {
    if (!isOpen) return;
    setTab("overview");
    setError(null);
  }, [isOpen]);

  const canFetchThread = Boolean(threadId);

  const selectedRun = useMemo(() => {
    if (!selectedRunId) return null;
    return threadRuns.find((r) => r.run_id === selectedRunId) ?? null;
  }, [selectedRunId, threadRuns]);

  async function refreshOverview() {
    setLoading(true);
    setError(null);
    try {
      const v = await operatorDashboardsOverview({ window_hours: 24, stuck_after_sec: 600 });
      setOverview(v);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function refreshSandboxes() {
    setLoading(true);
    setError(null);
    try {
      const v = await operatorSandboxes({ limit: 50 });
      setSandboxes(v.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function doSearch(q: string) {
    setLoading(true);
    setError(null);
    try {
      const v = await operatorSearch({ q, limit: 50 });
      setSearchHits(v.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function refreshThread() {
    if (!threadId) return;
    setLoading(true);
    setError(null);
    try {
      const [runs, diag] = await Promise.all([
        listDpThreadRuns({ thread_id: threadId, limit: 50, offset: 0 }),
        operatorThreadDiagnostics({ thread_id: threadId }),
      ]);
      setThreadRuns(runs.items);
      setDiagnostics(diag);
      if (!selectedRunId && runs.items.length > 0) {
        setSelectedRunId(runs.items[0].run_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function refreshSelectedRunEvents() {
    if (!selectedRunId) return;
    setLoading(true);
    setError(null);
    try {
      const v = await getDpRunEvents({ run_id: selectedRunId, after_event_id: 0, limit: 200 });
      setSelectedRunEvents(v.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!isOpen) return;
    if (tab === "overview" && overview === null && !loading) void refreshOverview();
    if (tab === "sandboxes" && sandboxes.length === 0 && !loading) void refreshSandboxes();
    if (tab === "thread" && canFetchThread && threadRuns.length === 0 && !loading) void refreshThread();
  }, [isOpen, tab, overview, sandboxes.length, canFetchThread, threadRuns.length, loading]);

  useEffect(() => {
    if (!isOpen) return;
    if (tab !== "thread") return;
    if (!selectedRunId) return;
    void refreshSelectedRunEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, tab, selectedRunId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[130] flex items-start justify-center pt-[10vh]">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-[980px] max-h-[78vh] rounded-2xl overflow-hidden bg-white border border-[#e5e5e5] shadow-xl animate-scale-in">
        <div className="h-12 px-5 flex items-center justify-between border-b border-[#e5e5e5]">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#737373]" />
            <h3 className="text-sm font-semibold text-[#171717]">中台 (Operator)</h3>
            {threadId && (
              <span className="text-[11px] font-mono text-[#a3a3a3]">thread {threadId.slice(0, 12)}</span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#737373] hover:bg-[#f5f5f5] hover:text-[#171717] disabled:opacity-40"
              disabled={loading}
              onClick={() => {
                if (tab === "overview") void refreshOverview();
                if (tab === "sandboxes") void refreshSandboxes();
                if (tab === "thread") void refreshThread();
              }}
              title="刷新"
            >
              <RefreshCcw className="w-4 h-4" />
            </button>
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
              onClick={onClose}
              title="关闭"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="h-10 px-3 flex items-center gap-1.5 border-b border-[#e5e5e5]">
          {(
            [
              ["overview", "概览"],
              ["search", "搜索"],
              ["sandboxes", "沙盒"],
              ["thread", "线程"],
            ] as Array<[Tab, string]>
          ).map(([k, label]) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                tab === k ? "bg-[#f5f5f5] text-[#171717] font-medium" : "text-[#737373] hover:text-[#171717]"
              }`}
            >
              {label}
            </button>
          ))}

          {tab === "search" && (
            <div className="ml-auto flex items-center gap-2">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#e5e5e5] bg-white">
                <Search className="w-4 h-4 text-[#a3a3a3]" />
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索 run_id / thread_id / stderr / error ..."
                  className="w-[360px] text-sm outline-none text-[#171717] placeholder:text-[#a3a3a3]"
                />
              </div>
              <button
                className="px-3 py-1.5 rounded-lg text-xs border border-[#e5e5e5] text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717] disabled:opacity-40"
                disabled={loading || !searchQuery.trim()}
                onClick={() => void doSearch(searchQuery.trim())}
              >
                搜索
              </button>
            </div>
          )}
        </div>

        <div className="p-5 overflow-auto max-h-[calc(78vh-88px)] custom-scrollbar space-y-3">
          {error && <div className="p-3 rounded-xl border border-red-200 bg-red-50 text-red-700 text-sm">{error}</div>}

          {tab === "overview" && <JsonBox value={overview} />}

          {tab === "sandboxes" && (
            <div className="space-y-2">
              {sandboxes.length === 0 && !loading && (
                <p className="text-sm text-[#a3a3a3] text-center py-8">暂无活跃会话</p>
              )}
              {sandboxes.map((s) => (
                <div key={s.chat_session_id} className="p-3 rounded-xl bg-[#fafafa] border border-[#e5e5e5]">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-xs text-[#a3a3a3]">thread</div>
                      <div className="text-sm font-mono truncate text-[#171717]">{s.thread_id}</div>
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs text-[#a3a3a3]">provider</div>
                      <div className="text-sm text-[#171717]">{s.provider_name}</div>
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs text-[#a3a3a3]">observed</div>
                      <div className="text-sm text-[#171717]">{s.observed_state}</div>
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs text-[#a3a3a3]">last cmd</div>
                      <div className="text-sm font-mono text-[#171717] truncate max-w-[260px]">
                        {s.last_command?.command_id
                          ? `${s.last_command.command_id.slice(0, 8)} ${s.last_command.status}`
                          : "(none)"}
                      </div>
                    </div>
                  </div>
                  {s.last_error && <div className="mt-2 text-xs text-red-600 font-mono whitespace-pre-wrap">{s.last_error}</div>}
                </div>
              ))}
            </div>
          )}

          {tab === "search" && (
            <div className="space-y-2">
              {searchHits.length === 0 && !loading && <p className="text-sm text-[#a3a3a3] text-center py-8">暂无结果</p>}
              {searchHits.map((h) => (
                <div key={`${h.type}:${h.id}`} className="p-3 rounded-xl bg-[#fafafa] border border-[#e5e5e5]">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-xs text-[#a3a3a3]">{h.type}</div>
                    <div className="text-xs font-mono text-[#a3a3a3]">{h.updated_at ?? ""}</div>
                  </div>
                  <div className="mt-1 text-sm font-mono text-[#171717] break-all">{h.id}</div>
                  {h.summary && <div className="mt-1 text-xs text-[#525252]">{h.summary}</div>}
                </div>
              ))}
            </div>
          )}

          {tab === "thread" && (
            <>
              {!canFetchThread && <p className="text-sm text-[#a3a3a3] text-center py-8">请先选择一个 thread</p>}
              {canFetchThread && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <div className="text-xs font-medium tracking-wider uppercase text-[#a3a3a3]">Runs</div>
                    {threadRuns.length === 0 && !loading && (
                      <p className="text-sm text-[#a3a3a3] text-center py-8">暂无 run 记录</p>
                    )}
                    {threadRuns.map((r) => (
                      <button
                        key={r.run_id}
                        className={`w-full text-left p-3 rounded-xl border transition-colors ${
                          r.run_id === selectedRunId
                            ? "bg-white border-[#171717]"
                            : "bg-[#fafafa] border-[#e5e5e5] hover:bg-white"
                        }`}
                        onClick={() => setSelectedRunId(r.run_id)}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="text-xs font-mono text-[#171717]">{r.run_id.slice(0, 8)}</div>
                          <div className="text-xs text-[#a3a3a3]">{r.status}</div>
                        </div>
                        <div className="mt-1 text-xs text-[#525252] truncate">{r.input_message}</div>
                        <div className="mt-1 text-[11px] text-[#a3a3a3]">{r.started_at}</div>
                      </button>
                    ))}
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-2">
                      <div className="text-xs font-medium tracking-wider uppercase text-[#a3a3a3]">Diagnostics</div>
                      <JsonBox value={diagnostics} />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-medium tracking-wider uppercase text-[#a3a3a3]">Events</div>
                        <button
                          className="px-2 py-1 rounded-lg text-[11px] border border-[#e5e5e5] text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717] disabled:opacity-40"
                          disabled={loading || !selectedRunId}
                          onClick={() => void refreshSelectedRunEvents()}
                        >
                          刷新
                        </button>
                      </div>
                      {selectedRunId && selectedRun && (
                        <div className="text-[11px] font-mono text-[#a3a3a3]">run {selectedRun.run_id}</div>
                      )}
                      <JsonBox value={selectedRunEvents} />
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

