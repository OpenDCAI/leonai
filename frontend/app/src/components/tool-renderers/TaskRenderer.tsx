import { GitBranch } from "lucide-react";
import type { ToolRendererProps } from "./types";

function parseArgs(args: unknown): { description?: string; prompt?: string; subject?: string; taskId?: string; status?: string } {
  if (args && typeof args === "object") return args as { description?: string; prompt?: string; subject?: string; taskId?: string; status?: string };
  return {};
}

function getTaskLabel(name: string, args: ReturnType<typeof parseArgs>): string {
  switch (name) {
    case "TaskCreate":
      return args.subject || args.description?.slice(0, 50) || "创建任务";
    case "TaskUpdate":
      return args.status ? `更新任务 #${args.taskId ?? "?"} → ${args.status}` : `更新任务 #${args.taskId ?? "?"}`;
    case "TaskList":
      return "查看任务列表";
    case "TaskGet":
      return `查看任务 #${args.taskId ?? "?"}`;
    default:
      return args.description?.slice(0, 60) || args.prompt?.slice(0, 60) || "执行子任务";
  }
}

export default function TaskRenderer({ step, expanded }: ToolRendererProps) {
  const args = parseArgs(step.args);
  const label = getTaskLabel(step.name, args);

  if (!expanded) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#a3a3a3]">
        <GitBranch className="w-3 h-3 text-violet-400 flex-shrink-0" />
        <span className="truncate max-w-[320px]">{label}</span>
        {step.status === "calling" && <span>...</span>}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {args.prompt && (
        <div className="p-3 rounded-lg text-xs bg-[#fafafa] border border-[#e5e5e5] text-[#525252] whitespace-pre-wrap">
          {args.prompt}
        </div>
      )}
      {step.result && (
        <pre className="p-3 rounded-lg text-xs overflow-x-auto max-h-[200px] overflow-y-auto font-mono bg-[#fafafa] border border-[#e5e5e5] text-[#525252]">
          {step.result}
        </pre>
      )}
    </div>
  );
}
