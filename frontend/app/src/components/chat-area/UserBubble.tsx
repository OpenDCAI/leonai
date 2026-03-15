import { memo } from "react";
import { useParams } from "react-router-dom";
import { FileText } from "lucide-react";
import type { UserMessage } from "../../api";
import { getWorkspaceDownloadUrl } from "../../api";
import { formatTime } from "./utils";

export const UserBubble = memo(function UserBubble({ entry }: { entry: UserMessage }) {
  const { threadId } = useParams<{ threadId: string }>();
  const attachments = entry.attachments;

  return (
    <div className="flex justify-end animate-fade-in">
      <div className="max-w-[78%]">
        {attachments && attachments.length > 0 && threadId && (
          <div className="mb-1.5 flex flex-wrap gap-1.5 justify-end">
            {attachments.map((filename) => (
              <a
                key={filename}
                href={getWorkspaceDownloadUrl(threadId, filename)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[#f0f0f0] hover:bg-[#e8e8e8] rounded-lg text-xs transition-colors cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-[#737373] flex-shrink-0" />
                <span className="text-[#404040] truncate max-w-[180px]">{filename}</span>
              </a>
            ))}
          </div>
        )}
        <div className="rounded-xl rounded-br-sm px-3.5 py-2 bg-[#f5f5f5] border border-[#e5e5e5]">
          <p className="text-[13px] whitespace-pre-wrap leading-[1.55] text-[#171717]">
            {entry.content}
          </p>
        </div>
        {entry.timestamp && (
          <div className="text-[10px] text-right mt-1 pr-1 text-[#d4d4d4]">
            {formatTime(entry.timestamp)}
          </div>
        )}
      </div>
    </div>
  );
});
