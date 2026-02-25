import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Bot, FileText, Wrench, Plug, Zap, Users, BookOpen, Brain,
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
import type { CrudItem, SubAgent } from "@/store/types";

// ==================== Types ====================

type ModuleId = "prompt" | "tools" | "mcp" | "skills" | "subagents" | "rules" | "memory";

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
  { id: "rules", label: "Rules", icon: BookOpen, hasChildren: false },
  { id: "memory", label: "Memory", icon: Brain, hasChildren: false },
];

// ==================== Selection state ====================

type Selection =
  | { module: "prompt" | "rules" | "memory" }
  | { module: "tools" | "mcp" | "skills"; itemId?: string }
  | { module: "subagents"; itemId?: string };

// ==================== Main Component ====================

export default function AgentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [showTest, setShowTest] = useState(false);
  const [showPublish, setShowPublish] = useState(false);

  // Store
  const staff = useAppStore(s => s.getStaffById(id || ""));
  const updateStaffConfig = useAppStore(s => s.updateStaffConfig);
  const loadAll = useAppStore(s => s.loadAll);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Selection
  const [selection, setSelection] = useState<Selection>({ module: "prompt" });

  // Collapsed state for tree sections
  const [collapsed, setCollapsed] = useState<Record<ModuleId, boolean>>({
    prompt: false, tools: false, mcp: false, skills: false, subagents: false, rules: false, memory: false,
  });

  // Search in tree
  const [treeSearch, setTreeSearch] = useState("");

  // Dialog state for adding items
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addDialogTarget, setAddDialogTarget] = useState<ModuleId>("tools");
  const [addName, setAddName] = useState("");
  const [addDesc, setAddDesc] = useState("");

  const statusLabels: Record<string, string> = { active: "在岗", draft: "草稿", inactive: "离线" };

  if (!staff) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">加载中...</p>
      </div>
    );
  }

  const getItemsForModule = (mod: ModuleId) => {
    if (mod === "tools") return staff.config.tools;
    if (mod === "mcp") return staff.config.mcps;
    if (mod === "skills") return staff.config.skills;
    if (mod === "subagents") return staff.config.subAgents.map(sa => ({ ...sa, enabled: true }));
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
    if (!addName.trim() || !staff) return;
    const newId = Date.now().toString();
    const newItem = { id: newId, name: addName.trim(), desc: addDesc.trim(), enabled: true };
    try {
      if (addDialogTarget === "tools") {
        await updateStaffConfig(staff.id, { tools: [...staff.config.tools, newItem] });
      } else if (addDialogTarget === "mcp") {
        await updateStaffConfig(staff.id, { mcps: [...staff.config.mcps, newItem] });
      } else if (addDialogTarget === "skills") {
        await updateStaffConfig(staff.id, { skills: [...staff.config.skills, newItem] });
      } else if (addDialogTarget === "subagents") {
        const newSa = { id: newId, name: addName.trim(), desc: addDesc.trim() };
        await updateStaffConfig(staff.id, { subAgents: [...staff.config.subAgents, newSa] });
      }
      toast.success(`${addName.trim()} 已添加`);
      setAddDialogOpen(false);
    } catch (e) {
      toast.error("添加失败，请重试");
    }
  };

  const handleDeleteItem = async (mod: ModuleId, itemId: string) => {
    if (!staff) return;
    try {
      if (mod === "tools") {
        await updateStaffConfig(staff.id, { tools: staff.config.tools.filter(i => i.id !== itemId) });
      } else if (mod === "mcp") {
        await updateStaffConfig(staff.id, { mcps: staff.config.mcps.filter(i => i.id !== itemId) });
      } else if (mod === "skills") {
        await updateStaffConfig(staff.id, { skills: staff.config.skills.filter(i => i.id !== itemId) });
      } else if (mod === "subagents") {
        await updateStaffConfig(staff.id, { subAgents: staff.config.subAgents.filter(i => i.id !== itemId) });
      }
      if ("itemId" in selection && selection.itemId === itemId) {
        setSelection({ module: mod } as Selection);
      }
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败，请重试");
    }
  };

  const handleToggle = async (mod: ModuleId, itemId: string, enabled: boolean) => {
    if (!staff) return;
    const update = (items: { id: string; name: string; desc: string; enabled: boolean }[]) =>
      items.map(i => i.id === itemId ? { ...i, enabled } : i);
    try {
      if (mod === "tools") {
        await updateStaffConfig(staff.id, { tools: update(staff.config.tools) });
      } else if (mod === "mcp") {
        await updateStaffConfig(staff.id, { mcps: update(staff.config.mcps) });
      } else if (mod === "skills") {
        await updateStaffConfig(staff.id, { skills: update(staff.config.skills) });
      }
    } catch (e) {
      toast.error("更新失败，请重试");
    }
  };

  // Filter tree items by search
  const filterItems = (items: { id: string; name: string }[]) => {
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
                    const isItemSelected = selection.module === mod.id && "itemId" in selection && selection.itemId === item.id;
                    return (
                      <div
                        key={item.id}
                        onClick={() => setSelection({ module: mod.id, itemId: item.id } as Selection)}
                        className={`flex items-center justify-between px-2 py-1.5 rounded-md text-xs cursor-pointer group/item transition-all ${
                          isItemSelected
                            ? "bg-primary/5 text-foreground font-medium"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        }`}
                      >
                        <span className="truncate flex-1">{item.name}</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteItem(mod.id, item.id); }}
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

    // Text editors (Prompt, Rules, Memory)
    if (mod === "prompt" || mod === "rules" || mod === "memory") {
      const labels: Record<string, string> = { prompt: "System Prompt", rules: "Rules", memory: "Memory" };
      return (
        <TextEditor
          key={mod}
          label={labels[mod]}
          initialValue={staff.config[mod] || ""}
          onSave={async (val) => {
            await updateStaffConfig(staff.id, { [mod]: val });
            toast.success(`${labels[mod]} 已保存`);
          }}
        />
      );
    }

    // CrudItem modules (tools, mcp, skills)
    if (mod === "tools" || mod === "mcp" || mod === "skills") {
      const configKey = mod === "tools" ? "tools" : mod === "mcp" ? "mcps" : "skills";
      const items = staff.config[configKey] as CrudItem[];
      const labels = { tools: "工具", mcp: "MCP", skills: "技能" };

      if (selectedItemId) {
        const item = items.find(i => i.id === selectedItemId);
        if (!item) return <div className="text-sm text-muted-foreground p-6">未找到该项</div>;
        return (
          <CrudItemEditor
            item={item}
            onSave={async (name, desc) => {
              await updateStaffConfig(staff.id, { [configKey]: items.map(i => i.id === selectedItemId ? { ...i, name, desc } : i) });
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
          onSelect={(itemId) => setSelection({ module: mod, itemId })}
          onDelete={(itemId) => handleDeleteItem(mod, itemId)}
          onToggle={(itemId, enabled) => handleToggle(mod, itemId, enabled)}
        />
      );
    }

    // Sub-agents
    if (mod === "subagents") {
      const saItems = staff.config.subAgents;
      if (selectedItemId) {
        const sa = saItems.find(i => i.id === selectedItemId);
        if (!sa) return <div className="text-sm text-muted-foreground p-6">未找到该项</div>;
        return (
          <SubAgentEditor
            item={sa}
            onSave={async (name, desc) => {
              await updateStaffConfig(staff.id, { subAgents: saItems.map(i => i.id === selectedItemId ? { ...i, name, desc } : i) });
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
          onSelect={(itemId) => setSelection({ module: "subagents", itemId })}
          onDelete={(itemId) => handleDeleteItem("subagents", itemId)}
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
          <button onClick={() => navigate("/staff")} className="p-1.5 rounded-md hover:bg-muted transition-colors shrink-0">
            <ArrowLeft className="w-4 h-4 text-muted-foreground" />
          </button>
          <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Bot className="w-4 h-4 text-primary" />
          </div>
          <h2 className="text-sm font-semibold text-foreground truncate">{staff.name}</h2>
          <div className="hidden md:flex items-center gap-1.5 ml-1">
            <div className={`w-1.5 h-1.5 rounded-full ${staff.status === "active" ? "bg-success" : staff.status === "draft" ? "bg-warning" : "bg-muted-foreground"}`} />
            <span className="text-[11px] text-muted-foreground">{statusLabels[staff.status] || staff.status}</span>
          </div>
          <span className="hidden md:inline text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded ml-2">v{staff.version}</span>
        </div>
        <div className="flex items-center gap-1 md:gap-2">
          <button onClick={() => navigate("/staff/" + id + "?history=true")} className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
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
            {showTest && <TestPanel staffName={staff.name} onClose={() => setShowTest(false)} />}
          </>
        )}
      </div>

      {/* Mobile test panel */}
      {isMobile && showTest && (
        <div className="fixed inset-0 z-50 bg-background flex flex-col">
          <TestPanel staffName={staff.name} onClose={() => setShowTest(false)} />
        </div>
      )}

      {/* Add Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              添加{addDialogTarget === "tools" ? "工具" : addDialogTarget === "mcp" ? "MCP" : addDialogTarget === "skills" ? "技能" : "Sub-agent"}
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

      <PublishDialog open={showPublish} onOpenChange={setShowPublish} staffId={staff.id} />
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
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
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
            key={item.id}
            className="flex items-center justify-between p-3 rounded-lg bg-card border border-border group cursor-pointer hover:border-primary/20 transition-colors"
            onClick={() => onSelect(item.id)}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">{item.name}</p>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
            <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
              <button onClick={() => onDelete(item.id)} className="p-1 rounded hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all" title="删除">
                <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
              </button>
              <Switch checked={item.enabled} onCheckedChange={checked => onToggle(item.id, checked)} />
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
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
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
            key={sa.id}
            className="flex items-center gap-3 p-3 rounded-lg bg-card border border-border group cursor-pointer hover:border-primary/20 transition-colors"
            onClick={() => onSelect(sa.id)}
          >
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">{sa.name}</p>
              <p className="text-xs text-muted-foreground">{sa.desc}</p>
            </div>
            <button
              onClick={e => { e.stopPropagation(); onDelete(sa.id); }}
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

