import type { ThreadSummary } from "../api";

interface ThreadListProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onCreate: () => void;
  onDelete: (threadId: string) => void;
}

function labelForThread(thread: ThreadSummary): string {
  const firstMessage = thread.messages?.[0]?.content?.trim();
  if (firstMessage) {
    return firstMessage.slice(0, 30);
  }
  return thread.thread_id.slice(0, 30);
}

export function ThreadList({ threads, activeThreadId, onSelect, onCreate, onDelete }: ThreadListProps) {
  return (
    <aside className="thread-list">
      <button className="new-chat-btn" onClick={onCreate}>
        + New Chat
      </button>

      <div className="thread-items">
        {threads.map((thread) => {
          const active = thread.thread_id === activeThreadId;
          return (
            <div
              key={thread.thread_id}
              className={`thread-item ${active ? "active" : ""}`}
              onClick={() => onSelect(thread.thread_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  onSelect(thread.thread_id);
                }
              }}
            >
              <span className="thread-label">{labelForThread(thread)}</span>
              <button
                className="thread-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(thread.thread_id);
                }}
                aria-label={`Delete ${thread.thread_id}`}
                title="Delete"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
