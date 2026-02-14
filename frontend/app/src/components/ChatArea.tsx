import { Check, ChevronDown, ChevronRight, Copy } from "lucide-react";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { AssistantTurn, ChatEntry, StreamStatus, ToolSegment, UserMessage } from "../api";
import MarkdownContent from "./MarkdownContent";
import { getToolRenderer } from "./tool-renderers";
import { Skeleton } from "./ui/skeleton";

interface ChatAreaProps {
  entries: ChatEntry[];
  isStreaming: boolean;
  streamTurnId?: string | null;
  runtimeStatus: StreamStatus | null;
  loading?: boolean;
  onFocusAgent?: (stepId: string) => void;
}

function formatTime(ts?: number): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 text-[10px] text-[#a3a3a3] hover:text-[#525252] transition-colors px-1.5 py-0.5 rounded hover:bg-[#f5f5f5]"
      title="复制"
    >
      {copied ? (
        <>
          <Check className="w-3 h-3" />
          <span>已复制</span>
        </>
      ) : (
        <>
          <Copy className="w-3 h-3" />
          <span>复制</span>
        </>
      )}
    </button>
  );
}

const UserBubble = memo(function UserBubble({ entry }: { entry: UserMessage }) {
  return (
    <div className="flex justify-end animate-fade-in">
      <div className="max-w-[78%]">
        <div className="rounded-xl rounded-br-sm px-3.5 py-2 bg-[#f5f5f5] border border-[#e5e5e5]">
          <p className="text-[13px] whitespace-pre-wrap leading-[1.55] text-[#171717]">
            {entry.content}
          </p>
        </div>
        {entry.timestamp && (
          <div className="text-[10px] text-right mt-1 pr-1 text-[#d4d4d4]">
            {formatTime(entry.timestamp)}
          </div>
        )}
      </div>
    </div>
  );
});

/** Every tool gets the same expandable card — collapsed shows the key info, expand shows details */
const TOOL_BADGE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  Bash: { bg: "bg-blue-50", text: "text-blue-600", label: "Bash" },
  run_command: { bg: "bg-blue-50", text: "text-blue-600", label: "Bash" },
  execute_command: { bg: "bg-blue-50", text: "text-blue-600", label: "Bash" },
  Read: { bg: "bg-emerald-50", text: "text-emerald-600", label: "Read" },
  read_file: { bg: "bg-emerald-50", text: "text-emerald-600", label: "Read" },
  Edit: { bg: "bg-amber-50", text: "text-amber-600", label: "Edit" },
  edit_file: { bg: "bg-amber-50", text: "text-amber-600", label: "Edit" },
  Write: { bg: "bg-amber-50", text: "text-amber-600", label: "Write" },
  write_file: { bg: "bg-amber-50", text: "text-amber-600", label: "Write" },
  Grep: { bg: "bg-purple-50", text: "text-purple-600", label: "Grep" },
  Glob: { bg: "bg-purple-50", text: "text-purple-600", label: "Glob" },
  search: { bg: "bg-purple-50", text: "text-purple-600", label: "Search" },
  find_files: { bg: "bg-purple-50", text: "text-purple-600", label: "Search" },
  ListDir: { bg: "bg-emerald-50", text: "text-emerald-600", label: "ListDir" },
  list_directory: { bg: "bg-emerald-50", text: "text-emerald-600", label: "ListDir" },
  list_dir: { bg: "bg-emerald-50", text: "text-emerald-600", label: "ListDir" },
  WebFetch: { bg: "bg-cyan-50", text: "text-cyan-600", label: "Web" },
  web_search: { bg: "bg-cyan-50", text: "text-cyan-600", label: "Web" },
  WebSearch: { bg: "bg-cyan-50", text: "text-cyan-600", label: "Web" },
  Task: { bg: "bg-violet-50", text: "text-violet-600", label: "Task" },
  TaskCreate: { bg: "bg-violet-50", text: "text-violet-600", label: "Task" },
  TaskUpdate: { bg: "bg-violet-50", text: "text-violet-600", label: "Task" },
  TaskList: { bg: "bg-violet-50", text: "text-violet-600", label: "Task" },
  TaskGet: { bg: "bg-violet-50", text: "text-violet-600", label: "Task" },
};

