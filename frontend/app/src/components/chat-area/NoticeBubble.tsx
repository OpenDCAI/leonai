import type { NoticeMessage } from "../../api";

interface NoticeBubbleProps {
  entry: NoticeMessage;
  onTaskNoticeClick?: (taskId: string) => void;
}

interface ParsedNotice {
  text: string;
  taskId?: string;
}

/**
 * Subtle notice for system-injected messages (steer reminders, task notifications).
 * Visually distinct from user/assistant messages — not prominent.
 */
export function NoticeBubble({ entry, onTaskNoticeClick }: NoticeBubbleProps) {
  const parsed = parseNoticeContent(entry.content);

  if (!parsed.text) return null;

  const inner = (
    <div className={`px-3 py-1 rounded-full bg-gray-100 text-gray-500 text-xs leading-relaxed max-w-lg text-center truncate ${
      parsed.taskId ? "hover:bg-gray-200 hover:text-gray-700 transition-colors" : ""
    }`}>
      {parsed.text}
    </div>
  );

  return (
    <div className="flex justify-center my-1.5">
      {parsed.taskId && onTaskNoticeClick ? (
        <button onClick={() => onTaskNoticeClick(parsed.taskId!)} className="cursor-pointer">
          {inner}
        </button>
      ) : (
        inner
      )}
    </div>
  );
}

function parseNoticeContent(raw: string): ParsedNotice {
  // Task notification: show concise "description status" with link
  const taskMatch = raw.match(/<task-notification>[\s\S]*?<\/task-notification>/);
  if (taskMatch) {
    const taskId = taskMatch[0].match(/<task-id>([\s\S]*?)<\/task-id>/)?.[1] ?? "";
    const status = taskMatch[0].match(/<status>([\s\S]*?)<\/status>/)?.[1] ?? "";
    const description = taskMatch[0].match(/<description>([\s\S]*?)<\/description>/)?.[1] ?? "";
    const label = description || `Task ${taskId}`;
    return { text: `${label} ${status}`, taskId: taskId || undefined };
  }

  // Steer reminder: extract only the user's original message
  const steerMatch = raw.match(/The user sent a new message while you were working:\n([\s\S]*?)\n\nIMPORTANT:/);
  if (steerMatch) {
    return { text: steerMatch[1].trim() };
  }

  // Fallback: strip all XML tags
  return { text: raw.replace(/<[^>]+>/g, "").trim() };
}
