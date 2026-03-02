import { CheckCircle2, XCircle, Clock } from "lucide-react";
import type { NoticeMessage } from "../../api";

interface NoticeBubbleProps {
  entry: NoticeMessage;
  onTaskNoticeClick?: (taskId: string) => void;
}

export interface ParsedNotice {
  text: string;
  status?: "completed" | "error" | "pending";
  taskId?: string;
}

export const STATUS_ICON = {
  completed: <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />,
  error: <XCircle className="w-3 h-3 text-red-400 shrink-0" />,
  pending: <Clock className="w-3 h-3 text-gray-400 shrink-0" />,
} as const;

/**
 * System notice rendered as a divider line — visually distinct from user/assistant messages.
 * Like "xxx joined the chat" in messaging apps.
 */
export function NoticeBubble({ entry, onTaskNoticeClick }: NoticeBubbleProps) {
  const parsed = parseNoticeContent(entry.content);

  if (!parsed.text) return null;

  const icon = parsed.status ? STATUS_ICON[parsed.status] : null;
  const isClickable = !!parsed.taskId && !!onTaskNoticeClick;

  const content = (
    <span className={`inline-flex items-center gap-1.5 px-2.5 text-[11px] text-gray-400 ${
      isClickable ? "hover:text-gray-600 transition-colors cursor-pointer" : ""
    }`}>
      {icon}
      {parsed.text}
    </span>
  );

  return (
    <div className="flex items-center gap-3 my-3 select-none">
      <div className="flex-1 h-px bg-gray-100" />
      {isClickable ? (
        <button onClick={() => onTaskNoticeClick(parsed.taskId!)}>{content}</button>
      ) : (
        content
      )}
      <div className="flex-1 h-px bg-gray-100" />
    </div>
  );
}

function normalizeStatus(raw: string): ParsedNotice["status"] {
  const lower = raw.toLowerCase().trim();
  if (lower === "completed" || lower === "done" || lower === "success") return "completed";
  if (lower === "error" || lower === "failed") return "error";
  return "pending";
}

export function parseNoticeContent(raw: string): ParsedNotice {
  // Task notification: show concise "Task: description 已完成"
  const taskMatch = raw.match(/<task-notification>[\s\S]*?<\/task-notification>/);
  if (taskMatch) {
    const taskId = taskMatch[0].match(/<task-id>([\s\S]*?)<\/task-id>/)?.[1]?.trim() ?? "";
    const statusRaw = taskMatch[0].match(/<status>([\s\S]*?)<\/status>/)?.[1]?.trim() ?? "";
    const description = taskMatch[0].match(/<description>([\s\S]*?)<\/description>/)?.[1]?.trim() ?? "";
    const status = normalizeStatus(statusRaw);
    const label = description || `Task ${taskId}`;
    const statusText = status === "completed" ? "已完成" : status === "error" ? "失败" : statusRaw;
    return { text: `${label} ${statusText}`, status, taskId: taskId || undefined };
  }

  // Steer reminder: extract only the user's original message
  const steerMatch = raw.match(/The user sent a new message while you were working:\n([\s\S]*?)\n\nIMPORTANT:/);
  if (steerMatch) {
    return { text: steerMatch[1].trim() };
  }

  // Fallback: strip all XML tags
  return { text: raw.replace(/<[^>]+>/g, "").trim() };
}
