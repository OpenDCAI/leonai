import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { ResourceSession } from "./types";
import { getAgentColor, getAgentInitials } from "./utils/avatar";
import { calculateDuration, formatDuration } from "./utils/duration";
import { formatMetric } from "./utils/format";

interface SessionListProps {
  sessions: ResourceSession[];
}

const statusLabel: Record<ResourceSession["status"], string> = {
  running: "运行中",
  paused: "已暂停",
  stopped: "已结束",
  destroying: "销毁中",
};

export default function SessionList({ sessions }: SessionListProps) {
  if (sessions.length === 0) {
    return <p className="text-xs text-muted-foreground">暂无会话</p>;
  }

  // Show active sessions first, then stopped
  const sorted = [...sessions].sort((a, b) => {
    const order = { running: 0, destroying: 1, paused: 2, stopped: 3 };
    return (order[a.status] ?? 4) - (order[b.status] ?? 4);
  });

  return (
    <div className="space-y-2">
      {sorted.map((session) => (
        <SessionItem key={session.id} session={session} />
      ))}
    </div>
  );
}

function SessionItem({ session }: { session: ResourceSession }) {
  const duration = session.startedAt ? calculateDuration(session.startedAt) : null;
  const isStopped = session.status === "stopped";
  const hasMetrics =
    session.metrics != null &&
    (session.metrics.cpu != null || session.metrics.memory != null || session.metrics.disk != null);

  return (
    <div className={`rounded-md border border-border/50 bg-card/60 px-3 py-2 ${isStopped ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <StatusDot status={session.status} />
          <Avatar className="w-5 h-5">
            <AvatarFallback className={getAgentColor(session.agentId)}>
              {getAgentInitials(session.agentName)}
            </AvatarFallback>
          </Avatar>
          <span className="text-xs text-foreground font-medium">{session.agentName || "未绑定Agent"}</span>
          <span className="text-[10px] text-muted-foreground font-mono">{shortId(session.threadId)}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {duration != null && (
            <span className="text-[10px] text-muted-foreground">时长 {formatDuration(duration)}</span>
          )}
          <span className="text-[10px] text-muted-foreground">{statusLabel[session.status]}</span>
        </div>
      </div>
      {hasMetrics && (
        <div className="grid grid-cols-3 gap-2 text-[10px] font-mono mt-2">
          <MetricCell label="CPU" value={session.metrics?.cpu} unit="%" />
          <MetricCell label="RAM" value={session.metrics?.memory} unit="GB" />
          <MetricCell label="磁盘" value={session.metrics?.disk} unit="GB" />
        </div>
      )}
    </div>
  );
}

function StatusDot({ status }: { status: ResourceSession["status"] }) {
  const dotClass = {
    running: "bg-success animate-pulse",
    paused: "bg-warning/80",
    stopped: "bg-muted-foreground/40",
    destroying: "bg-destructive animate-pulse",
  }[status];

  return <span className={`h-2 w-2 rounded-full shrink-0 ${dotClass}`} />;
}

function MetricCell({ label, value, unit }: { label: string; value: number | null | undefined; unit: string }) {
  return (
    <div className="rounded border border-border/40 bg-muted/20 px-2 py-1">
      <p className="text-muted-foreground">{label}</p>
      <p className="text-foreground font-semibold">{formatMetric(value, unit)}</p>
    </div>
  );
}

function shortId(raw: string): string {
  if (!raw) return "--";
  return raw.length <= 12 ? raw : `${raw.slice(0, 8)}...`;
}
