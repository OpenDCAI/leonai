import { ListOrdered } from "lucide-react";

interface QueueModeToggleProps {
  threadId: string | null;
  queueEnabled: boolean;
  onToggle: () => void;
}

export default function QueueModeToggle({
  threadId,
  queueEnabled,
  onToggle,
}: QueueModeToggleProps) {
  if (!threadId) return null;

  return (
    <button
      onClick={onToggle}
      className={`px-3 py-1.5 rounded-lg text-xs flex items-center gap-2 border transition-all ${
        queueEnabled
          ? "bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100"
          : "border-[#e5e5e5] text-[#525252] hover:bg-[#f5f5f5] hover:text-[#171717]"
      }`}
      title={queueEnabled ? "队列模式：消息排队执行" : "队列模式：消息立即插入"}
    >
      <ListOrdered className="w-3.5 h-3.5" />
      <span>{queueEnabled ? "队列" : "直接"}</span>
    </button>
  );
}
