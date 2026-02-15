import { Activity, Monitor, PanelLeft, Pause, Play, Settings } from "lucide-react";
import { useEffect, useRef, useState } from "react";
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
  queueEnabled: boolean;
  onToggleSidebar: () => void;
  onPauseSandbox: () => void;
  onResumeSandbox: () => void;
  onToggleQueue: () => void;
  onOpenOperator: () => void;
}

export default function Header({
  activeThreadId,
  threadPreview,
  sandboxInfo,
  queueEnabled,
  onToggleSidebar,
  onPauseSandbox,
  onResumeSandbox,
  onToggleQueue,
  onOpenOperator,
}: HeaderProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Close popover on outside click
  useEffect(() => {
    if (!settingsOpen) return;
    const handler = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [settingsOpen]);

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
        <button
          className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-2 border border-[#e5e5e5] text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717]"
          onClick={onOpenOperator}
          title="打开中台"
        >
          <Activity className="w-3.5 h-3.5" />
          中台
        </button>
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

        {/* Settings */}
        <div className="relative" ref={settingsRef}>
          <button
            onClick={() => setSettingsOpen((v) => !v)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[#737373] hover:bg-[#f5f5f5] hover:text-[#171717]"
          >
            <Settings className="w-4 h-4" />
          </button>

          {settingsOpen && (
            <div className="absolute right-0 top-10 w-64 bg-white rounded-xl border border-[#e5e5e5] shadow-lg z-50 py-2">
              <div className="px-4 py-2">
                <div className="text-xs font-medium text-[#a3a3a3] uppercase tracking-wider mb-3">消息设置</div>
                <button
                  onClick={onToggleQueue}
                  className="w-full flex items-center justify-between py-2 group"
                >
                  <div className="text-left">
                    <div className="text-sm text-[#171717]">队列模式</div>
                    <div className="text-[11px] text-[#a3a3a3] mt-0.5">
                      {queueEnabled ? "消息排队，等当前任务完成后执行" : "消息立即插入当前对话"}
                    </div>
                  </div>
                  <div
                    className={`w-9 h-5 rounded-full relative flex-shrink-0 ml-3 transition-all ${
                      queueEnabled ? "bg-amber-400" : "bg-[#d4d4d4]"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all ${
                        queueEnabled ? "left-[18px]" : "left-0.5"
                      }`}
                    />
                  </div>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
