import { useEffect, useState } from "react";
import type { StreamStatus } from "../../api";

const BOOT_MESSAGES = [
  "正在启动...",
  "加载工具链...",
  "初始化中间件...",
  "即将就绪...",
];

interface ThinkingIndicatorProps {
  runtimeStatus?: StreamStatus | null;
}

export function ThinkingIndicator({ runtimeStatus }: ThinkingIndicatorProps) {
  const isBooting = !runtimeStatus;
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    if (!isBooting) return;
    setMsgIdx(0);
    const interval = setInterval(() => {
      setMsgIdx((prev) => (prev + 1) % BOOT_MESSAGES.length);
    }, 1400);
    return () => clearInterval(interval);
  }, [isBooting]);

  const tool = runtimeStatus?.current_tool;
  const orbClass = isBooting ? "thinking-orb thinking-orb-boot" : "thinking-orb";

  return (
    <div className="flex items-center gap-2 h-5">
      <div className="flex items-center gap-[3px]">
        <span className={orbClass} />
        <span className={orbClass} style={{ animationDelay: "0.14s" }} />
        <span className={orbClass} style={{ animationDelay: "0.28s" }} />
      </div>
      {isBooting ? (
        <span key={msgIdx} className="text-[12px] text-[#737373] animate-fade-in">
          {BOOT_MESSAGES[msgIdx]}
        </span>
      ) : tool ? (
        <span className="text-[12px] text-[#a3a3a3] animate-fade-in">
          使用 {tool}
        </span>
      ) : null}
    </div>
  );
}
