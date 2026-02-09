import { Server, X } from "lucide-react";
import type { SandboxType } from "../api";

interface NewThreadModalProps {
  open: boolean;
  sandboxTypes: SandboxType[];
  onClose: () => void;
  onCreate: (sandboxName: string) => void;
}

const sandboxLabels: Record<string, { label: string; desc: string }> = {
  local: { label: "本地", desc: "在本机运行，适合本地项目开发" },
  agentbay: { label: "AgentBay", desc: "云端沙箱环境，安全隔离" },
  daytona: { label: "Daytona", desc: "云端开发环境，开箱即用" },
  docker: { label: "Docker", desc: "容器化隔离环境，可复现" },
  e2b: { label: "E2B", desc: "云端代码沙箱，快速启动" },
};

export default function NewThreadModal({ open, sandboxTypes, onClose, onCreate }: NewThreadModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-[400px] rounded-2xl bg-white border border-[#e5e5e5] shadow-xl animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e5e5]">
          <h2 className="text-base font-semibold text-[#171717]">新建会话</h2>
          <button
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm mb-3 text-[#737373]">选择运行环境</p>
          <div className="space-y-2">
            {sandboxTypes.map((item) => {
              const info = sandboxLabels[item.name] ?? { label: item.name, desc: "" };
              return (
                <button
                  key={item.name}
                  disabled={!item.available}
                  className={`w-full text-left px-4 py-3 rounded-xl border border-[#e5e5e5] transition-all ${
                    item.available
                      ? "hover:border-[#d4d4d4] hover:bg-[#fafafa] hover:shadow-sm"
                      : "opacity-30 cursor-not-allowed"
                  }`}
                  onClick={() => onCreate(item.name)}
                >
                  <div className="flex items-center gap-3">
                    <Server className="w-4 h-4 flex-shrink-0 text-[#737373]" />
                    <div>
                      <div className="text-sm font-medium text-[#171717]">{info.label}</div>
                      <div className="text-xs text-[#a3a3a3]">
                        {info.desc}{!item.available ? " (不可用)" : ""}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
