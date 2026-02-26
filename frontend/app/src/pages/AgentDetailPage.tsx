import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Bot, FileText, Wrench, Plug, Zap, Users, BookOpen,
  Play, Tag, History, Save, Plus, Trash2, Edit2, Check, Search,
  ChevronRight, ChevronDown,
} from "lucide-react";
import TestPanel from "@/components/TestPanel";
import PublishDialog from "@/components/PublishDialog";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useIsMobile } from "@/hooks/use-mobile";
import { useAppStore } from "@/store/app-store";
import type { CrudItem, SubAgent, RuleItem, McpItem } from "@/store/types";

// ==================== Types ====================

type ModuleId = "prompt" | "tools" | "mcp" | "skills" | "subagents" | "rules";

interface ModuleDef {
  id: ModuleId;
  label: string;
  icon: typeof FileText;
  hasChildren: boolean;
}

const moduleConfig: ModuleDef[] = [
  { id: "prompt", label: "System Prompt", icon: FileText, hasChildren: false },
  { id: "tools", label: "Tools", icon: Wrench, hasChildren: true },
  { id: "mcp", label: "MCP", icon: Plug, hasChildren: true },
  { id: "skills", label: "Skills", icon: Zap, hasChildren: true },
  { id: "subagents", label: "Sub-agents", icon: Users, hasChildren: true },
  { id: "rules", label: "Rules", icon: BookOpen, hasChildren: true },
];

// ==================== Selection state ====================

type Selection =
  | { module: "prompt" }
  | { module: "tools" | "mcp" | "skills" | "rules"; itemId?: string }
  | { module: "subagents"; itemId?: string };

// ==================== Main Component ====================

