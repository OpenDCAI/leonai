/**
 * @@@conversation-bubble - top-level conversation message in the brain thread view.
 *
 * Brain thread perspective: agent is "self" (left side).
 * - Incoming (someone → agent): right-aligned with sender avatar
 * - Outgoing (agent → someone): left-aligned with → @recipient [future]
 */
import type { ConversationMessage } from "../../api/types";
import type { MemberInfo } from "../../api/conversations";
import MemberAvatar from "../MemberAvatar";

interface ConversationBubbleProps {
  entry: ConversationMessage;
  agentMember?: MemberInfo;
}

export function ConversationBubble({ entry, agentMember }: ConversationBubbleProps) {
  if (entry.direction === "incoming") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[78%] flex gap-2.5">
          <div>
            <span className="text-[11px] text-muted-foreground text-right mr-0.5 mb-0.5 block">{entry.senderName}</span>
            <div className="rounded-xl rounded-br-sm bg-[#f5f5f5] border border-[#e5e5e5] px-3.5 py-2">
              <p className="text-[13px] whitespace-pre-wrap leading-[1.55] text-[#171717]">
                {entry.content}
              </p>
            </div>
          </div>
          <MemberAvatar memberId={entry.senderId || entry.senderName} name={entry.senderName} type={entry.senderType} size="xs" className="mt-0.5" />
        </div>
      </div>
    );
  }

  // Outgoing (agent → someone) — from logbook_reply. Agent is "self" → left side.
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="max-w-[78%] flex gap-2.5">
        {agentMember && (
          <MemberAvatar memberId={agentMember.id} name={agentMember.name} type={agentMember.type} size="xs" className="mt-0.5" />
        )}
        <div>
          {entry.recipientName && (
            <div className="flex items-center gap-1.5 ml-0.5 mb-0.5">
              <span className="text-[11px] text-muted-foreground">→</span>
              <MemberAvatar memberId={entry.recipientName} name={entry.recipientName} size="xs" />
              <span className="text-[11px] text-muted-foreground">{entry.recipientName}</span>
            </div>
          )}
          <div className="rounded-xl rounded-bl-sm bg-[#f0fdf4] border border-[#bbf7d0] px-3.5 py-2">
            <p className="text-[13px] whitespace-pre-wrap leading-[1.55] text-[#171717]">
              {entry.content}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
