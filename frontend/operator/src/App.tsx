import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  adoptOrphan,
  destroyOrphan,
  destroySession,
  getOrphans,
  getOverview,
  getProviderEvents,
  getRun,
  getRunEvents,
  getThreadCommands,
  getThreadDiagnostics,
  listSandboxes,
  listThreadRuns,
  pauseSession,
  resumeSession,
  search,
} from "./api";
import {
  CodeBlock,
  Collapsible,
  ErrorBox,
  EventItem,
  Spinner,
  StatusBadge,
  TimeAgo,
  truncId,
} from "./components";

export default function App() {
  const [selectedThread, setSelectedThread] = useState<string>("");
  const [showPanel, setShowPanel] = useState(false);

  const openThread = (threadId: string) => {
    setSelectedThread(threadId);
    setShowPanel(true);
  };

  const closePanel = () => {
    setShowPanel(false);
  };

  return (
    <div className="root">
      <header className="header">
        <div className="brand">Leon Operator Console</div>
      </header>
      <main className="main">
        <Dashboard openThread={openThread} />
      </main>

      {/* Slide-out panel for thread inspector */}
      {showPanel && (
        <>
          <div className="overlay" onClick={closePanel} />
          <div className="panel">
            <div className="panelHeader">
              <h2>Thread Inspector</h2>
              <button className="panelClose" onClick={closePanel}>✕</button>
            </div>
            <div className="panelBody">
              <ThreadDetail threadId={selectedThread} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ================================================================
   Main Dashboard
   ================================================================ */

function Dashboard({ openThread }: { openThread: (id: string) => void }) {
  const [overview, setOverview] = useState<any>(null);
  const [sandboxes, setSandboxes] = useState<any>(null);
  const [orphans, setOrphans] = useState<any>(null);
  const [sandboxFilter, setSandboxFilter] = useState<string>("active");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);
  const [err, setErr] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  // @@@stable-refresh - Preserve old data until new data arrives (no flash)
  const loadData = async () => {
    setLoading(true);
    setErr(null);
    try {
      const statusParam = sandboxFilter === "active" ? undefined : sandboxFilter;
      const [ov, sb, orp] = await Promise.all([
        getOverview(),
        listSandboxes(statusParam),
        getOrphans(),
      ]);
      // Only update state after successful fetch
      setOverview(ov);
      setSandboxes(sb);
      setOrphans(orp);
    } catch (e) {
      setErr(e);
      // Keep old data on error - don't clear
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    const interval = setInterval(() => void loadData(), 10000);
    return () => clearInterval(interval);
  }, [sandboxFilter]);

  const onSearch = async () => {
    const q = searchQuery.trim();
    if (!q) return;
    setLoading(true);
    try {
      setSearchResults(await search(q));
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async (threadId: string) => {
    try {
      await pauseSession(threadId);
      await loadData();
    } catch (e) {
      alert(`Failed to pause: ${e}`);
    }
  };

  const handleResume = async (threadId: string) => {
    try {
      await resumeSession(threadId);
      await loadData();
    } catch (e) {
      alert(`Failed to resume: ${e}`);
    }
  };

  const handleDestroy = async (threadId: string) => {
    if (!confirm(`Destroy session for thread ${threadId}?`)) return;
    try {
      await destroySession(threadId);
      await loadData();
    } catch (e) {
      alert(`Failed to destroy: ${e}`);
    }
  };

  const rbs = overview?.runs_by_status ?? {};
  const errorCount = (rbs.error ?? 0) as number;
  const runningCount = (rbs.running ?? 0) as number;
  const doneCount = (rbs.done ?? 0) as number;
  const stuckCount = overview?.stuck_runs?.count ?? 0;
  const sandboxItems = sandboxes?.items ?? [];
  const hasIssues = errorCount > 0 || stuckCount > 0;

  return (
    <>
      {/* System Status Header */}
      <div className="statusBar">
        <div className="statusMain">
          <div className={`statusIndicator ${hasIssues ? "statusIndicator-warn" : "statusIndicator-ok"}`} />
          <div className="statusText">
            {hasIssues ? "System has issues" : "All systems operational"}
          </div>
        </div>
        <div className="statusMeta">
          Last 24h · Auto-refresh: 10s
          {loading && <Spinner />}
          <button onClick={() => void loadData()}>Refresh now</button>
        </div>
      </div>

      {err ? <ErrorBox error={err} /> : null}

      {/* Main Grid Layout */}
      <div className="dashGrid">
        {/* Left Column: System Overview */}
        <div className="dashCol">
          <div className="dashSection">
            <h2>System Overview</h2>

            {/* Run Stats */}
            <div className="statGrid">
              <div className="statBox">
                <div className="statValue">{runningCount}</div>
                <div className="statLabel">Running</div>
              </div>
              <div className="statBox">
                <div className="statValue">{doneCount}</div>
                <div className="statLabel">Completed</div>
              </div>
              {errorCount > 0 && (
                <div className="statBox statBox-danger">
                  <div className="statValue">{errorCount}</div>
                  <div className="statLabel">Errors</div>
                </div>
              )}
              {stuckCount > 0 && (
                <div className="statBox statBox-warn">
                  <div className="statValue">{stuckCount}</div>
                  <div className="statLabel">Stuck</div>
                </div>
              )}
            </div>

            {/* Stuck Runs */}
            {stuckCount > 0 && (
              <div className="issueBox">
                <div className="issueHeader">⚠️ Stuck Runs</div>
                {overview.stuck_runs.items.map((r: any) => (
                  <div key={r.run_id} className="issueItem" onClick={() => openThread(r.thread_id)}>
                    <div className="issueTitle">{r.input_message}</div>
                    <div className="issueMeta">
                      Thread {truncId(r.thread_id)} · <TimeAgo iso={r.started_at} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Top Errors */}
            {overview?.top_errors?.length > 0 && (
              <div className="issueBox">
                <div className="issueHeader">🔴 Recent Errors</div>
                {overview.top_errors.map((e: any, i: number) => (
                  <div key={i} className="issueItem">
                    <div className="issueTitle">{e.error}</div>
                    <div className="issueMeta">
                      {e.count}× · <TimeAgo iso={e.last_seen_at} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Search */}
          <div className="dashSection">
            <h2>Search</h2>
            <div className="searchBox">
              <input
                className="searchInput"
                placeholder="Search by thread_id, run_id, or text..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void onSearch(); }}
              />
              <button onClick={() => void onSearch()}>Search</button>
            </div>
            {searchResults && (
              <div className="searchResults">
                {searchResults.items?.length === 0 ? (
                  <div className="emptyState">No results</div>
                ) : (
                  searchResults.items?.map((item: any, i: number) => (
                    <div key={i} className="searchItem" onClick={() => item.thread_id && openThread(item.thread_id)}>
                      <StatusBadge status={item.type} />
                      <div className="searchItemBody">
                        <div>{item.summary}</div>
                        <div className="searchItemMeta">
                          {item.thread_id && <span>Thread {truncId(item.thread_id)}</span>}
                          {item.updated_at && <TimeAgo iso={item.updated_at} />}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Sandboxes */}
        <div className="dashCol">
          <div className="dashSection">
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>Sandboxes ({sandboxItems.length})</h2>
              <select
                className="filterSelect"
                value={sandboxFilter}
                onChange={(e) => setSandboxFilter(e.target.value)}
              >
                <option value="active">Active only</option>
                <option value="all">All statuses</option>
                <option value="idle">Idle only</option>
                <option value="paused">Paused only</option>
              </select>
            </div>
            {sandboxItems.length === 0 ? (
              <div className="emptyState">No sandboxes</div>
            ) : (
              <table className={`table ${loading ? "table-loading" : ""}`}>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Thread</th>
                    <th>Session</th>
                    <th>Lease</th>
                    <th>Instance</th>
                    <th>Provider</th>
                    <th>State</th>
                    <th>Last Active</th>
                    <th>CWD</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sandboxItems.map((s: any) => {
                    const converged = s.desired_state === s.observed_state;
                    return (
                      <tr key={s.thread_id}>
                        <td><StatusBadge status={s.chat_status} /></td>
                        <td className="tableMono" onClick={() => openThread(s.thread_id)} style={{ cursor: "pointer", textDecoration: "underline" }}>
                          {truncId(s.thread_id)}
                        </td>
                        <td className="tableMono tableDim">{truncId(s.chat_session_id)}</td>
                        <td className="tableMono tableDim">{truncId(s.lease_id)}</td>
                        <td className="tableMono tableDim">{s.instance_id ? truncId(s.instance_id) : "-"}</td>
                        <td>{s.provider_name}</td>
                        <td>
                          <span className={converged ? "stateConverged" : "stateDiverged"}>
                            {s.observed_state}
                            {!converged && ` → ${s.desired_state}`}
                          </span>
                        </td>
                        <td><TimeAgo iso={s.last_active_at} /></td>
                        <td className="tableMono tableDim">{s.cwd}</td>
                        <td>
                          <div style={{ display: "flex", gap: 4 }}>
                            {s.chat_status === "active" && (
                              <button className="btn-xs" onClick={() => handlePause(s.thread_id)}>Pause</button>
                            )}
                            {(s.chat_status === "paused" || s.chat_status === "idle") && (
                              <button className="btn-xs" onClick={() => handleResume(s.thread_id)}>Resume</button>
                            )}
                            <button className="btn-xs btn-danger" onClick={() => handleDestroy(s.thread_id)}>Destroy</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Orphan Resources Panel */}
          {orphans && orphans.count > 0 && (
            <div className="dashSection" style={{ marginTop: 24 }}>
              <h2 style={{ color: "var(--yellow)" }}>⚠️ Orphan Resources ({orphans.count})</h2>
              <p style={{ fontSize: 13, color: "var(--dim)", marginBottom: 12 }}>
                Instances running in providers but not tracked in sandbox.db
              </p>
              <table className="table">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Instance ID</th>
                    <th>State</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {orphans.items.map((o: any) => (
                    <tr key={o.instance_id}>
                      <td>{o.provider}</td>
                      <td className="tableMono">{truncId(o.instance_id)}</td>
                      <td>{o.state || "unknown"}</td>
                      <td>{o.created_at ? <TimeAgo iso={o.created_at} /> : "-"}</td>
                      <td>
                        <button
                          className="btn-sm btn-danger"
                          onClick={async () => {
                            if (confirm(`Destroy orphan ${o.instance_id}?`)) {
                              try {
                                await destroyOrphan(o.instance_id, o.provider);
                                await loadData();
                              } catch (e) {
                                alert(`Failed: ${e}`);
                              }
                            }
                          }}
                        >
                          Destroy
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ================================================================
   Thread Detail Component (in slide-out panel)
   ================================================================ */

function ThreadDetail({ threadId }: { threadId: string }) {
  const [runs, setRuns] = useState<any>(null);
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [run, setRun] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [providerEvents, setProviderEvents] = useState<any>(null);
  const [err, setErr] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [tailing, setTailing] = useState(false);

  const afterIdRef = useRef<number | undefined>(undefined);
  const runIdRef = useRef("");
  const tailTimer = useRef<number | null>(null);
  const eventsEndRef = useRef<HTMLDivElement | null>(null);

  const stopTail = () => {
    setTailing(false);
    if (tailTimer.current) { window.clearInterval(tailTimer.current); tailTimer.current = null; }
  };

  useEffect(() => {
    const loadRuns = async () => {
      setLoading(true);
      setErr(null);
      try {
        setRuns(await listThreadRuns(threadId));
      } catch (e) {
        setErr(e);
      } finally {
        setLoading(false);
      }
    };
    void loadRuns();
    return () => stopTail();
  }, [threadId]);

  // Load provider events for this thread
  useEffect(() => {
    const loadProviderEvents = async () => {
      try {
        setProviderEvents(await getProviderEvents(threadId));
      } catch (e) {
        // Don't set error - provider events are optional
        console.warn("Failed to load provider events:", e);
      }
    };
    void loadProviderEvents();
  }, [threadId]);

  const selectRun = async (rid: string) => {
    stopTail();
    setSelectedRun(rid);
    runIdRef.current = rid;
    setRun(null);
    setEvents([]);
    afterIdRef.current = undefined;
    setLoading(true);
    setErr(null);
    try {
      setRun(await getRun(rid));
      const ev = await getRunEvents(rid);
      const arr = Array.isArray(ev?.items) ? ev.items : Array.isArray(ev) ? ev : [];
      setEvents(arr);
      const lastId = arr.length ? arr[arr.length - 1].event_id ?? arr[arr.length - 1].id : undefined;
      afterIdRef.current = typeof lastId === "number" ? lastId : undefined;
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const startTail = () => {
    const rid = runIdRef.current;
    if (!rid) return;
    if (tailTimer.current) window.clearInterval(tailTimer.current);
    setTailing(true);
    tailTimer.current = window.setInterval(async () => {
      try {
        const ev = await getRunEvents(rid, afterIdRef.current);
        const arr = Array.isArray(ev?.items) ? ev.items : Array.isArray(ev) ? ev : [];
        if (arr.length) {
          setEvents((prev) => [...prev, ...arr]);
          const lastId = arr[arr.length - 1]?.event_id ?? arr[arr.length - 1]?.id;
          if (typeof lastId === "number") afterIdRef.current = lastId;
          requestAnimationFrame(() => eventsEndRef.current?.scrollIntoView({ behavior: "smooth" }));
        }
      } catch (e) {
        stopTail();
        setErr(e);
      }
    }, 1000);
  };

  const runItems = Array.isArray(runs?.items) ? runs.items : Array.isArray(runs) ? runs : [];

  return (
    <>
      <div className="threadId">Thread: {threadId}</div>

      {loading && <Spinner label="Loading" />}
      {err ? <ErrorBox error={err} /> : null}

      {runItems.length > 0 && (
        <>
          <h3>Runs ({runItems.length})</h3>
          <div className="runList">
            {runItems.map((r: any) => {
              const rid = String(r.run_id ?? r.id);
              return (
                <div
                  key={rid}
                  className={`runCard ${selectedRun === rid ? "runCard-active" : ""}`}
                  onClick={() => void selectRun(rid)}
                >
                  <StatusBadge status={r.status} />
                  <span className="runId">{truncId(rid)}</span>
                  <span className="runInput">{r.input_message}</span>
                  {r.started_at && <TimeAgo iso={r.started_at} />}
                </div>
              );
            })}
          </div>
        </>
      )}

      {selectedRun && (
        <div style={{ marginTop: 12 }}>
          <button onClick={() => (tailing ? stopTail() : startTail())}>
            {tailing ? "Stop tail" : "Tail events"}
          </button>
          {tailing && <Spinner label="polling" />}
        </div>
      )}

      {run && (
        <div style={{ marginTop: 16 }}>
          <Collapsible title={`Run ${truncId(selectedRun)} (${run.status})`}>
            <CodeBlock value={run} />
          </Collapsible>
          <h3>Events ({events.length})</h3>
          <div className="timeline">
            {events.map((ev: any, i: number) => (
              <EventItem key={ev.event_id ?? ev.id ?? i} event={ev} />
            ))}
            <div ref={eventsEndRef} />
          </div>
        </div>
      )}

      {providerEvents && providerEvents.count > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Provider Events ({providerEvents.count})</h3>
          <div className="timeline">
            {providerEvents.items.map((ev: any) => (
              <div key={ev.event_id} className="evt evt-provider">
                <div className="evtLabel">
                  <strong>{ev.event_type}</strong> · {ev.provider}
                </div>
                {ev.payload && (
                  <div className="evtPre">{JSON.stringify(JSON.parse(ev.payload), null, 2)}</div>
                )}
                <span className="evtMeta">
                  {ev.instance_id && <span>Instance: {truncId(ev.instance_id)} · </span>}
                  <TimeAgo iso={ev.received_at} />
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
