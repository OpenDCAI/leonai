import { TerminalSquare } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { command?: string; description?: string } {
  if (args && typeof args === "object") return args as { command?: string; description?: string };
  return {};
}

export default function RunCommandRenderer({ step, expanded }: ToolRendererProps) {
  const { command, description } = parseArgs(step.args);

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#737373]">
        <TerminalSquare className="w-3 h-3 text-blue-500 flex-shrink-0" />
        <span className="font-medium text-[#525252]">执行命令</span>
        {description && <span className="text-[#a3a3a3] truncate max-w-[200px]">{description}</span>}
        {step.status === "calling" && <span className="text-[#a3a3a3]">...</span>}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {command && (
        <pre className="p-3 rounded-lg text-xs overflow-x-auto font-mono bg-[#171717] text-green-400 border border-[#333]">
          $ {command}
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
