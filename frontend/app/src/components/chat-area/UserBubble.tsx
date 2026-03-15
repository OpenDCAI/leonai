import { memo } from "react";
import type { UserMessage } from "../../api";
import type { MemberInfo } from "../../api/conversations";
import MemberAvatar from "../MemberAvatar";
import { formatTime } from "./utils";

export const UserBubble = memo(function UserBubble({
  entry,
  ownerMember,
}: {
  entry: UserMessage;
  ownerMember?: MemberInfo;
}) {
  return (
    <div className="flex justify-end animate-fade-in">
      <div className="max-w-[78%] flex gap-2.5">
        <div>
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
        {ownerMember && (
          <MemberAvatar memberId={ownerMember.id} name={ownerMember.name} type={ownerMember.type} size="xs" className="mt-0.5" />
        )}
      </div>
    </div>
  );
});
