import { MoreHorizontal, Plus, Search, Trash2 } from "lucide-react";
import type { ThreadSummary } from "../api";

interface SidebarProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  collapsed?: boolean;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => void;
  onSearchClick: () => void;
}

export default function Sidebar({
  threads,
  activeThreadId,
  collapsed = false,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  onSearchClick,
}: SidebarProps) {
  if (collapsed) {
    return (
      <div className="w-14 h-full flex flex-col items-center py-4 bg-[#fafafa] border-r border-[#e5e5e5] animate-slide-in">
        <div className="mb-5">
          <div className="w-8 h-8 rounded-lg bg-[#171717] flex items-center justify-center">
            <span className="text-xs font-bold text-white">L</span>
          </div>
        </div>
        <button
          className="w-9 h-9 rounded-lg flex items-center justify-center mb-2 text-[#737373] hover:bg-[#f0f0f0] hover:text-[#171717]"
          onClick={onCreateThread}
        >
          <Plus className="w-4.5 h-4.5" />
        </button>
        <button
          className="w-9 h-9 rounded-lg flex items-center justify-center mb-2 text-[#737373] hover:bg-[#f0f0f0] hover:text-[#171717]"
          onClick={onSearchClick}
        >
          <Search className="w-4.5 h-4.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-[272px] h-full flex flex-col bg-[#fafafa] border-r border-[#e5e5e5] animate-slide-in">
      {/* Brand */}
      <div className="px-4 py-4 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-[#171717] flex items-center justify-center">
          <span className="text-xs font-bold text-white">L</span>
        </div>
        <span className="text-sm font-semibold tracking-tight text-[#171717]">Leon</span>
      </div>

      {/* Actions */}
      <div className="px-3 pb-3">
        <div className="flex items-center gap-2">
          <button
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm border border-[#e5e5e5] text-[#525252] hover:bg-[#f0f0f0] hover:text-[#171717]"
            onClick={onCreateThread}
          >
            <Plus className="w-4 h-4" />
            <span>新建会话</span>
          </button>
          <button
            className="w-9 h-9 rounded-lg flex items-center justify-center text-[#737373] hover:bg-[#f0f0f0] hover:text-[#171717]"
            onClick={onSearchClick}
          >
            <Search className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px mx-3 bg-[#e5e5e5]" />

      {/* Thread list */}
      <div className="flex-1 min-h-0 px-3 pt-3 flex flex-col">
        <div className="flex items-center justify-between px-2 mb-2 flex-shrink-0">
          <span className="text-[11px] font-medium tracking-wider uppercase text-[#a3a3a3]">对话</span>
          <span className="text-[11px] text-[#d4d4d4]">{threads.length}</span>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto space-y-0.5 custom-scrollbar">
          {threads.map((thread) => {
            const isActive = activeThreadId === thread.thread_id;
            return (
              <div key={thread.thread_id} className="group relative">
                <button
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                    isActive
                      ? "bg-white border-l-2 border-l-[#171717] shadow-sm"
                      : "border-l-2 border-l-transparent hover:bg-[#f0f0f0]"
                  }`}
                  onClick={() => onSelectThread(thread.thread_id)}
                >
                  <div className={`text-sm truncate ${isActive ? "text-[#171717] font-medium" : "text-[#525252]"}`}>
                    {thread.preview || thread.thread_id.slice(0, 14)}
                  </div>
                  <div className="text-[11px] mt-0.5 text-[#a3a3a3]">
                    {thread.sandbox ?? "local"}
                  </div>
                </button>
                <div className="absolute right-2 top-2.5 hidden group-hover:flex items-center gap-0.5">
                  <button
                    className="w-6 h-6 rounded flex items-center justify-center text-[#a3a3a3] hover:bg-[#e5e5e5] hover:text-[#525252]"
                    onClick={() => onSelectThread(thread.thread_id)}
                    title="详情"
                  >
                    <MoreHorizontal className="w-3.5 h-3.5" />
                  </button>
                  <button
                    className="w-6 h-6 rounded flex items-center justify-center text-[#a3a3a3] hover:bg-[#fee2e2] hover:text-[#dc2626]"
                    onClick={() => onDeleteThread(thread.thread_id)}
                    title="删除"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
          {threads.length === 0 && (
            <p className="text-xs px-3 py-6 text-center text-[#a3a3a3]">
              暂无对话，点击"新建会话"开始。
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
