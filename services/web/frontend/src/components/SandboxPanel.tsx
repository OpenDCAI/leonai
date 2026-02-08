import { useEffect, useState } from "react";
import {
  destroySession, listSandboxSessions, pauseSession, resumeSession,
  getSessionMetrics, type SandboxSession, type SandboxMetrics,
} from "../api";

interface SandboxPanelProps {
  onClose: () => void;
}

export function SandboxPanel({ onClose }: SandboxPanelProps) {
  const [sessions, setSessions] = useState<SandboxSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<Record<string, SandboxMetrics | null>>({});
  const [busy, setBusy] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const list = await listSandboxSessions();
      setSessions(list);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function handlePause(sid: string) {
    setBusy(sid);
    try {
      await pauseSession(sid);
      await refresh();
    } finally { setBusy(null); }
  }

  async function handleResume(sid: string) {
    setBusy(sid);
    try {
      await resumeSession(sid);
      await refresh();
    } finally { setBusy(null); }
  }

  async function handleDestroy(sid: string) {
    setBusy(sid);
    try {
      await destroySession(sid);
      await refresh();
    } finally { setBusy(null); }
  }
// PLACEHOLDER_METRICS

  async function handleMetrics(sid: string) {
    try {
      const res = await getSessionMetrics(sid);
      setMetrics((prev) => ({ ...prev, [sid]: res.metrics }));
    } catch {
      setMetrics((prev) => ({ ...prev, [sid]: null }));
    }
  }

  return (
    <div className="sandbox-panel-overlay" onClick={onClose}>
      <div className="sandbox-panel" onClick={(e) => e.stopPropagation()}>
        <div className="sandbox-panel-header">
          <h2>Sandbox Sessions</h2>
          <div>
            <button className="sandbox-btn" onClick={() => void refresh()} disabled={loading}>
              Refresh
            </button>
            <button className="sandbox-btn close-btn" onClick={onClose}>&times;</button>
          </div>
        </div>

        {loading && <p className="sandbox-loading">Loading sessions...</p>}

        {!loading && sessions.length === 0 && (
          <p className="sandbox-empty">No active sandbox sessions.</p>
        )}

        {!loading && sessions.length > 0 && (
          <table className="sandbox-table">
            <thead>
              <tr>
                <th>Session ID</th>
                <th>Provider</th>
                <th>Status</th>
                <th>Thread</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_id}>
                  <td className="mono">{s.session_id.slice(0, 12)}</td>
                  <td><span className={`sandbox-badge ${s.provider}`}>{s.provider}</span></td>
                  <td><span className={`sandbox-status ${s.status}`}>{s.status}</span></td>
                  <td className="mono">{s.thread_id.slice(0, 12)}</td>
                  <td className="sandbox-actions">
                    {s.status === "running" && (
                      <button disabled={busy === s.session_id} onClick={() => void handlePause(s.session_id)}>
                        Pause
                      </button>
                    )}
                    {s.status === "paused" && (
                      <button disabled={busy === s.session_id} onClick={() => void handleResume(s.session_id)}>
                        Resume
                      </button>
                    )}
                    <button disabled={busy === s.session_id} onClick={() => void handleDestroy(s.session_id)}>
                      Destroy
                    </button>
                    <button onClick={() => void handleMetrics(s.session_id)}>
                      Metrics
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {Object.entries(metrics).map(([sid, m]) => (
          m && (
            <div key={sid} className="metrics-card">
              <h4>Metrics: {sid.slice(0, 12)}</h4>
              <div className="metrics-grid">
                <span>CPU: {m.cpu_percent.toFixed(1)}%</span>
                <span>Mem: {m.memory_used_mb.toFixed(0)} / {m.memory_total_mb.toFixed(0)} MB</span>
                <span>Disk: {m.disk_used_gb.toFixed(1)} / {m.disk_total_gb.toFixed(1)} GB</span>
                <span>Net: {m.network_rx_kbps.toFixed(0)} / {m.network_tx_kbps.toFixed(0)} kbps</span>
              </div>
            </div>
          )
        ))}
      </div>
    </div>
  );
}
