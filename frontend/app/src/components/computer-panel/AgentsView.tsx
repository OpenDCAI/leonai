import { useCallback, useEffect, useRef, useState } from "react";
import type { ToolStep } from "../../api";
import ChatArea from "../ChatArea";
import MarkdownContent from "../MarkdownContent";
import { useThreadData } from "../../hooks/use-thread-data";
import { parseAgentArgs } from "./utils";

type SubagentStream = NonNullable<ToolStep["subagent_stream"]>;

interface AgentsViewProps {
  steps: ToolStep[];
  focusedStepId: string | null;
  onFocusStep: (id: string | null) => void;
}

export function AgentsView({ steps, focusedStepId, onFocusStep }: AgentsViewProps) {
  const [leftWidth, setLeftWidth] = useState(280);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const focused = steps.find((s) => s.id === focusedStepId) ?? null;
  const stream = focused?.subagent_stream;
  const threadId = stream?.thread_id;
  const isRunning = stream?.status === "running";

  // Load sub-agent thread conversation
  const { entries, loading, refreshThread } = useThreadData(threadId);

  // Auto-refresh while sub-agent is running
  useEffect(() => {
    if (!threadId || !isRunning) return;
    const interval = setInterval(() => void refreshThread(), 2000);
    return () => clearInterval(interval);
  }, [threadId, isRunning, refreshThread]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartX.current = e.clientX;
    dragStartWidth.current = leftWidth;
  }, [leftWidth]);

  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - dragStartX.current;
      const newWidth = Math.max(200, Math.min(600, dragStartWidth.current + delta));
      setLeftWidth(newWidth);
    };
    const handleMouseUp = () => setIsDragging(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  if (steps.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
        暂无助手任务
      </div>
    );
  }

  return (
    <div className="h-full flex bg-white">
      {/* Left sidebar - agent list */}
      <div className="flex-shrink-0 border-r border-[#e5e5e5] flex flex-col" style={{ width: `${leftWidth}px` }}>
        <div className="px-3 py-2 border-b border-[#e5e5e5]">
          <div className="text-xs text-[#737373] font-medium">运行中的助手</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {steps.map((step) => (
            <AgentListItem
              key={step.id}
              step={step}
              isSelected={step.id === focusedStepId}
              onClick={() => onFocusStep(step.id)}
            />
          ))}
        </div>
      </div>

      {/* Resizable divider */}
      <div
        className={`w-1 flex-shrink-0 cursor-col-resize hover:bg-blue-400 transition-colors ${
          isDragging ? "bg-blue-500" : "bg-transparent"
        }`}
        onMouseDown={handleMouseDown}
      />

      {/* Right detail */}
      <div className="flex-1 flex flex-col min-w-0">
        {!focused ? (
          <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
            选择一个助手查看详情
          </div>
        ) : (
          <>
            <AgentDetailHeader focused={focused} stream={stream} />
            {threadId ? (
              <ChatArea
                entries={entries}
                isStreaming={!!isRunning}
                runtimeStatus={null}
                loading={loading}
              />
            ) : (
              <AgentFallbackOutput focused={focused} stream={stream} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* -- Agent list item -- */

function AgentListItem({ step, isSelected, onClick }: { step: ToolStep; isSelected: boolean; onClick: () => void }) {
  const args = parseAgentArgs(step.args);
  const agentType = args.subagent_type || "通用助手";
  const prompt = args.prompt || args.description || "";
  const promptPreview = prompt.slice(0, 80) + (prompt.length > 80 ? "..." : "");
  const ss = step.subagent_stream;
  const isRunning = step.status === "calling" && ss?.status === "running";
  const isError = step.status === "error" || ss?.status === "error";
  const statusDot = isRunning ? "bg-green-400 animate-pulse" : isError ? "bg-red-400" : "bg-[#a3a3a3]";

  return (
    <button
      className={`w-full text-left px-3 py-2.5 border-b border-[#f5f5f5] transition-colors ${
        isSelected ? "bg-blue-50" : "hover:bg-[#f5f5f5]"
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot}`} />
        <div className="text-[11px] font-semibold text-[#171717] truncate">{agentType}</div>
      </div>
      {promptPreview && (
        <div className="text-[10px] text-[#737373] line-clamp-3 leading-relaxed">{promptPreview}</div>
      )}
    </button>
  );
}

/* -- Agent detail header -- */

function getStatusLabel(focused: ToolStep, stream: SubagentStream | undefined): string {
  if (stream?.status === "running") return "运行中";
  if (stream?.status === "error") return "出错";
  if (focused.status === "calling") return "启动中";
  return "已完成";
}

function getStatusDotClass(focused: ToolStep, stream: SubagentStream | undefined): string {
  if (stream?.status === "running") return "bg-green-400 animate-pulse";
  if (stream?.status === "error") return "bg-red-400";
  if (focused.status === "calling") return "bg-yellow-400 animate-pulse";
  return "bg-[#a3a3a3]";
}

function AgentDetailHeader({ focused, stream }: { focused: ToolStep; stream: SubagentStream | undefined }) {
  const args = parseAgentArgs(focused.args);
  return (
    <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#e5e5e5] bg-[#fafafa] flex-shrink-0">
      <div className="flex-1">
        <div className="text-sm font-medium text-[#171717]">{args.subagent_type || "通用助手"}</div>
        <div className="text-[10px] text-[#737373] line-clamp-1">{args.prompt || args.description || ""}</div>
      </div>
      <span className={`w-2 h-2 rounded-full ${getStatusDotClass(focused, stream)}`} />
      <span className="text-[10px] text-[#a3a3a3]">{getStatusLabel(focused, stream)}</span>
    </div>
  );
}

/* -- Fallback output (when thread_id is not yet available) -- */

function AgentFallbackOutput({ focused, stream }: { focused: ToolStep; stream: SubagentStream | undefined }) {
  return (
    <div className="flex-1 overflow-y-auto px-4 py-3">
      {stream ? (
        <div className="space-y-3">
          {stream.text && (
            <div className="text-sm text-[#171717]">
              <MarkdownContent content={stream.text} />
            </div>
          )}
          {stream.tool_calls.length > 0 && (
            <div className="space-y-2">
              {stream.tool_calls.map((tc, idx) => (
                <div key={tc.id || idx} className="border-l-2 border-blue-400 pl-3 py-1">
                  <div className="text-[11px] font-medium text-[#525252] font-mono">{tc.name}</div>
                </div>
              ))}
            </div>
          )}
          {stream.error && (
            <div className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{stream.error}</div>
          )}
        </div>
      ) : focused.status === "calling" ? (
        <div className="flex items-center justify-center py-8">
          <span className="text-[11px] text-[#525252]">助手启动中...</span>
        </div>
      ) : focused.result ? (
        <div className="text-sm text-[#171717]">
          <MarkdownContent content={focused.result} />
        </div>
      ) : (
        <div className="text-xs text-[#525252] text-center py-8">(无输出)</div>
      )}
    </div>
  );
}
