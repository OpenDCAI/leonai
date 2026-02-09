import { ExternalLink, Terminal } from "lucide-react";

const sandboxTypeLabels: Record<string, string> = {
  local: "本地",
  agentbay: "AgentBay",
  daytona: "Daytona",
  docker: "Docker",
  e2b: "E2B",
};

interface TaskProgressProps {
  isStreaming: boolean;
  sandboxType: string | null;
  sandboxStatus: string | null;
  onOpenComputer?: () => void;
}

function statusColor(status: string | null): string {
  if (status === "running") return "#22c55e";
  if (status === "paused") return "#eab308";
  if (status === "detached") return "#a3a3a3";
  return "#ef4444";
}

export default function TaskProgress({ isStreaming, sandboxType, sandboxStatus, onOpenComputer }: TaskProgressProps) {
  return (
    <div className="bg-white">
      <div className="max-w-3xl mx-auto px-4">
        <div className="px-2 py-2">
          <div className="w-full flex items-center gap-3 p-2.5 rounded-lg bg-[#fafafa] border border-[#e5e5e5]">
            <div className="w-7 h-7 rounded-lg bg-[#f5f5f5] flex items-center justify-center flex-shrink-0">
              <Terminal className="w-3.5 h-3.5 text-[#737373]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-sm">
                <span className="w-2 h-2 rounded-full" style={{ background: statusColor(sandboxStatus) }} />
                <span className="text-[#171717]">
                  {sandboxTypeLabels[sandboxType ?? "local"] ?? sandboxType ?? "本地"}{" "}
                  {sandboxStatus === "running" ? "运行中" : sandboxStatus === "paused" ? "已暂停" : sandboxStatus === "detached" ? "已断开" : sandboxStatus ?? "未知"}
                </span>
                <span className="text-[#e5e5e5]">&middot;</span>
                <span className={isStreaming ? "text-[#171717] font-medium" : "text-[#a3a3a3]"}>
                  {isStreaming ? "Leon 正在工作" : "Leon 待命中"}
                </span>
              </div>
            </div>
            <button
              onClick={onOpenComputer}
              className="px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-center gap-1.5 border border-[#e5e5e5] text-[#525252] hover:bg-[#f0f0f0] hover:text-[#171717]"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              工作区
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