const DEFAULT_BADGE = { bg: "bg-gray-50", text: "text-gray-500", label: "" };

const ToolStepBlock = memo(function ToolStepBlock({ seg, onFocusAgent }: { seg: ToolSegment; onFocusAgent?: (stepId: string) => void }) {
  const isCalling = seg.step.status === "calling";
  const isCancelled = seg.step.status === "cancelled";
  const isWriteTool = seg.step.name === "Write" || seg.step.name === "write_file";

  // Auto-expand write_file when calling, collapse when done
  const [expanded, setExpanded] = useState(isWriteTool && isCalling);

  // Update expanded state when status changes
  useEffect(() => {
    if (isWriteTool) {
      setExpanded(isCalling);
    }
  }, [isWriteTool, isCalling]);

  const Renderer = getToolRenderer(seg.step);
  const badge = TOOL_BADGE_STYLES[seg.step.name] ?? { ...DEFAULT_BADGE, label: seg.step.name };

  // Task (sub-agent) gets a clickable card that opens the Agents panel
  if (seg.step.name === "Task") {
    return (
      <div
        className={`rounded-lg border bg-white animate-fade-in cursor-pointer hover:border-[#a3a3a3] transition-colors ${
          isCalling ? "tool-card-calling border-[#d4d4d4]" : isCancelled ? "border-gray-300 opacity-60" : "border-[#e5e5e5]"
        }`}
        onClick={() => onFocusAgent?.(seg.step.id)}
      >
        <div className="flex items-center gap-1.5 w-full text-left px-2.5 py-1.5">
          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}>
            {badge.label}
          </span>
          <div className={`flex-1 min-w-0 ${isCalling ? "tool-shimmer" : ""}`}>
            <Renderer step={seg.step} expanded={false} />
          </div>
          {isCancelled && (
            <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-[10px] font-medium">已取消</span>
          )}
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0">
            <polyline points="6,3 11,8 6,13" />
          </svg>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg border bg-white animate-fade-in ${
        isCalling ? "tool-card-calling border-[#d4d4d4]" : isCancelled ? "border-gray-300 opacity-60" : "border-[#e5e5e5]"
      }`}
    >
      <button
        className="flex items-center gap-1.5 w-full text-left px-2.5 py-1.5 hover:bg-[#fafafa] rounded-lg transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />
        )}
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${badge.bg} ${badge.text}`}>
          {badge.label}
        </span>
        <div className={`flex-1 min-w-0 ${isCalling ? "tool-shimmer" : ""}`}>
          <Renderer step={seg.step} expanded={false} />
        </div>
        {isCancelled && (
          <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-[10px] font-medium">Cancelled</span>
        )}
      </button>
      {expanded && (
        <div className="px-2.5 pb-2.5 pt-0 animate-scale-in">
          <Renderer step={seg.step} expanded={true} />
          {isCancelled && (
            <div className="text-xs text-gray-500 mt-2 italic">
              {seg.step.result || "任务被用户取消"}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

const AssistantBlock = memo(function AssistantBlock({ entry, isStreamingThis, onFocusAgent }: { entry: AssistantTurn; isStreamingThis?: boolean; onFocusAgent?: (stepId: string) => void }) {
  const fullText = entry.segments
    .filter((s) => s.type === "text")
    .map((s) => s.content)
    .join("\n");

  const hasVisible = entry.segments.some((s) => {
    if (s.type === "text") return s.content.trim().length > 0;
    return s.type === "tool";
  });

  if (!hasVisible) return null;

  return (
    <div className="flex gap-2.5 animate-fade-in">
      <div className="w-6 h-6 rounded-full bg-[#171717] flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-[11px] font-semibold text-white">L</span>
      </div>
      <div className="flex-1 max-w-[calc(100%-36px)] space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-[#171717]">Leon</span>
          {entry.timestamp && (
            <span className="text-[10px] text-[#d4d4d4]">{formatTime(entry.timestamp)}</span>
          )}
        </div>

        {entry.segments.map((seg, i) => {
          if (seg.type === "text" && seg.content.trim()) {
            if (isStreamingThis) {
              return (
                <div key={`seg-${i}`} className="text-[13px] leading-[1.55] text-[#404040] whitespace-pre-wrap">
                  {seg.content}
                </div>
              );
            }
            return <MarkdownContent key={`seg-${i}`} content={seg.content} />;
          }
          if (seg.type === "tool") {
            return <ToolStepBlock key={seg.step.id} seg={seg} onFocusAgent={onFocusAgent} />;
          }
          return null;
        })}

        {!isStreamingThis && fullText.trim() && (
          <div className="flex justify-start mt-0.5">
            <CopyButton text={fullText} />
          </div>
        )}
      </div>
    </div>
  );
});

function ChatSkeleton() {
  return (
    <div className="max-w-3xl mx-auto px-5 space-y-3.5 py-5 animate-fade-in">
      {/* Simulated user message */}
      <div className="flex justify-end">
        <Skeleton className="h-9 w-[45%] rounded-xl" />
      </div>
      {/* Simulated assistant response */}
      <div className="flex gap-2.5">
        <Skeleton className="w-6 h-6 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3.5 w-[20%]" />
          <Skeleton className="h-3.5 w-[90%]" />
          <Skeleton className="h-3.5 w-[75%]" />
          <Skeleton className="h-3.5 w-[60%]" />
        </div>
      </div>
      {/* Simulated user message */}
      <div className="flex justify-end">
        <Skeleton className="h-9 w-[35%] rounded-xl" />
      </div>
      {/* Simulated assistant response */}
      <div className="flex gap-2.5">
        <Skeleton className="w-6 h-6 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3.5 w-[15%]" />
          <Skeleton className="h-3.5 w-[85%]" />
          <Skeleton className="h-3.5 w-[50%]" />
        </div>
      </div>
    </div>
  );
}

export default function ChatArea({ entries, isStreaming, streamTurnId, runtimeStatus, loading, onFocusAgent }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length, isStreaming]);

  return (
    <div className="flex-1 overflow-y-auto py-5 bg-white">
      {loading ? (
        <ChatSkeleton />
      ) : (
      <div className="max-w-3xl mx-auto px-5 space-y-3.5">
        {entries.map((entry) => {
          if (entry.role === "user") {
            return <UserBubble key={entry.id} entry={entry} />;
          }
          return <AssistantBlock key={entry.id} entry={entry} isStreamingThis={isStreaming && entry.id === streamTurnId} onFocusAgent={onFocusAgent} />;
        })}

        {isStreaming && entries.length > 0 && entries[entries.length - 1].role === "assistant" && (
          (() => {
            const lastEntry = entries[entries.length - 1] as AssistantTurn;
            const hasContent = lastEntry.segments?.some(s =>
              (s.type === 'text' && s.content.trim()) || s.type === 'tool'
            );
            if (hasContent) return null;
            return (
              <div className="flex items-center animate-fade-in">
                <span className="text-sm text-[#a3a3a3]">
                  {runtimeStatus?.current_tool
                    ? `Leon 正在使用 ${runtimeStatus.current_tool}...`
                    : "Leon 正在思考..."}
                </span>
              </div>
            );
          })()
        )}

        {!isStreaming && entries.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 animate-fade-in">
            <div className="w-14 h-14 rounded-2xl bg-[#171717] flex items-center justify-center mb-6">
              <span className="text-2xl font-semibold text-white">L</span>
            </div>

            <h2 className="text-xl font-semibold mb-2 text-[#171717]">
              你好，我是 Leon
            </h2>
            <p className="text-sm mb-10 text-[#737373]">
              你的通用数字员工，随时准备为你工作
            </p>

            <div className="grid grid-cols-2 gap-3 max-w-md w-full">
              {[
                { title: "文件操作", desc: "读取、编辑、搜索项目文件" },
                { title: "代码探索", desc: "理解代码结构和实现逻辑" },
                { title: "命令执行", desc: "运行终端命令、Git 操作" },
                { title: "信息检索", desc: "搜索文档和网络资源" },
              ].map((item, i) => (
                <div
                  key={item.title}
                  className="px-4 py-3.5 rounded-xl border border-[#e5e5e5] hover:border-[#d4d4d4] hover:shadow-sm transition-all cursor-default animate-fade-in"
                  style={{ animationDelay: `${i * 0.06}s`, opacity: 0 }}
                >
                  <div className="text-sm font-medium mb-0.5 text-[#171717]">{item.title}</div>
                  <div className="text-xs text-[#737373]">{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
      )}
    </div>
  );
}
