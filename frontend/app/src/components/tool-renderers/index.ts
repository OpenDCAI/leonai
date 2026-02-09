import type { ToolStep } from "../../api";
import type { ToolRendererProps } from "./types";
import DefaultRenderer from "./DefaultRenderer";
import EditFileRenderer from "./EditFileRenderer";
import ReadFileRenderer from "./ReadFileRenderer";
import RunCommandRenderer from "./RunCommandRenderer";
import SearchRenderer from "./SearchRenderer";
import WebRenderer from "./WebRenderer";

type RendererComponent = React.ComponentType<ToolRendererProps>;

/** Disclosure level determines how a tool step is displayed:
 *  - "silent": hidden entirely (internal tools the user doesn't need to see)
 *  - "inline": single grey line, no expand (read-only / search tools)
 *  - "card":   bordered card, expandable details (write / command tools)
 */
export type DisclosureLevel = "silent" | "inline" | "card";

const TOOL_RENDERERS: Record<string, RendererComponent> = {
  // Card-level: write/edit tools
  Edit: EditFileRenderer,
  edit_file: EditFileRenderer,
  Write: EditFileRenderer,
  write_file: EditFileRenderer,

  // Card-level: command tools
  Bash: RunCommandRenderer,
  run_command: RunCommandRenderer,
  execute_command: RunCommandRenderer,

  // Inline: read tools
  Read: ReadFileRenderer,
  read_file: ReadFileRenderer,

  // Inline: search tools
  Grep: SearchRenderer,
  Glob: SearchRenderer,
  search: SearchRenderer,
  find_files: SearchRenderer,

  // Inline: web tools
  WebFetch: WebRenderer,
  web_search: WebRenderer,
  WebSearch: WebRenderer,
};

/** Tools that get card-level disclosure (expandable, bordered) */
const CARD_TOOLS = new Set([
  "Edit", "edit_file", "Write", "write_file",
  "Bash", "run_command", "execute_command",
]);

/** Tools that are hidden entirely */
const SILENT_TOOLS = new Set([
  "ListDir", "list_directory", "list_dir",
  "Task", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet",
  "EnterPlanMode", "ExitPlanMode",
  "AskUserQuestion",
]);

export function getDisclosureLevel(step: ToolStep): DisclosureLevel {
  if (SILENT_TOOLS.has(step.name)) return "silent";
  if (CARD_TOOLS.has(step.name)) return "card";
  return "inline";
}

export function getToolRenderer(step: ToolStep): RendererComponent {
  return TOOL_RENDERERS[step.name] ?? DefaultRenderer;
}

export type { ToolRendererProps } from "./types";
