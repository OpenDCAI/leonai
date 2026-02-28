import type { ToolStep } from "../../api";

export function formatTime(ts?: number): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

export function getStepSummary(step: ToolStep): string {
  const args = step.args as Record<string, unknown> | null;
  if (!args) return step.name;

  const filePath =
    (args.FilePath as string) ??
    (args.file_path as string) ??
    (args.path as string);
  if (filePath) {
    const parts = filePath.split("/");
    return parts[parts.length - 1] || filePath;
  }

  const cmd =
    (args.CommandLine as string) ??
    (args.command as string) ??
    (args.cmd as string);
  if (cmd) {
    return cmd.length > 60 ? cmd.slice(0, 57) + "..." : cmd;
  }

  const pattern =
    (args.Pattern as string) ??
    (args.pattern as string) ??
    (args.query as string) ??
    (args.SearchPath as string);
  if (pattern) {
    return pattern.length > 60 ? pattern.slice(0, 57) + "..." : pattern;
  }

  const desc = (args.description as string) ?? (args.prompt as string);
  if (desc) {
    return desc.length > 60 ? desc.slice(0, 57) + "..." : desc;
  }

  return step.name;
}
