import { Globe } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { url?: string; query?: string; prompt?: string } {
  if (args && typeof args === "object") return args as { url?: string; query?: string; prompt?: string };
  return {};
}

export default function WebRenderer({ step, expanded }: ToolRendererProps) {
  const { url, query, prompt } = parseArgs(step.args);
  let label = url || query || prompt || "";
  if (url) {
    try { label = new URL(url).hostname; } catch { /* keep raw */ }
  }

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#a3a3a3]">
        <Globe className="w-3 h-3 text-[#d4d4d4] flex-shrink-0" />
        <span className="truncate max-w-[280px]">访问 {label}</span>
        {step.status === "calling" && <span>...</span>}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {step.result && (
        <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
          {step.result}
        </pre>
      )}
    </div>
  );
}
