import { Bot, ChevronDown, ChevronRight, FileText, Folder, FolderOpen, Loader2, Pause, Play, Terminal } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getThreadLease,
  listWorkspace,
  pauseThreadSandbox,
  readWorkspaceFile,
  resumeThreadSandbox,
  type ChatEntry,
  type LeaseStatus,
  type ToolStep,
  type WorkspaceEntry,
} from "../api";
import MarkdownContent from "./MarkdownContent";

interface ComputerPanelProps {
  isOpen: boolean;
  onClose: () => void;
  threadId: string | null;
  sandboxType: string | null;
  chatEntries: ChatEntry[];
  width?: number;
  activeTab?: "terminal" | "files" | "agents";
  onTabChange?: (tab: "terminal" | "files" | "agents") => void;
  focusedAgentStepId?: string | null;
  onFocusAgent?: (stepId: string | null) => void;
}

function joinPath(base: string, name: string): string {
  if (base.endsWith("/")) return `${base}${name}`;
  return `${base}/${name}`;
}

/** Extract all run_command tool steps from chat entries */
function extractCommandSteps(entries: ChatEntry[]): ToolStep[] {
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

function parseCommandArgs(args: unknown): { command?: string; cwd?: string; description?: string } {
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

/* ── Terminal view ─────────────────────────────────────────── */

function TerminalView({ steps }: { steps: ToolStep[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps]);

  return (
    <div
      ref={scrollRef}
      className="h-full overflow-auto font-mono text-[13px] leading-[1.6] p-4"
      style={{ background: "#1e1e1e", color: "#d4d4d4" }}
    >
      {/* Boot banner */}
      <div style={{ color: "#6a9955" }} className="mb-3 select-none">
        <div>Leon Terminal v1.0</div>
        <div className="text-[11px]" style={{ color: "#555" }}>Type is streamed from agent tool calls</div>
        <div className="mt-1" style={{ color: "#333" }}>{"─".repeat(48)}</div>
      </div>

      {steps.length === 0 && (
        <div style={{ color: "#555" }}>
          <span style={{ color: "#6a9955" }}>leon@sandbox</span>
          <span style={{ color: "#555" }}>:</span>
          <span style={{ color: "#569cd6" }}>~</span>
          <span style={{ color: "#d4d4d4" }}>$ </span>
          <span className="animate-pulse">_</span>
        </div>
      )}

      {steps.map((step) => {
        const { command, cwd } = parseCommandArgs(step.args);
        const dir = cwd || "~";
        const shortDir = dir === "/" ? "/" : dir.split("/").pop() || dir;

        return (
          <div key={step.id} className="mb-3">
            {/* Prompt line */}
            <div className="flex flex-wrap">
              <span style={{ color: "#6a9955" }}>leon@sandbox</span>
              <span style={{ color: "#d4d4d4" }}>:</span>
              <span style={{ color: "#569cd6" }}>{shortDir}</span>
              <span style={{ color: "#d4d4d4" }}>$ </span>
              <span style={{ color: "#ce9178" }}>{command || "(empty)"}</span>
            </div>

            {/* Output */}
            {step.status === "calling" ? (
              <div className="mt-0.5" style={{ color: "#555" }}>
                <span className="animate-pulse">...</span>
              </div>
            ) : step.result ? (
              <pre
                className="mt-0.5 whitespace-pre-wrap break-words"
                style={{ color: "#cccccc" }}
              >{step.result}</pre>
            ) : (
              <div className="mt-0.5" style={{ color: "#555" }}>(no output)</div>
            )}

            {/* Exit indicator for errors */}
            {step.status === "error" && (
              <div style={{ color: "#f44747" }} className="mt-0.5">
                [exit: error]
              </div>
            )}
          </div>
        );
      })}

      {/* Cursor at bottom if last command is done */}
      {steps.length > 0 && steps[steps.length - 1].status !== "calling" && (
        <div>
          <span style={{ color: "#6a9955" }}>leon@sandbox</span>
          <span style={{ color: "#d4d4d4" }}>:</span>
          <span style={{ color: "#569cd6" }}>~</span>
          <span style={{ color: "#d4d4d4" }}>$ </span>
          <span className="animate-pulse">_</span>
        </div>
      )}
    </div>
  );
}

/* ── Resizable file tree divider ───────────────────────────── */

function useResizable(initialWidth: number, minWidth: number, maxWidth: number) {
  const [width, setWidth] = useState(initialWidth);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = width;

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = ev.clientX - startX.current;
      const next = Math.min(maxWidth, Math.max(minWidth, startW.current + delta));
      setWidth(next);
    };

    const onMouseUp = () => {
      dragging.current = false;
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [width, minWidth, maxWidth]);

  return { width, onMouseDown };
}

/* ── File tree types & component ────────────────────────────── */

interface TreeNode {
  name: string;
  fullPath: string;
  is_dir: boolean;
  size: number;
  children_count?: number | null;
  children?: TreeNode[];
  expanded?: boolean;
  loading?: boolean;
}

function buildTreeNodes(entries: WorkspaceEntry[], parentPath: string): TreeNode[] {
  return entries.map((e) => ({
    ...e,
    fullPath: joinPath(parentPath, e.name),
    children: e.is_dir ? undefined : undefined,
    expanded: false,
    loading: false,
  }));
}

function updateNodeAtPath(
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

function FileTreeNode({
  node,
  depth,
  onToggle,
  onSelectFile,
  selectedFilePath,
}: {
  node: TreeNode;
  depth: number;
  onToggle: (fullPath: string) => void;
  onSelectFile: (fullPath: string) => void;
  selectedFilePath: string | null;
}) {
  const isSelected = !node.is_dir && node.fullPath === selectedFilePath;

  return (
    <>
      <button
        className={`w-full text-left py-1 pr-2 rounded text-[13px] flex items-center gap-1 transition-colors ${
          isSelected
            ? "bg-blue-50 text-blue-700"
            : "text-[#171717] hover:bg-[#f5f5f5]"
        }`}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        onClick={() => {
          if (node.is_dir) {
            onToggle(node.fullPath);
          } else {
            onSelectFile(node.fullPath);
          }
        }}
      >
        {node.is_dir ? (
          node.loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[#a3a3a3] flex-shrink-0" />
          ) : node.expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-[#a3a3a3] flex-shrink-0" />
          )
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}
        {node.is_dir ? (
          node.expanded ? (
            <FolderOpen className="w-4 h-4 text-[#525252] flex-shrink-0" />
          ) : (
            <Folder className="w-4 h-4 text-[#525252] flex-shrink-0" />
          )
        ) : (
          <FileText className="w-4 h-4 text-[#a3a3a3] flex-shrink-0" />
        )}
        <span className="flex-1 truncate">{node.name}</span>
        {!node.is_dir && <span className="text-[10px] text-[#d4d4d4] flex-shrink-0">{node.size}</span>}
      </button>
      {node.is_dir && node.expanded && node.children && (
        node.children.map((child) => (
          <FileTreeNode
            key={child.fullPath}
            node={child}
            depth={depth + 1}
            onToggle={onToggle}
            onSelectFile={onSelectFile}
            selectedFilePath={selectedFilePath}
          />
        ))
      )}
    </>
  );
}

/* ── Extract Task agent steps ──────────────────────────────── */

function extractAgentSteps(entries: ChatEntry[]): ToolStep[] {
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

function parseAgentArgs(args: unknown): { description?: string; prompt?: string; subagent_type?: string } {
  if (args && typeof args === "object") return args as { description?: string; prompt?: string; subagent_type?: string };
  return {};
}

/* ── Agents view ──────────────────────────────────────────── */

function AgentsView({
  steps,
  focusedStepId,
  onFocusStep,
}: {
  steps: ToolStep[];
  focusedStepId: string | null;
  onFocusStep: (id: string | null) => void;
}) {
  const outputRef = useRef<HTMLDivElement>(null);
  const [leftWidth, setLeftWidth] = useState(280);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const focused = steps.find((s) => s.id === focusedStepId) ?? null;
  const stream = focused?.subagent_stream;

  // Auto-scroll output when streaming
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [focusedStepId, stream?.text, stream?.tool_calls.length]);

  // Drag handlers for resizable panel
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartX.current = e.clientX;
    dragStartWidth.current = leftWidth;
  }, [leftWidth]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - dragStartX.current;
      const newWidth = Math.max(200, Math.min(600, dragStartWidth.current + delta));
      setLeftWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  if (steps.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
        暂无助手任务
      </div>
    );
  }

  return (
    <div className="h-full flex bg-white">
      {/* Left sidebar - agent list */}
      <div className="flex-shrink-0 border-r border-[#e5e5e5] flex flex-col" style={{ width: `${leftWidth}px` }}>
        <div className="px-3 py-2 border-b border-[#e5e5e5]">
          <div className="text-xs text-[#737373] font-medium">运行中的助手</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {steps.map((step) => {
            const args = parseAgentArgs(step.args);
            const agentType = args.subagent_type || "通用助手";
            const prompt = args.prompt || args.description || "";
            const promptPreview = prompt.slice(0, 80) + (prompt.length > 80 ? "..." : "");
            const ss = step.subagent_stream;
            const isRunning = step.status === "calling" && ss?.status === "running";
            const isError = step.status === "error" || ss?.status === "error";
            const isSelected = step.id === focusedStepId;
            const statusDot = isRunning ? "bg-green-400 animate-pulse" : isError ? "bg-red-400" : "bg-[#a3a3a3]";

            return (
              <button
                key={step.id}
                className={`w-full text-left px-3 py-2.5 border-b border-[#f5f5f5] transition-colors ${
                  isSelected ? "bg-blue-50" : "hover:bg-[#f5f5f5]"
                }`}
                onClick={() => onFocusStep(step.id)}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot}`} />
                  <div className="text-[11px] font-semibold text-[#171717] truncate">{agentType}</div>
                </div>
                {promptPreview && (
                  <div className="text-[10px] text-[#737373] line-clamp-3 leading-relaxed">{promptPreview}</div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Resizable divider */}
      <div
        className={`w-1 flex-shrink-0 cursor-col-resize hover:bg-blue-400 transition-colors ${
          isDragging ? "bg-blue-500" : "bg-transparent"
        }`}
        onMouseDown={handleMouseDown}
      />

      {/* Right detail - real-time streaming output */}
      <div className="flex-1 flex flex-col min-w-0">
        {!focused ? (
          <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
            选择一个助手查看详情
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#e5e5e5] bg-[#fafafa] flex-shrink-0">
              <div className="flex-1">
                <div className="text-sm font-medium text-[#171717]">
                  {parseAgentArgs(focused.args).subagent_type || "通用助手"}
                </div>
                <div className="text-[10px] text-[#737373] line-clamp-1">
                  {parseAgentArgs(focused.args).prompt || parseAgentArgs(focused.args).description || ""}
                </div>
              </div>
              <span
                className={`w-2 h-2 rounded-full ${
                  stream?.status === "running"
                    ? "bg-green-400 animate-pulse"
                    : stream?.status === "error"
                    ? "bg-red-400"
                    : focused.status === "calling"
                    ? "bg-yellow-400 animate-pulse"
                    : "bg-[#a3a3a3]"
                }`}
              />
              <span className="text-[10px] text-[#a3a3a3]">
                {stream?.status === "running" ? "运行中" : stream?.status === "error" ? "出错" : focused.status === "calling" ? "启动中" : "已完成"}
              </span>
            </div>

            {/* Output - render streaming data */}
            <div ref={outputRef} className="flex-1 overflow-y-auto px-4 py-3">
              {stream ? (
                <div className="space-y-3">
                  {/* Streaming text */}
                  {stream.text && (
                    <div className="text-sm text-[#171717]">
                      <MarkdownContent content={stream.text} />
                    </div>
                  )}

                  {/* Tool calls */}
                  {stream.tool_calls.length > 0 && (
                    <div className="space-y-2">
                      {stream.tool_calls.map((tc, idx) => (
                        <div key={tc.id || idx} className="border-l-2 border-blue-400 pl-3 py-1">
                          <div className="text-[11px] font-medium text-[#525252] font-mono">{tc.name}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Error */}
                  {stream.error && (
                    <div className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{stream.error}</div>
                  )}
                </div>
              ) : focused.status === "calling" ? (
                <div className="flex items-center justify-center py-8">
                  <span className="text-[11px] text-[#525252]">助手启动中...</span>
                </div>
              ) : focused.result ? (
                <div className="text-sm text-[#171717]">
                  <MarkdownContent content={focused.result} />
                </div>
              ) : (
                <div className="text-xs text-[#525252] text-center py-8">(无输出)</div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Main panel ────────────────────────────────────────────── */

export default function ComputerPanel({ isOpen, onClose, threadId, sandboxType, chatEntries, width = 600, activeTab: controlledTab, onTabChange, focusedAgentStepId = null, onFocusAgent }: ComputerPanelProps) {
  const [internalTab, setInternalTab] = useState<"terminal" | "files" | "agents">("terminal");
  const activeTab = controlledTab ?? internalTab;
  const setActiveTab = onTabChange ?? setInternalTab;
  const [lease, setLease] = useState<LeaseStatus | null>(null);

  const [currentPath, setCurrentPath] = useState<string>("");
  const [workspaceRoot, setWorkspaceRoot] = useState<string>("");
  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const isRemote = sandboxType !== null && sandboxType !== "local";
  const commandSteps = useMemo(() => extractCommandSteps(chatEntries), [chatEntries]);
  const agentSteps = useMemo(() => extractAgentSteps(chatEntries), [chatEntries]);
  const { width: treeWidth, onMouseDown: onDragStart } = useResizable(288, 160, 500);

  async function refreshStatus() {
    if (!threadId) return;
    if (!isRemote) {
      setLease(null);
      return;
    }
    try {
      const l = await getThreadLease(threadId);
      setLease(l);
    } catch {
      // status banner not implemented; keep fail-loud in backend and keep UI minimal.
    }
  }

  async function refreshWorkspace(pathOverride?: string) {
    if (!threadId) return;
    const target = pathOverride ?? currentPath;
    setLoadingWorkspace(true);
    setWorkspaceError(null);
    try {
      const data = await listWorkspace(threadId, target || undefined);
      setCurrentPath(data.path);
      if (!workspaceRoot) setWorkspaceRoot(data.path);
      setTreeNodes(buildTreeNodes(data.entries, data.path));
    } catch (e) {
      setWorkspaceError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingWorkspace(false);
    }
  }

  const handleToggleFolder = useCallback(async (fullPath: string) => {
    if (!threadId) return;
    // Find the node to check if already expanded
    const findNode = (nodes: TreeNode[]): TreeNode | undefined => {
      for (const n of nodes) {
        if (n.fullPath === fullPath) return n;
        if (n.children) {
          const found = findNode(n.children);
          if (found) return found;
        }
      }
      return undefined;
    };

    const target = findNode(treeNodes);
    if (!target) return;

    if (target.expanded) {
      // Collapse
      setTreeNodes((prev) => updateNodeAtPath(prev, fullPath, (n) => ({ ...n, expanded: false })));
      return;
    }

    if (target.children) {
      // Already loaded, just expand
      setTreeNodes((prev) => updateNodeAtPath(prev, fullPath, (n) => ({ ...n, expanded: true })));
      return;
    }

    // Lazy load children
    setTreeNodes((prev) => updateNodeAtPath(prev, fullPath, (n) => ({ ...n, loading: true })));
    try {
      const data = await listWorkspace(threadId, fullPath);
      const children = buildTreeNodes(data.entries, fullPath);
      setTreeNodes((prev) =>
        updateNodeAtPath(prev, fullPath, (n) => ({ ...n, children, expanded: true, loading: false })),
      );
    } catch {
      setTreeNodes((prev) => updateNodeAtPath(prev, fullPath, (n) => ({ ...n, loading: false })));
    }
  }, [threadId, treeNodes]);

  const handleSelectFile = useCallback(async (fullPath: string) => {
    if (!threadId) return;
    setSelectedFilePath(fullPath);
    try {
      const file = await readWorkspaceFile(threadId, fullPath);
      setSelectedFileContent(file.content);
    } catch {
      setSelectedFileContent("(无法读取文件)");
    }
  }, [threadId]);

  useEffect(() => {
    if (!isOpen) return;
    void refreshStatus();
  }, [isOpen, threadId, sandboxType]);

  useEffect(() => {
    if (!isOpen || !threadId || activeTab !== "files") return;
    void refreshWorkspace();
  }, [isOpen, threadId, activeTab]);

  if (!isOpen) return null;

  return (
    <div className="h-full flex flex-col animate-fade-in bg-white border-l border-[#e5e5e5] flex-shrink-0" style={{ width }}>
      {/* Panel header */}
      <div className="h-12 flex items-center justify-between px-4 flex-shrink-0 border-b border-[#e5e5e5]">
        <div>
          <h3 className="text-sm font-semibold text-[#171717]">另一台小电脑</h3>
          <p className="text-[11px] font-mono text-[#a3a3a3]">
            {threadId ? threadId.slice(0, 20) : "无对话"}
          </p>
        </div>
        <div className="flex items-center gap-1">
          {isRemote && lease?.instance?.state === "running" && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
              onClick={() => void (threadId && pauseThreadSandbox(threadId).then(refreshStatus))}
            >
              <Pause className="w-4 h-4" />
            </button>
          )}
          {isRemote && lease?.instance?.state === "paused" && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-green-600"
              onClick={() => void (threadId && resumeThreadSandbox(threadId).then(refreshStatus))}
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          <button
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[#a3a3a3] hover:bg-[#f5f5f5] hover:text-[#171717]"
            onClick={onClose}
            title="收起视窗"
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
              <polyline points="3,10 7,10 7,14" />
              <polyline points="13,6 9,6 9,2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="h-10 flex items-center px-2 flex-shrink-0 border-b border-[#e5e5e5]">
        <button
          onClick={() => setActiveTab("terminal")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === "terminal"
              ? "bg-[#f5f5f5] text-[#171717] font-medium"
              : "text-[#737373] hover:text-[#171717]"
          }`}
        >
          <Terminal className="w-4 h-4" />
          <span>终端</span>
        </button>
        <button
          onClick={() => setActiveTab("files")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === "files"
              ? "bg-[#f5f5f5] text-[#171717] font-medium"
              : "text-[#737373] hover:text-[#171717]"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>文件</span>
        </button>
        <button
          onClick={() => setActiveTab("agents")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === "agents"
              ? "bg-[#f5f5f5] text-[#171717] font-medium"
              : "text-[#737373] hover:text-[#171717]"
          }`}
        >
          <Bot className="w-4 h-4" />
          <span>助手</span>
          {agentSteps.some((s) => s.status === "calling") && (
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          )}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "terminal" && (
          <TerminalView steps={commandSteps} />
        )}

        {activeTab === "agents" && (
          <AgentsView
            steps={agentSteps}
            focusedStepId={focusedAgentStepId}
            onFocusStep={(id) => onFocusAgent?.(id)}
          />
        )}

        {activeTab === "files" && (
          <div className="h-full flex bg-white">
            {/* File tree — resizable */}
            <div className="flex flex-col border-r border-[#e5e5e5] flex-shrink-0" style={{ width: treeWidth }}>
              <div className="px-3 py-2 border-b border-[#e5e5e5]">
                <div className="text-xs text-[#737373] font-medium truncate">
                  {workspaceRoot ? workspaceRoot.split("/").pop() || "/" : "/"}
                </div>
              </div>
              <div className="flex-1 overflow-auto py-1">
                {loadingWorkspace && (
                  <div className="text-xs flex items-center gap-2 px-2 py-2 text-[#737373]">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    加载中...
                  </div>
                )}
                {workspaceError && <p className="text-xs px-2 py-2 text-red-500">{workspaceError}</p>}
                {!loadingWorkspace && !workspaceError && treeNodes.map((node) => (
                  <FileTreeNode
                    key={node.fullPath}
                    node={node}
                    depth={0}
                    onToggle={handleToggleFolder}
                    onSelectFile={handleSelectFile}
                    selectedFilePath={selectedFilePath}
                  />
                ))}
              </div>
            </div>

            {/* Drag handle */}
            <div
              className="w-1 cursor-col-resize hover:bg-blue-400 active:bg-blue-500 transition-colors flex-shrink-0"
              onMouseDown={onDragStart}
            />

            {/* File preview */}
            <div className="flex-1 overflow-auto min-w-0">
              {!selectedFilePath && (
                <div className="h-full flex items-center justify-center text-sm text-[#a3a3a3]">
                  选择文件以预览
                </div>
              )}
              {selectedFilePath && (
                <div className="h-full flex flex-col">
                  <div className="px-4 py-2 text-xs font-mono border-b border-[#e5e5e5] text-[#737373]">
                    {selectedFilePath}
                  </div>
                  <pre className="flex-1 p-4 text-sm whitespace-pre-wrap break-words font-mono text-[#404040]">
                    {selectedFileContent}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
