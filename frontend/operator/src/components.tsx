import React, { useState } from "react";

/* ---- shared primitives ---- */

export function truncId(id: string, len = 8): string {
  return id.length > len + 3 ? id.slice(0, len) + "\u2026" : id;
}

export function CodeBlock({ value }: { value: unknown }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <pre className="code">
      <code>{text}</code>
    </pre>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner">
      <div className="dot" />
      <div className="dot" />
      <div className="dot" />
      {label ? <span className="spinnerLabel">{label}</span> : null}
    </div>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="error">
      <div className="errorTitle">Error</div>
      <div className="errorMsg">{msg}</div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "running" || status === "active"
      ? "badge-ok"
      : status === "done"
        ? "badge-done"
        : status === "error"
          ? "badge-err"
          : status === "idle" || status === "paused"
            ? "badge-warn"
            : "badge-muted";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export function StatCard({
  label,
  value,
  variant,
}: {
  label: string;
  value: string | number;
  variant?: "accent" | "danger" | "green" | "warn";
}) {
  return (
    <div className={`stat ${variant ? `stat-${variant}` : ""}`}>
      <div className="statValue">{value}</div>
      <div className="statLabel">{label}</div>
    </div>
  );
}

export function TimeAgo({ iso }: { iso: string }) {
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  const text =
    sec < 60
      ? `${sec}s ago`
      : sec < 3600
        ? `${Math.floor(sec / 60)}m ago`
        : sec < 86400
          ? `${Math.floor(sec / 3600)}h ago`
          : `${Math.floor(sec / 86400)}d ago`;
  return (
    <span className="timeago" title={iso}>
      {text}
    </span>
  );
}

export function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="collapsible">
      <button className="collapsibleToggle" onClick={() => setOpen(!open)}>
        <span>{open ? "\u25be" : "\u25b8"}</span> {title}
      </button>
      {open ? <div className="collapsibleBody">{children}</div> : null}
    </div>
  );
}

/** @@@ EventItem - renders a single event with type-specific formatting */
export function EventItem({ event }: { event: any }) {
  const { event_type, payload, created_at, event_id } = event;

  if (event_type === "text" || event_type === "text_full") {
    return (
      <div className="evt evt-text">
        <pre className="evtPre">{payload?.content}</pre>
        <span className="evtMeta">
          #{event_id} <TimeAgo iso={created_at} />
        </span>
      </div>
    );
  }

  if (event_type === "tool_call") {
    return (
      <div className="evt evt-tool">
        <div className="evtLabel">
          tool: <strong>{payload?.name}</strong>
        </div>
        <Collapsible title="args">
          <CodeBlock value={payload?.args} />
        </Collapsible>
        <span className="evtMeta">
          #{event_id} <TimeAgo iso={created_at} />
        </span>
      </div>
    );
  }

  if (event_type === "tool_result") {
    return (
      <div className="evt evt-result">
        <div className="evtLabel">
          result: <strong>{payload?.name}</strong>
        </div>
        <Collapsible title="content">
          <pre className="evtPre">
            {typeof payload?.content === "string" ? payload.content : JSON.stringify(payload?.content, null, 2)}
          </pre>
        </Collapsible>
        <span className="evtMeta">
          #{event_id} <TimeAgo iso={created_at} />
        </span>
      </div>
    );
  }

  if (event_type === "error") {
    return (
      <div className="evt evt-error">
        <div className="evtLabel">error</div>
        <div className="errorMsg">{payload?.error}</div>
        <span className="evtMeta">
          #{event_id} <TimeAgo iso={created_at} />
        </span>
      </div>
    );
  }

  if (event_type === "done" || event_type === "cancelled") {
    return (
      <div className={`evt ${event_type === "done" ? "evt-done" : "evt-cancelled"}`}>
        <div className="evtLabel">{event_type === "done" ? "\u2713 done" : "\u2717 cancelled"}</div>
        <span className="evtMeta">
          #{event_id} <TimeAgo iso={created_at} />
        </span>
      </div>
    );
  }

  if (event_type === "status") {
    return (
      <div className="evt evt-status">
        <Collapsible title={`status #${event_id}`}>
          <CodeBlock value={payload} />
        </Collapsible>
      </div>
    );
  }

  // fallback for unknown event types
  return (
    <div className="evt">
      <div className="evtLabel">{event_type}</div>
      <CodeBlock value={payload} />
      <span className="evtMeta">
        #{event_id} <TimeAgo iso={created_at} />
      </span>
    </div>
  );
}
