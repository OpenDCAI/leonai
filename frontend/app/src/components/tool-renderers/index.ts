import type { ToolStep } from "../../api";
import type { ToolRendererProps } from "./types";
import DefaultRenderer from "./DefaultRenderer";
import EditFileRenderer from "./EditFileRenderer";
import ReadFileRenderer from "./ReadFileRenderer";
import RunCommandRenderer from "./RunCommandRenderer";
import SearchRenderer from "./SearchRenderer";
import WebRenderer from "./WebRenderer";

type RendererComponent = React.ComponentType<ToolRendererProps>;

const TOOL_RENDERERS: Record<string, RendererComponent> = {
  // Edit tools
  Edit: EditFileRenderer,
  edit_file: EditFileRenderer,
  Write: EditFileRenderer,
  write_file: EditFileRenderer,

  // Command tools
  Bash: RunCommandRenderer,
  run_command: RunCommandRenderer,
  execute_command: RunCommandRenderer,

  // Read tools
  Read: ReadFileRenderer,
  read_file: ReadFileRenderer,

  // Search tools
  Grep: SearchRenderer,
  Glob: SearchRenderer,
  search: SearchRenderer,
  find_files: SearchRenderer,

  // Web tools
  WebFetch: WebRenderer,
  web_search: WebRenderer,
  WebSearch: WebRenderer,
};

export function getToolRenderer(step: ToolStep): RendererComponent {
  return TOOL_RENDERERS[step.name] ?? DefaultRenderer;
}

export type { ToolRendererProps } from "./types";
