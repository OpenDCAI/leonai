import type { ChatEntry, ToolStep, WorkspaceEntry } from "../../api";
import type { TreeNode } from "./types";

export function joinPath(base: string, name: string): string {
  if (base.endsWith("/")) return `${base}${name}`;
  return `${base}/${name}`;
}

/** Extract all run_command tool steps from chat entries */
export function extractCommandSteps(entries: ChatEntry[]): ToolStep[] {
  const steps: ToolStep[] = [];
  for (const entry of entries) {
    if (entry.role !== "assistant") continue;
    for (const seg of entry.segments) {
      if (seg.type === "tool" && seg.step.name === "run_command") {
        steps.push(seg.step);
      }
    }
  }
  return steps;
}

/** Extract all Task agent steps from chat entries */
export function extractAgentSteps(entries: ChatEntry[]): ToolStep[] {
  const steps: ToolStep[] = [];
  for (const entry of entries) {
    if (entry.role !== "assistant") continue;
    for (const seg of entry.segments) {
      if (seg.type === "tool" && seg.step.name === "Task") {
        steps.push(seg.step);
      }
    }
  }
  return steps;
}

/** Extract all tool steps from chat entries */
export function extractAllToolSteps(entries: ChatEntry[]): ToolStep[] {
  const steps: ToolStep[] = [];
  for (const entry of entries) {
    if (entry.role !== "assistant") continue;
    for (const seg of entry.segments) {
      if (seg.type === "tool") {
        steps.push(seg.step);
      }
    }
  }
  return steps;
}

export function parseCommandArgs(args: unknown): { command?: string; cwd?: string; description?: string } {
  if (args && typeof args === "object") {
    const a = args as Record<string, unknown>;
    return {
      command: (a.CommandLine ?? a.command ?? a.cmd) as string | undefined,
      cwd: (a.Cwd ?? a.cwd ?? a.working_directory) as string | undefined,
      description: a.description as string | undefined,
    };
  }
  return {};
}

export function parseAgentArgs(args: unknown): { description?: string; prompt?: string; subagent_type?: string } {
  if (args && typeof args === "object") return args as { description?: string; prompt?: string; subagent_type?: string };
  return {};
}

export function buildTreeNodes(entries: WorkspaceEntry[], parentPath: string): TreeNode[] {
  return entries.map((e) => ({
    ...e,
    fullPath: joinPath(parentPath, e.name),
    children: undefined,
    expanded: false,
    loading: false,
  }));
}

export function updateNodeAtPath(
  nodes: TreeNode[],
  targetPath: string,
  updater: (node: TreeNode) => TreeNode,
): TreeNode[] {
  return nodes.map((node) => {
    if (node.fullPath === targetPath) return updater(node);
    if (node.children && targetPath.startsWith(node.fullPath + "/")) {
      return { ...node, children: updateNodeAtPath(node.children, targetPath, updater) };
    }
    return node;
  });
}
