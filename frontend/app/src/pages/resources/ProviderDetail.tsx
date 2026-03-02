import { Monitor, Cloud, Container, Lock, Settings, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { AllocatedResource, ProviderInfo } from "./types";
import ResourceAllocation from "./ResourceAllocation";

const typeIcon = {
  local: Monitor,
  cloud: Cloud,
  container: Container,
} as const;

const typeLabel = {
  local: "本地",
  cloud: "云端",
  container: "容器",
} as const;

const statusLabel = {
  active: "活跃",
  ready: "就绪",
  unavailable: "未就绪",
} as const;

interface ProviderDetailProps {
  provider: ProviderInfo;
  allocatedResources: AllocatedResource[];
}

export default function ProviderDetail({ provider, allocatedResources }: ProviderDetailProps) {
  const { name, description, vendor, type, status, unavailableReason, sessions, quota, latencyMs } = provider;
  const TypeIcon = typeIcon[type];
  const runningSessions = sessions.filter((s) => s.status === "running");

  // Unavailable state
  if (status === "unavailable") {
    return (
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-muted/20">
          <div className="flex items-center gap-3">
            <TypeIcon className="w-4 h-4 text-muted-foreground" />
            <div>
              <h3 className="text-sm font-semibold text-foreground">{name}</h3>
              <p className="text-[11px] text-muted-foreground">{description}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-muted-foreground">{typeLabel[type]}</span>
            <span className="text-[11px] text-muted-foreground">·</span>
            <span className="text-[11px] text-muted-foreground">{statusLabel[status]}</span>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-12 px-6">
          <Lock className="w-8 h-8 text-muted-foreground/40 mb-3" />
          <p className="text-sm text-muted-foreground mb-1">{unavailableReason}</p>
          <p className="text-xs text-muted-foreground mb-4">
            前往 设置 &gt; 沙箱 配置 {name} 环境
          </p>
          <Link
            to="/settings"
            className="inline-flex items-center gap-1.5 text-xs text-foreground hover:text-primary transition-colors border border-border rounded-lg px-3 py-1.5"
          >
            <Settings className="w-3 h-3" />
            前往设置
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    );
  }

  // Local special state
  if (type === "local") {
    return (
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-muted/20">
          <div className="flex items-center gap-3">
            <TypeIcon className="w-4 h-4 text-muted-foreground" />
            <div>
              <h3 className="text-sm font-semibold text-foreground">{name}</h3>
              <p className="text-[11px] text-muted-foreground">{description}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-muted-foreground">{typeLabel[type]}</span>
            <span className="text-[11px] text-muted-foreground">·</span>
            <span className="text-[11px] text-success">常驻</span>
          </div>
        </div>
        <div className="p-5">
          <div className="rounded-lg border border-border/60 bg-muted/15 p-5">
            <div className="text-center mb-4">
              <span className="text-3xl font-mono font-bold text-foreground">&infin;</span>
              <p className="text-xs text-muted-foreground mt-1">无限制</p>
            </div>
            <div className="space-y-1.5 text-xs text-muted-foreground">
              <p>本地沙箱直接运行在宿主机上</p>
              <p>· 无配额限制</p>
              <p>· 无指标监控</p>
              <p>· 会话与进程生命周期绑定</p>
            </div>
            <div className="mt-4 pt-3 border-t border-border/60">
              <div className="mb-2">
                <span className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                  资源分配
                </span>
              </div>
              <ResourceAllocation resources={allocatedResources} providerId={provider.id} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Normal cloud/container provider
  return (
    <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-muted/20">
        <div className="flex items-center gap-3">
          <TypeIcon className="w-4 h-4 text-muted-foreground" />
          <div>
            <h3 className="text-sm font-semibold text-foreground">{name}</h3>
            <p className="text-[11px] text-muted-foreground">
              {description}
              {vendor && ` · ${vendor}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">{typeLabel[type]}</span>
          <span className="text-[11px] text-muted-foreground">·</span>
          <span className={`text-[11px] ${status === "active" ? "text-success" : "text-muted-foreground"}`}>
            {statusLabel[status]}
          </span>
        </div>
      </div>

      {/* Stats grid */}
      <div className="p-5">
        <div className="mb-1">
          <span className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
            概览
          </span>
        </div>
        <div className="grid grid-cols-4 gap-3 mb-5">
          <StatBlock value={String(sessions.length)} label="total" sub="会话" />
          <StatBlock value={String(runningSessions.length)} label="running" sub="运行" />
          <StatBlock
            value={quota ? `${quota.used}` : "-"}
            label="quota"
            sub={quota ? `/${quota.limit}` : ""}
          />
          <StatBlock value={latencyMs != null ? `${latencyMs}ms` : "-"} label="latency" sub="延迟" />
        </div>

        {/* Resource allocation */}
        <div>
          <div className="mb-2">
            <span className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
              资源分配
            </span>
          </div>
          <div className="rounded-lg bg-muted/15 border border-border/40 p-3">
            <ResourceAllocation resources={allocatedResources} providerId={provider.id} />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatBlock({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div className="text-center rounded-lg bg-muted/30 border border-border/40 py-3 px-2">
      <p className="text-2xl font-mono font-bold text-foreground">{value}</p>
      <p className="text-[10px] text-muted-foreground font-mono">{sub}</p>
      <p className="text-[9px] text-muted-foreground/60 uppercase tracking-wider mt-0.5">{label}</p>
    </div>
  );
}
