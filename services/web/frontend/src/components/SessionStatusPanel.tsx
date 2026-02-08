import { useEffect, useState } from "react";
import {
  getThreadSession,
  getThreadTerminal,
  getThreadLease,
  type SessionStatus,
  type TerminalStatus,
  type LeaseStatus,
} from "../api";

interface SessionStatusPanelProps {
  threadId: string;
  sandboxType: string;
}

export function SessionStatusPanel({ threadId, sandboxType }: SessionStatusPanelProps) {
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [terminal, setTerminal] = useState<TerminalStatus | null>(null);
  const [lease, setLease] = useState<LeaseStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  async function refresh() {
    if (sandboxType === "local") return;

    setLoading(true);
    setError(null);
    try {
      const [sessionData, terminalData, leaseData] = await Promise.all([
        getThreadSession(threadId),
        getThreadTerminal(threadId),
        getThreadLease(threadId),
      ]);
      setSession(sessionData);
      setTerminal(terminalData);
      setLease(leaseData);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [threadId, sandboxType]);

  if (sandboxType === "local") {
    return null;
  }

  return (
    <div className="session-status-panel">
      <div className="session-status-header" onClick={() => setExpanded(!expanded)}>
        <h3>Session Status</h3>
        <button className="expand-btn">{expanded ? "▼" : "▶"}</button>
      </div>

      {expanded && (
        <div className="session-status-content">
          {loading && <p className="status-loading">Loading...</p>}
          {error && <p className="status-error">Error: {error}</p>}

          {!loading && !error && session && (
            <>
              <div className="status-section">
                <h4>Chat Session</h4>
                <div className="status-grid">
                  <span className="label">Session ID:</span>
                  <span className="mono">{session.session_id.slice(0, 12)}...</span>

                  <span className="label">Status:</span>
                  <span className={`status-badge ${session.status}`}>{session.status}</span>

                  <span className="label">Created:</span>
                  <span>{new Date(session.created_at).toLocaleString()}</span>

                  <span className="label">Last Active:</span>
                  <span>{new Date(session.last_active_at).toLocaleString()}</span>

                  {session.expires_at && (
                    <>
                      <span className="label">Expires:</span>
                      <span>{new Date(session.expires_at).toLocaleString()}</span>
                    </>
                  )}
                </div>
              </div>

              {terminal && (
                <div className="status-section">
                  <h4>Terminal State</h4>
                  <div className="status-grid">
                    <span className="label">Terminal ID:</span>
                    <span className="mono">{terminal.terminal_id.slice(0, 12)}...</span>

                    <span className="label">CWD:</span>
                    <span className="mono">{terminal.cwd}</span>

                    <span className="label">Version:</span>
                    <span>{terminal.version}</span>

                    <span className="label">Updated:</span>
                    <span>{new Date(terminal.updated_at).toLocaleString()}</span>
                  </div>

                  {Object.keys(terminal.env_delta).length > 0 && (
                    <div className="env-delta">
                      <strong>Environment Variables:</strong>
                      <pre>{JSON.stringify(terminal.env_delta, null, 2)}</pre>
                    </div>
                  )}
                </div>
              )}

              {lease && (
                <div className="status-section">
                  <h4>Sandbox Lease</h4>
                  <div className="status-grid">
                    <span className="label">Lease ID:</span>
                    <span className="mono">{lease.lease_id.slice(0, 12)}...</span>

                    <span className="label">Provider:</span>
                    <span className={`provider-badge ${lease.provider_name}`}>{lease.provider_name}</span>

                    {lease.instance && (
                      <>
                        <span className="label">Instance ID:</span>
                        <span className="mono">{lease.instance.instance_id?.slice(0, 12) || "N/A"}</span>

                        <span className="label">Instance State:</span>
                        <span className={`status-badge ${lease.instance.state}`}>{lease.instance.state || "unknown"}</span>

                        {lease.instance.started_at && (
                          <>
                            <span className="label">Started:</span>
                            <span>{new Date(lease.instance.started_at).toLocaleString()}</span>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}

              <button className="refresh-btn" onClick={() => void refresh()} disabled={loading}>
                Refresh Status
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
