import type { NoticeMessage } from "../../api";

interface NoticeBubbleProps {
  entry: NoticeMessage;
}

/**
 * Subtle notice for system-injected messages (steer reminders, task notifications).
 * Visually distinct from user/assistant messages — not prominent.
 */
export function NoticeBubble({ entry }: NoticeBubbleProps) {
  const displayContent = parseNoticeContent(entry.content);

  if (!displayContent) return null;

  return (
    <div className="flex justify-center my-1.5">
      <div className="px-3 py-1 rounded-full bg-gray-100 text-gray-500 text-xs leading-relaxed max-w-lg text-center truncate">
        {displayContent}
      </div>
    </div>
  );
}

function parseNoticeContent(raw: string): string {
  // Task notification: show concise "Task {id} {status}"
  const taskMatch = raw.match(/<task-notification>[\s\S]*?<\/task-notification>/);
  if (taskMatch) {
    const taskId = taskMatch[0].match(/<task-id>([\s\S]*?)<\/task-id>/)?.[1] ?? "";
    const status = taskMatch[0].match(/<status>([\s\S]*?)<\/status>/)?.[1] ?? "";
    return `Task ${taskId} ${status}`;
  }

  // Steer reminder: extract only the user's original message
  const steerMatch = raw.match(/The user sent a new message while you were working:\n([\s\S]*?)\n\nIMPORTANT:/);
  if (steerMatch) {
    return steerMatch[1].trim();
  }

  // Fallback: strip all XML tags
  return raw.replace(/<[^>]+>/g, "").trim();
}
