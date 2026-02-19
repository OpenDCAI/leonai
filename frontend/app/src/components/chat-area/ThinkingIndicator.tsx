import type { StreamStatus } from "../../api";

interface ThinkingIndicatorProps {
  runtimeStatus?: StreamStatus | null;
}

export function ThinkingIndicator({ runtimeStatus }: ThinkingIndicatorProps) {
  const tool = runtimeStatus?.current_tool;

  return (
    <div className="flex items-center gap-2 h-5">
      <div className="flex items-center gap-[3px]">
        <span className="thinking-orb" />
        <span className="thinking-orb" style={{ animationDelay: "0.15s" }} />
        <span className="thinking-orb" style={{ animationDelay: "0.3s" }} />
      </div>
      {tool && (
        <span className="text-[12px] text-[#a3a3a3] animate-fade-in">
          使用 {tool}
        </span>
      )}
    </div>
  );
}
