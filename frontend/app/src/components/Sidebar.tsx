import { MoreHorizontal, Plus, Search, Server, Sparkles, Trash2 } from "lucide-react";
import type { SandboxType, ThreadSummary } from "../api";

interface SidebarProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  sandboxTypes: SandboxType[];
  selectedSandbox: string;
  collapsed?: boolean;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => void;
  onSelectSandboxType: (value: string) => void;
  onSearchClick: () => void;
}

export default function Sidebar({
  threads,
  activeThreadId,
  sandboxTypes,
  selectedSandbox,
  collapsed = false,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  onSelectSandboxType,
  onSearchClick,
}: SidebarProps) {
  if (collapsed) {
    return (
      <div className="w-14 h-full bg-[#1e1e1e] border-r border-[#333] flex flex-col items-center py-3 animate-slide-in">
        <div className="mb-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        </div>
        <button className="w-10 h-10 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center mb-2 transition-colors" onClick={onCreateThread}>
          <Plus className="w-5 h-5 text-gray-400" />
        </button>
        <button className="w-10 h-10 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center mb-2 transition-colors" onClick={onSearchClick}>
          <Search className="w-5 h-5 text-gray-400" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-[280px] h-full bg-[#1e1e1e] border-r border-[#333] flex flex-col animate-slide-in">
      <div className="px-3 py-3 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <span className="text-white font-medium text-sm">Leon</span>
      </div>

      <div className="px-2 py-2 space-y-2 border-b border-[#333]">
        <div className="flex items-center gap-2">
          <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-[#2a2a2a] text-gray-200 transition-colors text-sm border border-[#333]" onClick={onCreateThread}>
            <Plus className="w-4 h-4" />
            <span>新建会话</span>
          </button>
          <button className="w-10 h-10 rounded-lg hover:bg-[#2a2a2a] flex items-center justify-center text-gray-300" onClick={onSearchClick}>
            <Search className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-2 px-2 py-1 rounded-lg bg-[#232323] border border-[#333]">
          <Server className="w-4 h-4 text-gray-500" />
          <select
            className="w-full bg-transparent text-sm text-gray-200 outline-none"
            value={selectedSandbox}
            onChange={(e) => onSelectSandboxType(e.target.value)}
          >
            {sandboxTypes.map((item) => (
              <option key={item.name} value={item.name} disabled={!item.available}>
                {item.name}{item.available ? "" : " (unavailable)"}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex-1 min-h-0 px-2 py-2">
        <div className="flex items-center justify-between px-3 mb-2">
          <span className="text-xs text-gray-500 font-medium">线程</span>
          <span className="text-xs text-gray-500">{threads.length}</span>
        </div>
        <div className="h-full overflow-y-auto space-y-1">
          {threads.map((thread) => (
            <div key={thread.thread_id} className="group relative">
              <button
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                  activeThreadId === thread.thread_id ? "bg-[#343434] text-white" : "hover:bg-[#2a2a2a] text-gray-300"
                }`}
                onClick={() => onSelectThread(thread.thread_id)}
              >
                <div className="text-xs font-mono">{thread.thread_id.slice(0, 14)}</div>
                <div className="text-[11px] text-gray-500 mt-0.5">{thread.sandbox ?? "local"}</div>
              </button>
              <div className="absolute right-2 top-2 hidden group-hover:flex items-center gap-1">
                <button
                  className="w-6 h-6 rounded hover:bg-[#3a3a3a] flex items-center justify-center text-gray-400"
                  onClick={() => onSelectThread(thread.thread_id)}
                  title="Focus"
                >
                  <MoreHorizontal className="w-3.5 h-3.5" />
                </button>
                <button
                  className="w-6 h-6 rounded hover:bg-[#5a2a2a] flex items-center justify-center text-gray-400 hover:text-red-300"
                  onClick={() => onDeleteThread(thread.thread_id)}
                  title="Delete"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
          {threads.length === 0 && <p className="text-xs text-gray-500 px-3 py-4">暂无线程，点击“新建会话”。</p>}
        </div>
      </div>
    </div>
  );
}
