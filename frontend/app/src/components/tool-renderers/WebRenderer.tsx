import { Globe } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { url?: string; query?: string; prompt?: string } {
  if (args && typeof args === "object") return args as { url?: string; query?: string; prompt?: string };
  return {};
}

export default function WebRenderer({ step, expanded }: ToolRendererProps) {
  const { url, query, prompt } = parseArgs(step.args);
  const label = url || query || prompt || "";

  return (
    <>
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <Globe className="w-3 h-3 text-orange-500" />
        <span className="font-medium text-[#525252]">网络请求</span>
        {label && <span className="text-[#a3a3a3] truncate max-w-[240px]">{label}</span>}
        {step.status === "calling" && <span className="text-[#a3a3a3] animate-pulse-slow">请求中...</span>}
      </div>
      {expanded && step.result && (
        <div className="mt-2">
          <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
            {step.result}
          </pre>
        </div>
      )}
    </>
  );
}
