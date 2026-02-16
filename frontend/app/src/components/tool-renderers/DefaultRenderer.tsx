import { FileText } from "lucide-react";
import type { ToolRendererProps } from "./types";

export default function DefaultRenderer({ step, expanded }: ToolRendererProps) {
  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#a3a3a3]">
        <FileText className="w-3 h-3 text-[#d4d4d4] flex-shrink-0" />
        <span>{step.name}</span>
        {step.status === "calling" && <span>...</span>}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
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
  );
}
