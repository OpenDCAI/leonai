import { Copy, Monitor, PanelLeft, Pause, Play, Share2 } from "lucide-react";
import type { SandboxInfo } from "../api";

const sandboxTypeLabels: Record<string, string> = {
  local: "本地",
  agentbay: "AgentBay",
  daytona: "Daytona",
  docker: "Docker",
  e2b: "E2B",
};

interface HeaderProps {
  activeThreadId: string | null;
  threadPreview: string | null;
  sandboxInfo: SandboxInfo | null;
  onToggleSidebar: () => void;
  onToggleComputer: () => void;
  onPauseSandbox: () => void;
  onResumeSandbox: () => void;
  computerOpen: boolean;
}

export default function Header({
  activeThreadId,
  threadPreview,
  sandboxInfo,
  onToggleSidebar,
  onToggleComputer,
  onPauseSandbox,
  onResumeSandbox,
  computerOpen,
}: HeaderProps) {
  const hasRemote = sandboxInfo && sandboxInfo.type !== "local";
  const sandboxLabel = sandboxTypeLabels[sandboxInfo?.type ?? "local"] ?? sandboxInfo?.type ?? "本地";
  const hasKnownStatus = sandboxInfo?.status === "running" || sandboxInfo?.status === "paused";
  const statusText = sandboxInfo?.status === "running" ? "运行中" : sandboxInfo?.status === "paused" ? "已暂停" : "";
  const statusDotColor = sandboxInfo?.status === "running"
    ? "#22c55e"
    : sandboxInfo?.status === "paused"
      ? "#eab308"
      : "#a3a3a3";

  return (
    <header className="h-12 flex items-center justify-between px-4 flex-shrink-0 bg-white border-b border-[#e5e5e5]">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-[#737373] hover:bg-[#f5f5f5] hover:text-[#171717]"
        >
          <PanelLeft className="w-4 h-4" />
        </button>

        {/* Context indicator */}
        <div className="flex items-center rounded-lg border border-[#e5e5e5] overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#fafafa]">
            <Monitor className="w-3.5 h-3.5 text-[#a3a3a3]" />
            <span className="text-sm text-[#171717] truncate max-w-[160px]">
              {threadPreview || (activeThreadId ? "新对话" : "无对话")}
            </span>
          </div>
          {hasKnownStatus && (
            <>
              <div className="w-px h-6 bg-[#e5e5e5]" />
              <div className="flex items-center gap-2 px-3 py-1.5 bg-[#fafafa]">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: statusDotColor }} />
                <span className="text-sm text-[#525252]">{sandboxLabel}</span>
                {hasRemote && statusText && (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                    style={{
                      background: sandboxInfo?.status === "running" ? "rgba(34,197,94,0.1)" : "rgba(234,179,8,0.1)",
                      color: sandboxInfo?.status === "running" ? "#16a34a" : "#ca8a04",
                    }}
                  >
                    {statusText}
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        {hasRemote && sandboxInfo?.status === "running" && (
          <button
            className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-2 border border-[#e5e5e5] text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717]"
            onClick={onPauseSandbox}
          >
            <Pause className="w-3.5 h-3.5" />
            暂停
          </button>
        )}
        {hasRemote && sandboxInfo?.status === "paused" && (
          <button
            className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-2 border border-[#e5e5e5] text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717]"
            onClick={onResumeSandbox}
          >
            <Play className="w-3.5 h-3.5" />
            恢复
          </button>
        )}
        <button
          className="w-8 h-8 rounded-lg flex items-center justify-center text-[#737373] hover:bg-[#f5f5f5] hover:text-[#171717]"
          title="分享"
        >
          <Share2 className="w-4 h-4" />
        </button>
        <button
          onClick={onToggleComputer}
          title="工作区"
          className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            computerOpen
              ? "bg-[#171717] text-white"
              : "text-[#737373] hover:bg-[#f5f5f5] hover:text-[#171717]"
          }`}
        >
          <Copy className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
