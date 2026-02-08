import { CheckCircle2, ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { useMemo, useState } from "react";
import type { ChatMessage } from "../api";

interface TaskProgressProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onOpenComputer?: () => void;
}

export default function TaskProgress({ messages, isStreaming, onOpenComputer }: TaskProgressProps) {
  const [expanded, setExpanded] = useState(true);
  const toolCalls = useMemo(() => messages.filter((m) => m.role === "tool_call"), [messages]);
  const toolResults = useMemo(() => messages.filter((m) => m.role === "tool_result"), [messages]);

  return (
    <div className="bg-[#1a1a1a]">
      <div className="max-w-3xl mx-auto px-4">
        <div className="px-2">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="w-full flex items-center gap-3 p-3 rounded-lg bg-[#1e1e1e] border border-[#333] hover:bg-[#252525] transition-colors text-left"
          >
            <div className="w-8 h-8 rounded-lg bg-[#2a2a2a] flex items-center justify-center flex-shrink-0">
              <Terminal className="w-4 h-4 text-gray-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-gray-300 text-sm">{isStreaming ? "Agent 正在执行中..." : "Agent 空闲"}</p>
              <p className="text-gray-500 text-xs mt-0.5">Tool calls: {toolCalls.length}, results: {toolResults.length}</p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
            </div>
          </button>

          {expanded && (
            <div className="mt-2 ml-14 space-y-2 animate-fade-in">
              {toolCalls.slice(-3).map((msg) => (
                <div key={msg.id} className="text-xs text-gray-400 flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                  <span>{msg.name ?? "tool"}</span>
                </div>
              ))}
              <button
                onClick={onOpenComputer}
                className="w-full mt-3 px-3 py-2 rounded-lg bg-[#2a2a2a] hover:bg-[#333] text-gray-300 text-xs transition-colors flex items-center justify-center gap-2"
              >
                <Terminal className="w-3.5 h-3.5" />
                <span>查看计算机 / Workspace</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
