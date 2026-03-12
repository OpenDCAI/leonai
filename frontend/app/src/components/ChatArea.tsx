import type { AssistantTurn, ChatEntry, NoticeMessage, StreamStatus } from "../api";
import { useStickyScroll } from "../hooks/use-sticky-scroll";
import { AssistantBlock } from "./chat-area/AssistantBlock";
import { ChatSkeleton } from "./chat-area/ChatSkeleton";
import { NoticeBubble } from "./chat-area/NoticeBubble";
import { UserBubble } from "./chat-area/UserBubble";

export type ViewMode = "owner" | "contact";

interface ChatAreaProps {
  entries: ChatEntry[];
  isStreaming: boolean;
  runtimeStatus: StreamStatus | null;
  loading?: boolean;
  viewMode?: ViewMode;
  onFocusAgent?: (taskId: string) => void;
  onTaskNoticeClick?: (taskId: string) => void;
}

export default function ChatArea({ entries, isStreaming: _isStreaming, runtimeStatus, loading, viewMode = "owner", onFocusAgent, onTaskNoticeClick }: ChatAreaProps) {
  const containerRef = useStickyScroll<HTMLDivElement>();

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto py-5 bg-white">
      {loading ? (
        <ChatSkeleton />
      ) : (
        <div className="max-w-3xl mx-auto px-5 space-y-3.5">
          {entries.map((entry) => {
            if (entry.role === "notice") {
              // @@@view-mode-filter - hide notices in contact mode
              if (viewMode === "contact") return null;
              return <NoticeBubble key={entry.id} entry={entry as NoticeMessage} onTaskNoticeClick={onTaskNoticeClick} />;
            }
            if (entry.role === "user") {
              return <UserBubble key={entry.id} entry={entry} />;
            }
            const assistantEntry = entry as AssistantTurn;
            const isStreamingThis = assistantEntry.streaming === true;

            // @@@view-mode-filter - in contact mode, only show text segments
            const filteredEntry = viewMode === "contact"
              ? { ...assistantEntry, segments: assistantEntry.segments.filter(s => s.type === "text") }
              : assistantEntry;

            // Skip empty assistant turns in contact mode (e.g. tool-only turns)
            if (viewMode === "contact" && filteredEntry.segments.length === 0 && !isStreamingThis) return null;

            return (
              <AssistantBlock
                key={entry.id}
                entry={filteredEntry}
                isStreamingThis={isStreamingThis}
                runtimeStatus={isStreamingThis ? runtimeStatus : null}
                onFocusAgent={onFocusAgent}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
