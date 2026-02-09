import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import { useState } from "react";
import type { ChatMessage } from "../api";

interface ChatAreaProps {
  messages: ChatMessage[];
  isStreaming: boolean;
}

function formatTime(ts?: number): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function ToolBlock({ message }: { message: ChatMessage }) {
  const [open, setOpen] = useState(false);
  const isCall = message.role === "tool_call";
  return (
    <div className="animate-fade-in">
      <button
        className="flex items-center gap-2 text-xs py-1.5 text-[#737373] hover:text-[#171717] transition-colors group"
        onClick={() => setOpen((v) => !v)}
      >
        <Wrench className="w-3 h-3 text-[#a3a3a3]" />
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <span>
          {isCall ? "工具调用" : "工具结果"}{message.name ? `: ${message.name}` : ""}
        </span>
        {message.timestamp && (
          <span className="ml-1 text-[#d4d4d4]">{formatTime(message.timestamp)}</span>
        )}
      </button>
      {open && (
        <div className="ml-5 mt-1 animate-scale-in">
          {message.content && (
            <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
              {message.content}
            </pre>
          )}
          {message.args !== undefined && (
            <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
              {JSON.stringify(message.args, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChatArea({ messages, isStreaming }: ChatAreaProps) {
  return (
    <div className="flex-1 overflow-y-auto py-8 bg-white">
      <div className="max-w-3xl mx-auto px-6 space-y-6">
        {messages.map((message) => {
          if (message.role === "tool_call" || message.role === "tool_result") {
            return <ToolBlock key={message.id} message={message} />;
          }

          if (message.role === "user") {
            return (
              <div key={message.id} className="flex justify-end animate-fade-in">
                <div className="max-w-[78%]">
                  <div className="rounded-2xl rounded-br-md px-4 py-3 bg-[#f5f5f5] border border-[#e5e5e5]">
                    <p className="text-sm whitespace-pre-wrap leading-relaxed text-[#171717]">
                      {message.content}
                    </p>
                  </div>
                  {message.timestamp && (
                    <div className="text-[10px] text-right mt-1.5 pr-1 text-[#d4d4d4]">
                      {formatTime(message.timestamp)}
                    </div>
                  )}
                </div>
              </div>
            );
          }

          return (
            <div key={message.id} className="flex gap-3.5 animate-fade-in">
              {/* Leon avatar */}
              <div className="w-7 h-7 rounded-full bg-[#171717] flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold text-white">L</span>
              </div>
              <div className="flex-1 max-w-[calc(100%-44px)]">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-sm font-medium text-[#171717]">Leon</span>
                  {message.timestamp && (
                    <span className="text-[10px] text-[#d4d4d4]">{formatTime(message.timestamp)}</span>
                  )}
                </div>
                <div className="text-sm whitespace-pre-wrap break-words leading-relaxed text-[#404040]">
                  {message.content}
                </div>
              </div>
            </div>
          );
        })}

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="flex items-center gap-3 animate-fade-in">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#171717] thinking-dot" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#171717] thinking-dot" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#171717] thinking-dot" />
            </div>
            <span className="text-sm text-[#a3a3a3]">Leon 正在回复...</span>
          </div>
        )}

        {/* Empty state */}
        {!isStreaming && messages.length === 0 && (
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
      </div>
    </div>
  );
}
