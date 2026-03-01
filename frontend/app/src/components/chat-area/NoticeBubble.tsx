import type { NoticeMessage } from "../../api";

interface NoticeBubbleProps {
  entry: NoticeMessage;
}

/**
 * Subtle notice for system-injected messages (steer reminders, task notifications).
 * Visually distinct from user/assistant messages — not prominent.
 */
export function NoticeBubble({ entry }: NoticeBubbleProps) {
  // Strip XML tags for display, show human-readable content
  const displayContent = entry.content
    .replace(/<system-reminder>\n?/g, "")
    .replace(/<\/system-reminder>/g, "")
    .replace(/<task-notification>[\s\S]*?<\/task-notification>/g, (match) => {
      // Extract summary from task notification
      const summary = match.match(/<summary>([\s\S]*?)<\/summary>/)?.[1] ?? "";
      const status = match.match(/<status>([\s\S]*?)<\/status>/)?.[1] ?? "";
      return `[Task ${status}] ${summary}`;
    })
    .trim();

  if (!displayContent) return null;

  return (
    <div className="flex justify-center my-1.5">
      <div className="px-3 py-1 rounded-full bg-gray-100 text-gray-500 text-xs leading-relaxed max-w-lg text-center truncate">
        {displayContent}
      </div>
    </div>
  );
}
