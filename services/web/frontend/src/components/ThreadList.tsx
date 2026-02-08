import { useState } from "react";
import type { SandboxType, ThreadSummary } from "../api";

interface ThreadListProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  sandboxTypes: SandboxType[];
  onSelect: (threadId: string) => void;
  onCreate: (sandboxType: string) => void;
  onDelete: (threadId: string) => void;
  onShowSandboxPanel: () => void;
}

function labelForThread(thread: ThreadSummary): string {
  const firstMessage = thread.messages?.[0]?.content?.trim();
  if (firstMessage) {
    return firstMessage.slice(0, 30);
  }
  return thread.thread_id.slice(0, 16);
}

export function ThreadList({
  threads, activeThreadId, sandboxTypes, onSelect, onCreate, onDelete, onShowSandboxPanel,
}: ThreadListProps) {
  const [showPicker, setShowPicker] = useState(false);

  function handleCreate(type: string) {
    setShowPicker(false);
    void onCreate(type);
  }

  return (
    <aside className="thread-list">
      <div className="thread-list-header">
        <button className="new-chat-btn" onClick={() => setShowPicker((v) => !v)}>
          + New Chat
        </button>
        <button className="sandbox-panel-btn" onClick={onShowSandboxPanel} title="Sandbox Sessions">
          &#9881;
        </button>
      </div>

      {showPicker && (
        <div className="sandbox-picker">
          {sandboxTypes.filter((t) => t.available).map((t) => (
            <button key={t.name} className="sandbox-pick-btn" onClick={() => handleCreate(t.name)}>
              {t.name}
            </button>
          ))}
        </div>
      )}

      <div className="thread-items">
        {threads.map((thread) => {
          const active = thread.thread_id === activeThreadId;
          const sbx = thread.sandbox;
          return (
            <div
              key={thread.thread_id}
              className={`thread-item ${active ? "active" : ""}`}
              onClick={() => onSelect(thread.thread_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelect(thread.thread_id);
              }}
            >
              <div className="thread-item-content">
                <span className="thread-label">{labelForThread(thread)}</span>
                {sbx && sbx !== "local" && (
                  <span className={`sandbox-badge ${sbx}`}>{sbx}</span>
                )}
              </div>
              <button
                className="thread-delete"
                onClick={(e) => { e.stopPropagation(); onDelete(thread.thread_id); }}
                aria-label={`Delete ${thread.thread_id}`}
                title="Delete"
              >
                &times;
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
