import { useEffect, useRef } from "react";
import type { AssistantTurn, ChatEntry, StreamStatus } from "../api";
import { AssistantBlock } from "./chat-area/AssistantBlock";
import { ChatSkeleton } from "./chat-area/ChatSkeleton";
import { UserBubble } from "./chat-area/UserBubble";

interface ChatAreaProps {
  entries: ChatEntry[];
  isStreaming: boolean;
  runtimeStatus: StreamStatus | null;
  loading?: boolean;
  onFocusAgent?: (stepId: string) => void;
}

export default function ChatArea({ entries, isStreaming, runtimeStatus, loading, onFocusAgent }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length, isStreaming]);

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto py-5 bg-white">
        <ChatSkeleton />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto py-5 bg-white">
      <div className="max-w-3xl mx-auto px-5 space-y-3.5">
        {entries.map((entry) => {
          if (entry.role === "user") {
            return <UserBubble key={entry.id} entry={entry} />;
          }
          const assistantEntry = entry as AssistantTurn;
          const isStreamingThis = assistantEntry.streaming === true;
          return (
            <AssistantBlock
              key={entry.id}
              entry={assistantEntry}
              isStreamingThis={isStreamingThis}
              runtimeStatus={isStreamingThis ? runtimeStatus : null}
              onFocusAgent={onFocusAgent}
            />
          );
        })}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
