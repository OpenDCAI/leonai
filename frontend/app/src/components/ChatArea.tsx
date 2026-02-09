import { Check, ChevronDown, ChevronRight, Copy } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { AssistantTurn, ChatEntry, StreamStatus, ToolSegment, UserMessage } from "../api";
import MarkdownContent from "./MarkdownContent";
import { getToolRenderer } from "./tool-renderers";

interface ChatAreaProps {
  entries: ChatEntry[];
  isStreaming: boolean;
  streamTurnId?: string | null;
  runtimeStatus: StreamStatus | null;
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

function UserBubble({ entry }: { entry: UserMessage }) {
  return (
    <div className="flex justify-end animate-fade-in">
      <div className="max-w-[78%]">
        <div className="rounded-2xl rounded-br-md px-4 py-3 bg-[#f5f5f5] border border-[#e5e5e5]">
          <p className="text-sm whitespace-pre-wrap leading-relaxed text-[#171717]">
            {entry.content}
          </p>
        </div>
        {entry.timestamp && (
          <div className="text-[10px] text-right mt-1.5 pr-1 text-[#d4d4d4]">
            {formatTime(entry.timestamp)}
          </div>
        )}
      </div>
    </div>
  );
}

/** Every tool gets the same expandable card — collapsed shows the key info, expand shows details */
function ToolStepBlock({ seg }: { seg: ToolSegment }) {
  const [expanded, setExpanded] = useState(false);
  const Renderer = getToolRenderer(seg.step);
  const isCalling = seg.step.status === "calling";

  return (
    <div
      className={`rounded-lg border bg-white animate-fade-in ${
        isCalling ? "tool-card-calling border-[#d4d4d4]" : "border-[#e5e5e5]"
      }`}
    >
      <button
        className="flex items-center gap-1.5 w-full text-left px-3 py-2 hover:bg-[#fafafa] rounded-lg transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-[#a3a3a3] flex-shrink-0" />
        )}
        <div className={`flex-1 min-w-0 ${isCalling ? "tool-shimmer" : ""}`}>
          <Renderer step={seg.step} expanded={false} />
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 pt-0 animate-scale-in">
          <Renderer step={seg.step} expanded={true} />
        </div>
      )}
    </div>
  );
}

function AssistantBlock({ entry, isStreamingThis }: { entry: AssistantTurn; isStreamingThis?: boolean }) {
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
    <div className="flex gap-3.5 animate-fade-in">
      <div className="w-7 h-7 rounded-full bg-[#171717] flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-xs font-semibold text-white">L</span>
      </div>
      <div className="flex-1 max-w-[calc(100%-44px)] space-y-2">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-[#171717]">Leon</span>
          {entry.timestamp && (
            <span className="text-[10px] text-[#d4d4d4]">{formatTime(entry.timestamp)}</span>
          )}
        </div>

        {entry.segments.map((seg, i) => {
          if (seg.type === "text" && seg.content.trim()) {
            if (isStreamingThis) {
              return (
                <div key={`seg-${i}`} className="text-sm leading-relaxed text-[#404040] whitespace-pre-wrap">
                  {seg.content}
                </div>
              );
            }
            return <MarkdownContent key={`seg-${i}`} content={seg.content} />;
          }
          if (seg.type === "tool") {
            return <ToolStepBlock key={seg.step.id} seg={seg} />;
          }
          return null;
        })}

        {fullText.trim() && (
          <div className="flex justify-start mt-1">
            <CopyButton text={fullText} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatArea({ entries, isStreaming, streamTurnId, runtimeStatus }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, isStreaming]);

  return (
    <div className="flex-1 overflow-y-auto py-8 bg-white">
      <div className="max-w-3xl mx-auto px-6 space-y-6">
        {entries.map((entry) => {
          if (entry.role === "user") {
            return <UserBubble key={entry.id} entry={entry} />;
          }
          return <AssistantBlock key={entry.id} entry={entry} isStreamingThis={isStreaming && entry.id === streamTurnId} />;
        })}

        {isStreaming && (
          <div className="flex items-center gap-3 animate-fade-in">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#171717] thinking-dot" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#171717] thinking-dot" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#171717] thinking-dot" />
            </div>
            <span className="text-sm text-[#a3a3a3]">
              {runtimeStatus?.current_tool
                ? `Leon 正在使用 ${runtimeStatus.current_tool}...`
                : "Leon 正在思考..."}
            </span>
          </div>
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
    </div>
  );
}
