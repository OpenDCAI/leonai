import { MoreHorizontal, Plus, Search, Trash2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import type { ThreadSummary } from "../api";
import { useAppStore } from "../store/app-store";
import { Skeleton } from "./ui/skeleton";

interface SidebarProps {
  threads: ThreadSummary[];
  collapsed?: boolean;
  loading?: boolean;
  width?: number;
  onDeleteThread: (threadId: string) => void;
  onSearchClick: () => void;
}

function ThreadSkeleton() {
  return (
    <div className="space-y-0.5">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="px-3 py-2.5 rounded-lg" style={{ animationDelay: `${i * 0.08}s` }}>
          <Skeleton className="h-4 w-[70%] mb-1.5" />
          <Skeleton className="h-3 w-[40%]" />
        </div>
      ))}
    </div>
  );
}

export default function Sidebar({
  threads,
  collapsed = false,
  loading = false,
  width = 272,
  onDeleteThread,
  onSearchClick,
}: SidebarProps) {
  const { threadId } = useParams<{ threadId?: string }>();
  const activeThreadId = threadId || null;
  const memberList = useAppStore(s => s.memberList);
  const memberNameMap = new Map(memberList.map(m => [m.id, m.name]));
  if (collapsed) {
    return (
      <div className="w-14 h-full flex flex-col items-center py-4 bg-card border-r border-border animate-slide-in">
        <Link
          to="/members"
          className="w-9 h-9 rounded-lg flex items-center justify-center mb-2 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Plus className="w-4.5 h-4.5" />
        </Link>
        <button
          className="w-9 h-9 rounded-lg flex items-center justify-center mb-2 text-muted-foreground hover:bg-muted hover:text-foreground"
          onClick={onSearchClick}
        >
          <Search className="w-4.5 h-4.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-card border-r border-border animate-slide-in flex-shrink-0" style={{ width }}>
      {/* Header */}
      <div className="px-4 pt-3 pb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-foreground">消息</span>
      </div>

      {/* Actions */}
      <div className="px-3 pb-3 space-y-2">
        <Link
          to="/members"
          className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm border border-border text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Plus className="w-4 h-4" />
          <span>发起会话</span>
        </Link>
        <button
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground/60 hover:bg-muted hover:text-foreground"
          onClick={onSearchClick}
        >
          <Search className="w-4 h-4" />
          <span>搜索对话...</span>
        </button>
      </div>

      {/* Divider */}
      <div className="h-px mx-3 bg-border" />

      {/* Thread list */}
      <div className="flex-1 min-h-0 px-3 pt-3 flex flex-col">
        <div className="flex items-center justify-between px-2 mb-2 flex-shrink-0">
          <span className="text-[11px] font-medium tracking-wider uppercase text-muted-foreground/60">对话</span>
          <span className="text-[11px] text-muted-foreground/40">{threads.length}</span>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto space-y-0.5 custom-scrollbar">
          {loading ? (
            <ThreadSkeleton />
          ) : (
            <>
              {threads.map((thread) => {
                const isActive = activeThreadId === thread.thread_id;
                return (
                  <div key={thread.thread_id} className="group relative">
                    <Link
                      to={`/chat/${thread.thread_id}`}
                      className={`block w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                        isActive
                          ? "bg-background border-l-2 border-l-foreground shadow-sm"
                          : "border-l-2 border-l-transparent hover:bg-muted"
                      }`}
                    >
                      <div className={`flex items-center gap-1.5 ${isActive ? "text-foreground font-medium" : "text-foreground"}`}>
                        {thread.running && (
                          <span className="w-3 h-3 rounded-full border-2 border-muted-foreground border-t-foreground animate-spin flex-shrink-0" />
                        )}
                        <span className="text-sm font-medium truncate">
                          {thread.agent ? (memberNameMap.get(thread.agent) || thread.agent) : "Leon"}
                        </span>
                      </div>
                      <div className="text-[11px] mt-0.5 text-muted-foreground/60 truncate">
                        {thread.preview || thread.thread_id.slice(0, 14)}
                      </div>
                    </Link>
                    <div className="absolute right-2 top-2.5 hidden group-hover:flex items-center gap-0.5">
                      <button
                        className="w-6 h-6 rounded flex items-center justify-center text-muted-foreground/60 hover:bg-muted hover:text-foreground"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                        title="详情"
                      >
                        <MoreHorizontal className="w-3.5 h-3.5" />
                      </button>
                      <button
                        className="w-6 h-6 rounded flex items-center justify-center text-muted-foreground/60 hover:bg-destructive/10 hover:text-destructive"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          onDeleteThread(thread.thread_id);
                        }}
                        title="删除"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
              {threads.length === 0 && (
                <p className="text-xs px-3 py-6 text-center text-muted-foreground/60">
                  暂无对话，点击"发起会话"开始。
                </p>
              )}
            </>
          )}
        </div>
      </div>

    </div>
  );
}
