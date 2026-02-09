import { Copy, PanelLeft, Pause, Play, Server, Share2 } from "lucide-react";
import type { SandboxInfo } from "../api";

interface HeaderProps {
  activeThreadId: string | null;
  sandboxInfo: SandboxInfo | null;
  onToggleSidebar: () => void;
  onToggleComputer: () => void;
  onOpenSandboxSessions: () => void;
  onPauseSandbox: () => void;
  onResumeSandbox: () => void;
  computerOpen: boolean;
}

export default function Header({
  activeThreadId,
  sandboxInfo,
  onToggleSidebar,
  onToggleComputer,
  onOpenSandboxSessions,
  onPauseSandbox,
  onResumeSandbox,
  computerOpen,
}: HeaderProps) {
  const status = sandboxInfo?.status ?? null;

  return (
    <header className="h-12 bg-[#1a1a1a] border-b border-[#333] flex items-center justify-between px-4 flex-shrink-0">
      <div className="flex items-center gap-2">
        <button onClick={onToggleSidebar} className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <PanelLeft className="w-4 h-4 text-gray-400" />
        </button>
        <div className="px-2 py-1 rounded-lg bg-[#242424] border border-[#333]">
          <div className="text-[11px] text-gray-500">Thread</div>
          <div className="text-sm text-gray-200 font-mono">{activeThreadId ? `${activeThreadId.slice(0, 14)}...` : "none"}</div>
        </div>
        <div className="px-2 py-1 rounded-lg bg-[#242424] border border-[#333]">
          <div className="text-[11px] text-gray-500">Sandbox</div>
          <div className="text-sm text-gray-200">{sandboxInfo?.type ?? "local"}</div>
        </div>
        {status && (
          <span className={`px-2 py-1 rounded text-xs ${sandboxInfo?.status === "running" ? "bg-green-900/40 text-green-400" : "bg-yellow-900/40 text-yellow-400"}`}>
            {sandboxInfo?.status ?? "unknown"}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {status === "running" && (
          <button className="px-3 py-1.5 rounded-lg bg-[#2a2a2a] hover:bg-[#373737] text-gray-200 text-xs flex items-center gap-2" onClick={onPauseSandbox}>
            <Pause className="w-3.5 h-3.5" />
            Pause
          </button>
        )}
        {status === "paused" && (
          <button className="px-3 py-1.5 rounded-lg bg-[#2a2a2a] hover:bg-[#373737] text-gray-200 text-xs flex items-center gap-2" onClick={onResumeSandbox}>
            <Play className="w-3.5 h-3.5" />
            Resume
          </button>
        )}
        <button className="px-3 py-1.5 rounded-lg bg-[#2a2a2a] hover:bg-[#373737] text-gray-200 text-xs flex items-center gap-2" onClick={onOpenSandboxSessions}>
          <Server className="w-3.5 h-3.5" />
          Sessions
        </button>
        <button className="w-8 h-8 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center transition-colors">
          <Share2 className="w-4 h-4 text-gray-400" />
        </button>
        <button
          onClick={onToggleComputer}
          className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${computerOpen ? "bg-blue-600 text-white" : "hover:bg-[#2a2a2a] text-gray-400"}`}
        >
          <Copy className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