export default function AgentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [showTest, setShowTest] = useState(false);
  const [showPublish, setShowPublish] = useState(false);

  // Store
  const member = useAppStore(s => s.getMemberById(id || ""));
  const updateMemberConfig = useAppStore(s => s.updateMemberConfig);
  const loadAll = useAppStore(s => s.loadAll);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Selection
  const [selection, setSelection] = useState<Selection>({ module: "prompt" });

  // Collapsed state for tree sections
  const [collapsed, setCollapsed] = useState<Record<ModuleId, boolean>>({
    prompt: false, tools: false, mcp: false, skills: false, subagents: false, rules: false,
  });

  // Search in tree
  const [treeSearch, setTreeSearch] = useState("");

  // Dialog state for adding items
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addDialogTarget, setAddDialogTarget] = useState<ModuleId>("tools");
  const [addName, setAddName] = useState("");
  const [addDesc, setAddDesc] = useState("");

  const statusLabels: Record<string, string> = { active: "在岗", draft: "草稿", inactive: "离线" };

  if (!member) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">加载中...</p>
      </div>
    );
  }

  const getItemsForModule = (mod: ModuleId): { name: string; [k: string]: any }[] => {
    if (mod === "tools") return member.config.tools;
    if (mod === "mcp") return member.config.mcps;
    if (mod === "skills") return member.config.skills;
    if (mod === "subagents") return member.config.subAgents.map(sa => ({ ...sa, enabled: true }));
    if (mod === "rules") return member.config.rules;
    return [];
  };

  const toggleCollapse = (mod: ModuleId) => {
    setCollapsed(prev => ({ ...prev, [mod]: !prev[mod] }));
  };

  const openAddDialog = (target: ModuleId) => {
    setAddDialogTarget(target);
    setAddName("");
    setAddDesc("");
    setAddDialogOpen(true);
  };

  const handleAdd = async () => {
    if (!addName.trim() || !member) return;
    const trimName = addName.trim();
    const trimDesc = addDesc.trim();
    try {
      if (addDialogTarget === "tools") {
        await updateMemberConfig(member.id, { tools: [...member.config.tools, { name: trimName, desc: trimDesc, enabled: true }] });
      } else if (addDialogTarget === "mcp") {
        await updateMemberConfig(member.id, { mcps: [...member.config.mcps, { name: trimName, command: "", args: [], env: {}, disabled: false }] });
      } else if (addDialogTarget === "skills") {
        await updateMemberConfig(member.id, { skills: [...member.config.skills, { name: trimName, desc: trimDesc, enabled: true }] });
      } else if (addDialogTarget === "subagents") {
        await updateMemberConfig(member.id, { subAgents: [...member.config.subAgents, { name: trimName, desc: trimDesc }] });
      } else if (addDialogTarget === "rules") {
        await updateMemberConfig(member.id, { rules: [...member.config.rules, { name: trimName, content: "" }] });
      }
      toast.success(`${trimName} 已添加`);
      setAddDialogOpen(false);
    } catch (e) {
      toast.error("添加失败，请重试");
    }
  };

  const handleDeleteItem = async (mod: ModuleId, itemName: string) => {
    if (!member) return;
    try {
      if (mod === "tools") {
        await updateMemberConfig(member.id, { tools: member.config.tools.filter(i => i.name !== itemName) });
      } else if (mod === "mcp") {
        await updateMemberConfig(member.id, { mcps: member.config.mcps.filter(i => i.name !== itemName) });
      } else if (mod === "skills") {
        await updateMemberConfig(member.id, { skills: member.config.skills.filter(i => i.name !== itemName) });
      } else if (mod === "subagents") {
        await updateMemberConfig(member.id, { subAgents: member.config.subAgents.filter(i => i.name !== itemName) });
      } else if (mod === "rules") {
        await updateMemberConfig(member.id, { rules: member.config.rules.filter(i => i.name !== itemName) });
      }
      if ("itemId" in selection && selection.itemId === itemName) {
        setSelection({ module: mod } as Selection);
      }
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败，请重试");
    }
  };

  const handleToggle = async (mod: ModuleId, itemName: string, enabled: boolean) => {
    if (!member) return;
    try {
      if (mod === "tools") {
        await updateMemberConfig(member.id, { tools: member.config.tools.map(i => i.name === itemName ? { ...i, enabled } : i) });
      } else if (mod === "mcp") {
        await updateMemberConfig(member.id, { mcps: member.config.mcps.map(i => i.name === itemName ? { ...i, disabled: !enabled } : i) });
      } else if (mod === "skills") {
        await updateMemberConfig(member.id, { skills: member.config.skills.map(i => i.name === itemName ? { ...i, enabled } : i) });
      }
    } catch (e) {
      toast.error("更新失败，请重试");
    }
  };

  // Filter tree items by search
  const filterItems = (items: { name: string }[]) => {
    if (!treeSearch) return items;
    return items.filter(i => i.name.toLowerCase().includes(treeSearch.toLowerCase()));
  };

  // ==================== Tree Sidebar ====================

  const renderTreeSidebar = () => (
    <div className="w-[200px] shrink-0 border-r border-border bg-card flex flex-col overflow-hidden">
      {/* Search */}
      <div className="p-2 border-b border-border">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
          <input
            value={treeSearch}
            onChange={e => setTreeSearch(e.target.value)}
            placeholder="搜索模块..."
            className="w-full pl-7 pr-2 py-1.5 rounded-md bg-muted/50 border-none text-xs text-foreground placeholder:text-muted-foreground outline-none focus:bg-muted transition-colors"
          />
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {moduleConfig.map(mod => {
          const items = mod.hasChildren ? filterItems(getItemsForModule(mod.id)) : [];
          const allItems = mod.hasChildren ? getItemsForModule(mod.id) : [];
          const isExpanded = !collapsed[mod.id];
          const isModuleSelected = selection.module === mod.id && !("itemId" in selection && selection.itemId);

          // Hide entire module if search active and no matching children (for modules with children)
          if (treeSearch && mod.hasChildren && items.length === 0) return null;

          return (
            <div key={mod.id}>
              {/* Module header */}
              <div
                className={`flex items-center gap-1 px-2 py-2 rounded-lg text-xs cursor-pointer select-none transition-all group ${
                  isModuleSelected
                    ? "bg-primary/5 text-foreground border border-primary/15 font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground border border-transparent"
                }`}
              >
                {/* Expand/collapse toggle */}
                {mod.hasChildren ? (
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleCollapse(mod.id); }}
                    className="p-0.5 shrink-0"
                  >
                    {isExpanded
                      ? <ChevronDown className="w-3 h-3" />
                      : <ChevronRight className="w-3 h-3" />
                    }
                  </button>
                ) : (
                  <span className="w-4" /> /* spacer for alignment */
                )}

                <div
                  className="flex items-center gap-1.5 flex-1 min-w-0"
                  onClick={() => setSelection({ module: mod.id } as Selection)}
                >
                  <mod.icon className={`w-3.5 h-3.5 shrink-0 ${isModuleSelected ? "text-primary" : ""}`} />
                  <span className="truncate">{mod.label}</span>
                </div>

                {mod.hasChildren && (
                  <div className="flex items-center gap-1 shrink-0">
                    <span className="text-[10px] font-mono text-muted-foreground">{allItems.length}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); openAddDialog(mod.id); }}
                      className="p-0.5 rounded hover:bg-primary/10 opacity-0 group-hover:opacity-100 transition-all"
                      title="添加"
                    >
                      <Plus className="w-3 h-3 text-primary" />
                    </button>
                  </div>
                )}
              </div>

              {/* Children */}
              {mod.hasChildren && isExpanded && (
                <div className="ml-4 pl-2 border-l border-border/50 space-y-0.5 mt-0.5">
                  {items.map(item => {
                    const isItemSelected = selection.module === mod.id && "itemId" in selection && selection.itemId === item.name;
                    return (
                      <div
                        key={item.name}
                        onClick={() => setSelection({ module: mod.id, itemId: item.name } as Selection)}
                        className={`flex items-center justify-between px-2 py-1.5 rounded-md text-xs cursor-pointer group/item transition-all ${
                          isItemSelected
                            ? "bg-primary/5 text-foreground font-medium"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        }`}
                      >
                        <span className="truncate flex-1">{item.name}</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteItem(mod.id, item.name); }}
                          className="p-0.5 rounded hover:bg-destructive/10 opacity-0 group-hover/item:opacity-100 transition-all shrink-0"
                          title="删除"
                        >
                          <Trash2 className="w-2.5 h-2.5 text-muted-foreground hover:text-destructive" />
                        </button>
                      </div>
                    );
                  })}
                  {items.length === 0 && !treeSearch && (
                    <div className="px-2 py-1 text-[10px] text-muted-foreground">暂无</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  // ==================== Center Column Content ====================

  const renderCenterContent = () => {
    const mod = selection.module;
    const selectedItemId = "itemId" in selection ? selection.itemId : undefined;

    // Text editor (Prompt only)
    if (mod === "prompt") {
      return (
        <TextEditor
          key={mod}
          label="System Prompt"
          initialValue={member.config.prompt || ""}
          onSave={async (val) => {
            await updateMemberConfig(member.id, { prompt: val });
            toast.success("System Prompt 已保存");
          }}
        />
      );
    }

    // Rules — file-folder UI
    if (mod === "rules") {
      const rules = member.config.rules;
      if (selectedItemId) {
        const rule = rules.find(r => r.name === selectedItemId);
        if (!rule) return <div className="text-sm text-muted-foreground p-6">未找到该规则</div>;
        return (
          <RuleEditor
            rule={rule}
            onSave={async (content) => {
              await updateMemberConfig(member.id, { rules: rules.map(r => r.name === selectedItemId ? { ...r, content } : r) });
              toast.success("规则已保存");
            }}
            onDelete={() => handleDeleteItem("rules", selectedItemId)}
          />
        );
      }
      return (
        <RulesOverview
          rules={rules}
          onAdd={() => openAddDialog("rules")}
          onSelect={(name) => setSelection({ module: "rules", itemId: name })}
          onDelete={(name) => handleDeleteItem("rules", name)}
        />
      );
    }

    // MCP — list with disabled toggle
    if (mod === "mcp") {
      const mcps = member.config.mcps;
      if (selectedItemId) {
        const mcp = mcps.find(m => m.name === selectedItemId);
        if (!mcp) return <div className="text-sm text-muted-foreground p-6">未找到该 MCP</div>;
        return (
          <McpEditor
            item={mcp}
            onToggle={async (enabled) => handleToggle("mcp", selectedItemId, enabled)}
            onDelete={() => handleDeleteItem("mcp", selectedItemId)}
          />
        );
      }
      return (
        <McpOverview
          items={mcps}
          onAdd={() => openAddDialog("mcp")}
          onSelect={(name) => setSelection({ module: "mcp", itemId: name })}
          onDelete={(name) => handleDeleteItem("mcp", name)}
          onToggle={(name, enabled) => handleToggle("mcp", name, enabled)}
        />
      );
    }

    // CrudItem modules (tools, skills)
    if (mod === "tools" || mod === "skills") {
      const configKey = mod === "tools" ? "tools" : "skills";
      const items = member.config[configKey] as CrudItem[];
      const labels = { tools: "工具", skills: "技能" };

      if (selectedItemId) {
        const item = items.find(i => i.name === selectedItemId);
        if (!item) return <div className="text-sm text-muted-foreground p-6">未找到该项</div>;
        return (
          <CrudItemEditor
            item={item}
            onSave={async (name, desc) => {
              await updateMemberConfig(member.id, { [configKey]: items.map(i => i.name === selectedItemId ? { ...i, name, desc } : i) });
              toast.success("已更新");
            }}
            onDelete={() => handleDeleteItem(mod, selectedItemId)}
            onToggle={(enabled) => handleToggle(mod, selectedItemId, enabled)}
          />
        );
      }

      return (
        <ModuleOverview
          title={labels[mod]}
          items={items}
          onAdd={() => openAddDialog(mod)}
          onSelect={(name) => setSelection({ module: mod, itemId: name })}
          onDelete={(name) => handleDeleteItem(mod, name)}
          onToggle={(name, enabled) => handleToggle(mod, name, enabled)}
        />
      );
    }

    // Sub-agents
    if (mod === "subagents") {
      const saItems = member.config.subAgents;
      if (selectedItemId) {
        const sa = saItems.find(i => i.name === selectedItemId);
        if (!sa) return <div className="text-sm text-muted-foreground p-6">未找到该项</div>;
        return (
          <SubAgentEditor
            item={sa}
            onSave={async (name, desc) => {
              await updateMemberConfig(member.id, { subAgents: saItems.map(i => i.name === selectedItemId ? { ...i, name, desc } : i) });
              toast.success("已更新");
            }}
            onDelete={() => handleDeleteItem("subagents", selectedItemId)}
          />
        );
      }

      return (
        <SubAgentOverview
          items={saItems}
          onAdd={() => openAddDialog("subagents")}
          onSelect={(name) => setSelection({ module: "subagents", itemId: name })}
          onDelete={(name) => handleDeleteItem("subagents", name)}
        />
      );
    }

    return null;
  };

  // ==================== Mobile module selector ====================

  const renderMobileSelector = () => (
    <div className="flex overflow-x-auto border-b border-border bg-card shrink-0 px-2 py-1.5 gap-1">
      {moduleConfig.map(mod => {
        const isActive = selection.module === mod.id;
        const count = mod.hasChildren ? getItemsForModule(mod.id).length : null;
        return (
          <button
            key={mod.id}
            onClick={() => setSelection({ module: mod.id } as Selection)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              isActive ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            <mod.icon className="w-3.5 h-3.5" />
            {mod.label}
            {count !== null && <span className="font-mono text-[10px]">{count}</span>}
          </button>
        );
      })}
    </div>
  );

  // ==================== Render ====================

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-4 md:px-6 shrink-0 bg-card">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={() => navigate("/members")} className="p-1.5 rounded-md hover:bg-muted transition-colors shrink-0">
            <ArrowLeft className="w-4 h-4 text-muted-foreground" />
          </button>
          <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Bot className="w-4 h-4 text-primary" />
          </div>
          <h2 className="text-sm font-semibold text-foreground truncate">{member.name}</h2>
          <div className="hidden md:flex items-center gap-1.5 ml-1">
            <div className={`w-1.5 h-1.5 rounded-full ${member.status === "active" ? "bg-success" : member.status === "draft" ? "bg-warning" : "bg-muted-foreground"}`} />
            <span className="text-[11px] text-muted-foreground">{statusLabels[member.status] || member.status}</span>
          </div>
          <span className="hidden md:inline text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded ml-2">v{member.version}</span>
        </div>
        <div className="flex items-center gap-1 md:gap-2">
          <button onClick={() => navigate("/members/" + id + "?history=true")} className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
            <History className="w-3.5 h-3.5" />
            历史
          </button>
          <button
            onClick={() => setShowTest(!showTest)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              showTest ? "bg-success/10 text-success" : "bg-muted text-foreground hover:bg-muted/80"
            }`}
          >
            <Play className="w-3.5 h-3.5" />
            <span className="hidden md:inline">测试</span>
          </button>
          <button onClick={() => setShowPublish(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-opacity">
            <Tag className="w-3 h-3" />
            <span className="hidden md:inline">发布</span>
          </button>
        </div>
      </div>

      {/* Three-column layout */}
      <div className="flex-1 flex overflow-hidden">
        {isMobile ? (
          <div className="flex flex-col flex-1 overflow-hidden">
            {renderMobileSelector()}
            <div className="flex-1 overflow-y-auto p-4">
              {renderCenterContent()}
            </div>
          </div>
        ) : (
          <>
            {renderTreeSidebar()}
            <div className="flex-1 overflow-y-auto bg-background">
              <div className="max-w-2xl mx-auto py-6 px-6">
                {renderCenterContent()}
              </div>
            </div>
            {showTest && <TestPanel memberName={member.name} onClose={() => setShowTest(false)} />}
          </>
        )}
      </div>

      {/* Mobile test panel */}
      {isMobile && showTest && (
        <div className="fixed inset-0 z-50 bg-background flex flex-col">
          <TestPanel memberName={member.name} onClose={() => setShowTest(false)} />
        </div>
      )}

      {/* Add Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              添加{addDialogTarget === "tools" ? "工具" : addDialogTarget === "mcp" ? "MCP" : addDialogTarget === "skills" ? "技能" : addDialogTarget === "rules" ? "规则" : "Sub-agent"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input value={addName} onChange={e => setAddName(e.target.value)} placeholder="名称" />
            <Input value={addDesc} onChange={e => setAddDesc(e.target.value)} placeholder="描述" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>取消</Button>
            <Button onClick={handleAdd} disabled={!addName.trim()}>添加</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <PublishDialog open={showPublish} onOpenChange={setShowPublish} memberId={member.id} />
    </div>
  );
}

// ==================== Text Editor ====================

function TextEditor({ label, initialValue, onSave }: { label: string; initialValue: string; onSave: (val: string) => Promise<void> }) {
  const [value, setValue] = useState(initialValue);
  const [savedValue, setSavedValue] = useState(initialValue);
  const [saving, setSaving] = useState(false);
  const isDirty = value !== savedValue;

  // Sync with external changes
  useEffect(() => { setValue(initialValue); setSavedValue(initialValue); }, [initialValue]);

  const handleSave = async () => {
    try {
      setSaving(true);
      await onSave(value);
      setSavedValue(value);
    } catch (e) {
      toast.error("保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-foreground">{label}</h3>
      <textarea
        value={value}
        onChange={e => setValue(e.target.value)}
        rows={12}
        className="w-full bg-background border border-border rounded-lg px-4 py-3 text-sm text-foreground font-mono leading-relaxed outline-none focus:border-primary/40 resize-none transition-colors"
      />
      {isDirty && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-warning">有未保存的更改</span>
          <Button size="sm" onClick={handleSave} disabled={saving} className="gap-1.5">
            <Save className="w-3 h-3" />
            保存
          </Button>
        </div>
      )}
    </div>
  );
}

// ==================== Module Overview (list view for tools/mcp/skills) ====================

function ModuleOverview({
  title, items, onAdd, onSelect, onDelete, onToggle,
}: {
  title: string;
  items: CrudItem[];
  onAdd: () => void;
  onSelect: (name: string) => void;
  onDelete: (name: string) => void;
  onToggle: (name: string, enabled: boolean) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">{title} ({items.length})</h3>
        <Button variant="outline" size="sm" onClick={onAdd} className="gap-1.5">
          <Plus className="w-3 h-3" />
          添加
        </Button>
      </div>
      <div className="space-y-2">
        {items.map(item => (
          <div
            key={item.name}
            className="flex items-center justify-between p-3 rounded-lg bg-card border border-border group cursor-pointer hover:border-primary/20 transition-colors"
            onClick={() => onSelect(item.name)}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">{item.name}</p>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
            <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
              <button onClick={() => onDelete(item.name)} className="p-1 rounded hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all" title="删除">
                <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
              </button>
              <Switch checked={item.enabled} onCheckedChange={checked => onToggle(item.name, checked)} />
            </div>
          </div>
        ))}
        {items.length === 0 && (
          <div className="text-center py-8 text-xs text-muted-foreground">暂无内容，点击上方按钮添加</div>
        )}
      </div>
    </div>
  );
}

// ==================== CrudItem Editor (single item detail) ====================

function CrudItemEditor({
  item, onSave, onDelete, onToggle,
}: {
  item: CrudItem;
  onSave: (name: string, desc: string) => void;
  onDelete: () => void;
  onToggle: (enabled: boolean) => void;
}) {
  const [name, setName] = useState(item.name);
  const [desc, setDesc] = useState(item.desc);
  const isDirty = name !== item.name || desc !== item.desc;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">编辑: {item.name}</h3>
        <div className="flex items-center gap-2">
          <Switch checked={item.enabled} onCheckedChange={onToggle} />
          <Button variant="ghost" size="sm" onClick={onDelete} className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1">
            <Trash2 className="w-3 h-3" />
            删除
          </Button>
        </div>
      </div>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">名称</label>
          <Input value={name} onChange={e => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">描述</label>
          <Input value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
      </div>
      {isDirty && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-warning">有未保存的更改</span>
          <Button size="sm" onClick={() => onSave(name.trim(), desc.trim())} disabled={!name.trim()} className="gap-1.5">
            <Save className="w-3 h-3" />
            保存
          </Button>
        </div>
      )}
    </div>
  );
}

// ==================== Sub-agent Overview ====================

function SubAgentOverview({
  items, onAdd, onSelect, onDelete,
}: {
  items: SubAgent[];
  onAdd: () => void;
  onSelect: (name: string) => void;
  onDelete: (name: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Sub-agents ({items.length})</h3>
        <Button variant="outline" size="sm" onClick={onAdd} className="gap-1.5">
          <Plus className="w-3 h-3" />
          添加
        </Button>
      </div>
      <div className="space-y-2">
        {items.map(sa => (
          <div
            key={sa.name}
            className="flex items-center gap-3 p-3 rounded-lg bg-card border border-border group cursor-pointer hover:border-primary/20 transition-colors"
            onClick={() => onSelect(sa.name)}
          >
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">{sa.name}</p>
              <p className="text-xs text-muted-foreground">{sa.desc}</p>
            </div>
            <button
              onClick={e => { e.stopPropagation(); onDelete(sa.name); }}
              className="p-1 rounded hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all"
              title="删除"
            >
              <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
            </button>
          </div>
        ))}
        {items.length === 0 && (
          <div className="text-center py-8 text-xs text-muted-foreground">暂无 Sub-agent，点击上方按钮添加</div>
        )}
      </div>
    </div>
  );
}

// ==================== Sub-agent Editor ====================

function SubAgentEditor({
  item, onSave, onDelete,
}: {
  item: SubAgent;
  onSave: (name: string, desc: string) => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(item.name);
  const [desc, setDesc] = useState(item.desc);
  const isDirty = name !== item.name || desc !== item.desc;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          编辑: {item.name}
        </h3>
        <Button variant="ghost" size="sm" onClick={onDelete} className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1">
          <Trash2 className="w-3 h-3" />
          删除
        </Button>
      </div>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">名称</label>
          <Input value={name} onChange={e => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">描述</label>
          <Input value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
      </div>
      {isDirty && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-warning">有未保存的更改</span>
          <Button size="sm" onClick={() => onSave(name.trim(), desc.trim())} disabled={!name.trim()} className="gap-1.5">
            <Save className="w-3 h-3" />
            保存
          </Button>
        </div>
      )}
    </div>
  );
}

// ==================== Rules Overview ====================

function RulesOverview({
  rules, onAdd, onSelect, onDelete,
}: {
  rules: RuleItem[];
  onAdd: () => void;
  onSelect: (name: string) => void;
  onDelete: (name: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Rules ({rules.length})</h3>
        <Button variant="outline" size="sm" onClick={onAdd} className="gap-1.5">
          <Plus className="w-3 h-3" />
          添加
        </Button>
      </div>
      <div className="space-y-2">
        {rules.map(rule => (
          <div
            key={rule.name}
            className="flex items-center justify-between p-3 rounded-lg bg-card border border-border group cursor-pointer hover:border-primary/20 transition-colors"
            onClick={() => onSelect(rule.name)}
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <BookOpen className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground">{rule.name}.md</p>
                <p className="text-xs text-muted-foreground truncate">{rule.content.slice(0, 80) || "空规则"}</p>
              </div>
            </div>
            <button
              onClick={e => { e.stopPropagation(); onDelete(rule.name); }}
              className="p-1 rounded hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all shrink-0"
              title="删除"
            >
              <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
            </button>
          </div>
        ))}
        {rules.length === 0 && (
          <div className="text-center py-8 text-xs text-muted-foreground">暂无规则，点击上方按钮添加</div>
        )}
      </div>
    </div>
  );
}

// ==================== Rule Editor ====================

function RuleEditor({
  rule, onSave, onDelete,
}: {
  rule: RuleItem;
  onSave: (content: string) => Promise<void>;
  onDelete: () => void;
}) {
  const [content, setContent] = useState(rule.content);
  const [savedContent, setSavedContent] = useState(rule.content);
  const [saving, setSaving] = useState(false);
  const isDirty = content !== savedContent;

  useEffect(() => { setContent(rule.content); setSavedContent(rule.content); }, [rule.content]);

  const handleSave = async () => {
    try {
      setSaving(true);
      await onSave(content);
      setSavedContent(content);
    } catch (e) {
      toast.error("保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-primary" />
          {rule.name}.md
        </h3>
        <Button variant="ghost" size="sm" onClick={onDelete} className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1">
          <Trash2 className="w-3 h-3" />
          删除
        </Button>
      </div>
      <textarea
        value={content}
        onChange={e => setContent(e.target.value)}
        rows={16}
        className="w-full bg-background border border-border rounded-lg px-4 py-3 text-sm text-foreground font-mono leading-relaxed outline-none focus:border-primary/40 resize-none transition-colors"
      />
      {isDirty && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-warning">有未保存的更改</span>
          <Button size="sm" onClick={handleSave} disabled={saving} className="gap-1.5">
            <Save className="w-3 h-3" />
            保存
          </Button>
        </div>
      )}
    </div>
  );
}

// ==================== MCP Overview ====================

function McpOverview({
  items, onAdd, onSelect, onDelete, onToggle,
}: {
  items: McpItem[];
  onAdd: () => void;
  onSelect: (name: string) => void;
  onDelete: (name: string) => void;
  onToggle: (name: string, enabled: boolean) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">MCP ({items.length})</h3>
        <Button variant="outline" size="sm" onClick={onAdd} className="gap-1.5">
          <Plus className="w-3 h-3" />
          添加
        </Button>
      </div>
      <div className="space-y-2">
        {items.map(item => (
          <div
            key={item.name}
            className="flex items-center justify-between p-3 rounded-lg bg-card border border-border group cursor-pointer hover:border-primary/20 transition-colors"
            onClick={() => onSelect(item.name)}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">{item.name}</p>
              <p className="text-xs text-muted-foreground font-mono">{item.command || "未配置"}</p>
            </div>
            <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
              <button onClick={() => onDelete(item.name)} className="p-1 rounded hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all" title="删除">
                <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
              </button>
              <Switch checked={!item.disabled} onCheckedChange={checked => onToggle(item.name, checked)} />
            </div>
          </div>
        ))}
        {items.length === 0 && (
          <div className="text-center py-8 text-xs text-muted-foreground">暂无 MCP，点击上方按钮添加</div>
        )}
      </div>
    </div>
  );
}

// ==================== MCP Editor ====================

function McpEditor({
  item, onToggle, onDelete,
}: {
  item: McpItem;
  onToggle: (enabled: boolean) => void;
  onDelete: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Plug className="w-4 h-4 text-primary" />
          {item.name}
        </h3>
        <div className="flex items-center gap-2">
          <Switch checked={!item.disabled} onCheckedChange={onToggle} />
          <Button variant="ghost" size="sm" onClick={onDelete} className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1">
            <Trash2 className="w-3 h-3" />
            删除
          </Button>
        </div>
      </div>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Command</label>
          <div className="px-3 py-2 rounded-md bg-muted text-sm font-mono text-foreground">{item.command || "—"}</div>
        </div>
        {item.args.length > 0 && (
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Args</label>
            <div className="px-3 py-2 rounded-md bg-muted text-sm font-mono text-foreground">{item.args.join(" ")}</div>
          </div>
        )}
        {Object.keys(item.env).length > 0 && (
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Env</label>
            <div className="px-3 py-2 rounded-md bg-muted text-xs font-mono text-foreground space-y-1">
              {Object.entries(item.env).map(([k, v]) => (
                <div key={k}>{k}={v.length > 20 ? v.slice(0, 20) + "..." : v}</div>
              ))}
            </div>
          </div>
        )}
      </div>
      <p className="text-xs text-muted-foreground">MCP 配置请直接编辑 .mcp.json 文件</p>
    </div>
  );
}

