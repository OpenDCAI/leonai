import { FolderOpen, Server, X } from "lucide-react";
import { useState } from "react";
import { pickFolder, type SandboxType } from "../api";

interface NewThreadModalProps {
  open: boolean;
  sandboxTypes: SandboxType[];
  onClose: () => void;
  onCreate: (sandboxName: string, cwd?: string) => void;
}

const KNOWN_LABELS: Record<string, { label: string; desc: string }> = {
  local: { label: "本地", desc: "在本机运行，适合本地项目开发" },
  agentbay: { label: "AgentBay", desc: "云端沙箱环境，安全隔离" },
  daytona: { label: "Daytona", desc: "云端开发环境，开箱即用" },
  docker: { label: "Docker", desc: "容器化隔离环境，可复现" },
  e2b: { label: "E2B", desc: "云端代码沙箱，快速启动" },
};
function sandboxLabel(name: string): { label: string; desc: string } {
  return KNOWN_LABELS[name] ?? { label: name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()), desc: "" };
}

export default function NewThreadModal({ open, sandboxTypes, onClose, onCreate }: NewThreadModalProps) {
  const [localExpanded, setLocalExpanded] = useState(false);
  const [cwdInput, setCwdInput] = useState("");

  if (!open) return null;

  const handleClose = () => {
    setLocalExpanded(false);
    setCwdInput("");
    onClose();
  };

  const handleLocalConfirm = () => {
    const cwd = cwdInput.trim() || undefined;
    handleClose();
    onCreate("local", cwd);
  };

  const handleBrowseFolder = async () => {
    try {
      const path = await pickFolder();
      if (path) {
        setCwdInput(path);
      }
    } catch (err) {
      console.error('Failed to pick folder:', err);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="w-[400px] rounded-2xl bg-white border border-[#e5e5e5] shadow-xl animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e5e5]">
          <h2 className="text-base font-semibold text-[#171717]">新建会话</h2>
          <button
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
            onClick={handleClose}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm mb-3 text-[#737373]">选择运行环境</p>
          <div className="space-y-2">
            {sandboxTypes.map((item) => {
              const info = sandboxLabel(item.name);

              if (item.name === "local") {
                return (
                  <div key="local" className="rounded-xl border border-[#e5e5e5] transition-all overflow-hidden">
                    <button
                      disabled={!item.available}
                      className={`w-full text-left px-4 py-3 transition-all ${
                        item.available
                          ? "hover:bg-[#fafafa]"
                          : "opacity-30 cursor-not-allowed"
                      }`}
                      onClick={() => {
                        if (localExpanded) {
                          handleLocalConfirm();
                        } else {
                          setLocalExpanded(true);
                        }
                      }}
                    >
                      <div className="flex items-center gap-3">
                        <Server className="w-4 h-4 flex-shrink-0 text-[#737373]" />
                        <div className="flex-1">
                          <div className="text-sm font-medium text-[#171717]">{info.label}</div>
                          <div className="text-xs text-[#a3a3a3]">{info.desc}</div>
                        </div>
                      </div>
                    </button>

                    {localExpanded && (
                      <div className="px-4 pb-3 animate-fade-in">
                        <div className="flex items-center gap-2 mt-1">
                          <FolderOpen className="w-4 h-4 text-[#a3a3a3] flex-shrink-0" />
                          <input
                            type="text"
                            value={cwdInput}
                            onChange={(e) => setCwdInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleLocalConfirm();
                            }}
                            placeholder="工作目录，如 ~/projects/my-app"
                            className="flex-1 text-sm px-3 py-1.5 rounded-lg border border-[#e5e5e5] bg-[#fafafa] text-[#171717] placeholder:text-[#d4d4d4] focus:outline-none focus:border-[#a3a3a3] transition-colors"
                            autoFocus
                          />
                          <button
                            className="px-3 py-1.5 text-xs rounded-lg border border-[#e5e5e5] bg-white text-[#525252] hover:bg-[#fafafa] hover:border-[#d4d4d4] transition-colors flex items-center gap-1.5"
                            onClick={handleBrowseFolder}
                            title="选择文件夹"
                          >
                            <FolderOpen className="w-3.5 h-3.5" />
                            浏览
                          </button>
                        </div>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-[10px] text-[#d4d4d4]">留空则使用默认目录</span>
                          <button
                            className="text-xs px-3 py-1 rounded-lg bg-[#171717] text-white hover:bg-[#333] transition-colors"
                            onClick={handleLocalConfirm}
                          >
                            确认
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <button
                  key={item.name}
                  disabled={!item.available}
                  className={`w-full text-left px-4 py-3 rounded-xl border border-[#e5e5e5] transition-all ${
                    item.available
                      ? "hover:border-[#d4d4d4] hover:bg-[#fafafa] hover:shadow-sm"
                      : "opacity-30 cursor-not-allowed"
                  }`}
                  onClick={() => {
                    handleClose();
                    onCreate(item.name);
                  }}
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
