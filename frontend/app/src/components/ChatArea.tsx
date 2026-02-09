import { Sparkles, Wrench } from "lucide-react";
import type { ChatMessage } from "../api";

interface ChatAreaProps {
  messages: ChatMessage[];
  isStreaming: boolean;
}

function roleLabel(role: ChatMessage["role"]): string {
  if (role === "assistant") return "Leon";
  if (role === "user") return "You";
  if (role === "tool_call") return "Tool Call";
  return "Tool Result";
}

export default function ChatArea({ messages, isStreaming }: ChatAreaProps) {
  return (
    <div className="flex-1 overflow-y-auto py-6">
      <div className="max-w-3xl mx-auto px-4 space-y-5">
        {messages.map((message) => {
          if (message.role === "user") {
            return (
              <div key={message.id} className="flex justify-end animate-fade-in">
                <div className="max-w-[82%] bg-[#2a2a2a] rounded-2xl px-4 py-2.5">
                  <p className="text-white text-sm whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
            );
          }

          return (
            <div key={message.id} className="flex gap-3 animate-fade-in">
              <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${message.role === "assistant" ? "bg-gradient-to-br from-blue-500 to-cyan-500" : "bg-[#303030]"}`}>
                {message.role === "assistant" ? <Sparkles className="w-3.5 h-3.5 text-white" /> : <Wrench className="w-3.5 h-3.5 text-gray-300" />}
              </div>
              <div className="flex-1 max-w-[calc(100%-40px)]">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-white text-sm font-medium">{roleLabel(message.role)}</span>
                  {message.name && <span className="px-1.5 py-0.5 rounded bg-[#333] text-gray-400 text-xs">{message.name}</span>}
                </div>
                <div className="text-gray-200 text-sm whitespace-pre-wrap break-words">{message.content}</div>
                {message.args !== undefined && (
                  <pre className="mt-2 p-2 rounded bg-[#111] border border-[#2d2d2d] text-xs text-gray-300 overflow-x-auto">
                    {JSON.stringify(message.args, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          );
        })}
        {isStreaming && (
          <div className="flex items-center gap-2 text-gray-400 text-sm animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-blue-500 thinking-dot" />
            <span className="w-2 h-2 rounded-full bg-blue-500 thinking-dot" />
            <span className="w-2 h-2 rounded-full bg-blue-500 thinking-dot" />
            <span className="ml-2">Leon is responding...</span>
          </div>
        )}
        {!isStreaming && messages.length === 0 && <p className="text-sm text-gray-500">Start by sending a message.</p>}
      </div>
    </div>
  );
}
