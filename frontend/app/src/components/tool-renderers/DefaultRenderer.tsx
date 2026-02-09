import { FileText } from "lucide-react";
import type { ToolRendererProps } from "./types";

export default function DefaultRenderer({ step, expanded }: ToolRendererProps) {
  return (
    <>
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <FileText className="w-3 h-3 text-[#a3a3a3]" />
        <span className="font-medium text-[#525252]">{step.name}</span>
        {step.status === "calling" && <span className="text-[#a3a3a3] animate-pulse-slow">执行中...</span>}
      </div>
      {expanded && (
        <div className="mt-2 space-y-2">
          {step.args !== undefined && (
            <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
              {typeof step.args === "string" ? step.args : JSON.stringify(step.args, null, 2)}
            </pre>
          )}
          {step.result && (
            <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
              {step.result}
            </pre>
          )}
        </div>
      )}
    </>
  );
}
