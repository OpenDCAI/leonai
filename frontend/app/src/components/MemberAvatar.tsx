/**
 * MemberAvatar — unified avatar component for all DOM surfaces.
 * Shows avatar image from /api/members/{id}/avatar with initials fallback.
 * Radix Avatar handles the fallback automatically on 404 or load error.
 */

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

const SIZE_MAP = {
  xs: "w-6 h-6 text-[8px]",
  sm: "w-7 h-7 text-[10px]",
  md: "w-10 h-10 text-xs",
  lg: "w-16 h-16 text-lg",
} as const;

// @@@avatar-colors - rotating background colors for initials fallback
const FALLBACK_COLORS = [
  "bg-blue-100 text-blue-700",
  "bg-green-100 text-green-700",
  "bg-purple-100 text-purple-700",
  "bg-orange-100 text-orange-700",
  "bg-pink-100 text-pink-700",
  "bg-teal-100 text-teal-700",
];

function colorForId(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0;
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}

function getInitials(name: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

interface MemberAvatarProps {
  memberId: string;
  name: string;
  size?: keyof typeof SIZE_MAP;
  className?: string;
}

export default function MemberAvatar({
  memberId,
  name,
  size = "md",
  className,
}: MemberAvatarProps) {
  const sizeClass = SIZE_MAP[size];
  const fallbackColor = colorForId(memberId);

  return (
    <Avatar className={cn(sizeClass, "shrink-0", className)}>
      <AvatarImage
        src={`/api/members/${memberId}/avatar`}
        alt={name}
      />
      <AvatarFallback className={cn("font-semibold", fallbackColor)}>
        {getInitials(name)}
      </AvatarFallback>
    </Avatar>
  );
}
