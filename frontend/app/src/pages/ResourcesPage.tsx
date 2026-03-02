import { useMemo, useState } from "react";
import { useIsMobile } from "@/hooks/use-mobile";
import { PROVIDER_REGISTRY, deriveAllocatedResources } from "./resources/fake-data";
import ProviderCard from "./resources/ProviderCard";
import ProviderDetail from "./resources/ProviderDetail";

export default function ResourcesPage() {
  const isMobile = useIsMobile();
  const [selectedId, setSelectedId] = useState<string>("local");

  const selected = PROVIDER_REGISTRY.find((p) => p.id === selectedId)!;
  const activeCount = PROVIDER_REGISTRY.filter((p) => p.status === "active").length;
  const totalSessions = PROVIDER_REGISTRY.reduce((sum, p) => sum + p.sessions.length, 0);
  const allocatedResources = useMemo(() => deriveAllocatedResources(PROVIDER_REGISTRY), []);

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 md:px-6 border-b border-border bg-card/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-foreground">资源</h2>
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
            <span className="inline-flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-slow" />
              {activeCount} 活跃
            </span>
            <span>·</span>
            <span>{totalSessions} 会话</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {/* Provider cards */}
        <div className={`grid gap-3 ${isMobile ? "grid-cols-2" : "grid-cols-5"}`}>
          {PROVIDER_REGISTRY.map((p) => (
            <ProviderCard
              key={p.id}
              provider={p}
              selected={p.id === selectedId}
              onSelect={() => p.status !== "unavailable" && setSelectedId(p.id)}
            />
          ))}
        </div>

        {/* Provider detail */}
        <div key={selectedId} className="animate-fade-in">
          <ProviderDetail provider={selected} allocatedResources={allocatedResources} />
        </div>
      </div>
    </div>
  );
}
