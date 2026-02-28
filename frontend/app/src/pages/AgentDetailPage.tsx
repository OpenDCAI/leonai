import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Bot, FileText, Wrench, Plug, Zap, Users, BookOpen,
  Play, Tag, Save, Plus, Trash2, Search, X, Check,
} from "lucide-react";
import TestPanel from "@/components/TestPanel";
import PublishDialog from "@/components/PublishDialog";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useAppStore } from "@/store/app-store";
import type { CrudItem, RuleItem, ResourceItem } from "@/store/types";

// ==================== Types ====================

type ModuleId = "prompt" | "tools" | "mcp" | "skills" | "subagents" | "rules";

interface ModuleDef {
  id: ModuleId;
  label: string;
  icon: typeof FileText;
  count?: (cfg: any) => number;
}

const modules: ModuleDef[] = [
  { id: "prompt", label: "System Prompt", icon: FileText },
  { id: "tools", label: "Tools", icon: Wrench, count: c => c.tools.length },
  { id: "mcp", label: "MCP", icon: Plug, count: c => c.mcps.length },
  { id: "skills", label: "Skills", icon: Zap, count: c => c.skills.length },
  { id: "subagents", label: "Agents", icon: Users, count: c => c.subAgents.length },
  { id: "rules", label: "Rules", icon: BookOpen, count: c => c.rules.length },
];

// ==================== Main Component ====================

export default function AgentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [showTest, setShowTest] = useState(false);
  const [showPublish, setShowPublish] = useState(false);
  const [activeModule, setActiveModule] = useState<ModuleId>("prompt");

  const member = useAppStore(s => s.getMemberById(id || ""));
  const updateMemberConfig = useAppStore(s => s.updateMemberConfig);
  const loadAll = useAppStore(s => s.loadAll);
  const librarySkills = useAppStore(s => s.librarySkills);
  const libraryMcps = useAppStore(s => s.libraryMcps);
  const libraryAgents = useAppStore(s => s.libraryAgents);
  useEffect(() => { loadAll(); }, [loadAll]);

  const [pickerType, setPickerType] = useState<"skill" | "mcp" | "agent" | null>(null);

  const statusLabels: Record<string, string> = { active: "在岗", draft: "草稿", inactive: "离线" };

  if (!member) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">加载中...</p>
      </div>
    );
  }

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
    } catch { toast.error("更新失败"); }
  };

  const handleAssign = async (type: "skill" | "mcp" | "agent", names: string[]) => {
    if (!member) return;
    try {
      if (type === "skill") {
        const existing = new Set(member.config.skills.map(s => s.name));
        const newSkills = names.filter(n => !existing.has(n)).map(n => {
          const lib = librarySkills.find(s => s.name === n);
          return { name: n, desc: lib?.desc || "", enabled: true };
        });
        if (newSkills.length) await updateMemberConfig(member.id, { skills: [...member.config.skills, ...newSkills] });
      } else if (type === "mcp") {
        const existing = new Set(member.config.mcps.map(m => m.name));
        const newMcps = names.filter(n => !existing.has(n)).map(n => {
          const lib = libraryMcps.find(m => m.name === n);
          return { name: n, command: lib?.desc || "", args: [], env: {}, disabled: false };
        });
        if (newMcps.length) await updateMemberConfig(member.id, { mcps: [...member.config.mcps, ...newMcps] });
      } else {
        const existing = new Set(member.config.subAgents.map(a => a.name));
        const newAgents = names.filter(n => !existing.has(n)).map(n => {
          const lib = libraryAgents.find(a => a.name === n);
          return { name: n, desc: lib?.desc || "" };
        });
        if (newAgents.length) await updateMemberConfig(member.id, { subAgents: [...member.config.subAgents, ...newAgents] });
      }
      toast.success("已添加");
    } catch { toast.error("添加失败"); }
  };

  const handleRemove = async (mod: ModuleId, itemName: string) => {
    if (!member) return;
    try {
      if (mod === "mcp") await updateMemberConfig(member.id, { mcps: member.config.mcps.filter(i => i.name !== itemName) });
      else if (mod === "skills") await updateMemberConfig(member.id, { skills: member.config.skills.filter(i => i.name !== itemName) });
      else if (mod === "subagents") await updateMemberConfig(member.id, { subAgents: member.config.subAgents.filter(i => i.name !== itemName) });
      else if (mod === "rules") await updateMemberConfig(member.id, { rules: member.config.rules.filter(i => i.name !== itemName) });
      toast.success("已移除");
    } catch { toast.error("移除失败"); }
  };

  const renderContent = () => {
    switch (activeModule) {
      case "prompt":
        return (
          <PromptEditor
            value={member.config.prompt || ""}
            onSave={async (val) => {
              await updateMemberConfig(member.id, { prompt: val });
              toast.success("System Prompt 已保存");
            }}
          />
        );
      case "tools":
        return <ToolsGrid items={member.config.tools} onToggle={(name, en) => handleToggle("tools", name, en)} />;
      case "rules":
        return (
          <RulesPanel
            rules={member.config.rules}
            onSave={async (name, content) => {
              await updateMemberConfig(member.id, { rules: member.config.rules.map(r => r.name === name ? { ...r, content } : r) });
              toast.success("规则已保存");
            }}
            onAdd={async (name) => {
              await updateMemberConfig(member.id, { rules: [...member.config.rules, { name, content: "" }] });
              toast.success(`${name} 已添加`);
            }}
            onDelete={(name) => handleRemove("rules", name)}
          />
        );
      case "skills":
        return (
          <ResourceCards
            type="skill"
            items={member.config.skills.map(s => ({ name: s.name, desc: s.desc, enabled: s.enabled }))}
            onToggle={(name, en) => handleToggle("skills", name, en)}
            onRemove={(name) => handleRemove("skills", name)}
            onAdd={() => setPickerType("skill")}
          />
        );
      case "mcp":
        return (
          <ResourceCards
            type="mcp"
            items={member.config.mcps.map(m => ({ name: m.name, desc: m.command || "未配置", enabled: !m.disabled }))}
            onToggle={(name, en) => handleToggle("mcp", name, en)}
            onRemove={(name) => handleRemove("mcp", name)}
            onAdd={() => setPickerType("mcp")}
          />
        );
      case "subagents":
        return (
          <ResourceCards
            type="agent"
            items={member.config.subAgents.map(a => ({ name: a.name, desc: a.desc }))}
            onRemove={(name) => handleRemove("subagents", name)}
            onAdd={() => setPickerType("agent")}
          />
        );
      default: return null;
    }
  };
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b shrink-0">
        <Button variant="ghost" size="icon" onClick={() => navigate("/members")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Bot className="h-5 w-5 text-primary" />
        <span className="font-medium">{member.name}</span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
          {statusLabels[member.status] || member.status}
        </span>
        <span className="text-xs text-muted-foreground">v{member.version}</span>
        <div className="flex-1" />
        <Button size="sm" variant="outline" onClick={() => setShowTest(true)}>
          <Play className="h-3.5 w-3.5 mr-1" /> 测试
        </Button>
        <Button size="sm" onClick={() => setShowPublish(true)}>
          <Tag className="h-3.5 w-3.5 mr-1" /> 发布
        </Button>
      </div>

      {/* Body: sidebar + content */}
      <div className="flex-1 flex min-h-0">
        {/* Flat sidebar */}
        <nav className="w-48 shrink-0 border-r bg-muted/30 py-2">
          {modules.map(m => {
            const Icon = m.icon;
            const count = m.count ? m.count(member.config) : undefined;
            const active = activeModule === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setActiveModule(m.id)}
                className={`w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors ${
                  active ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:bg-muted"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{m.label}</span>
                {count !== undefined && (
                  <span className="ml-auto text-xs opacity-60">{count}</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0 overflow-auto">
          {renderContent()}
        </div>
      </div>

      {showTest && <TestPanel memberName={member.name} onClose={() => setShowTest(false)} />}
      {showPublish && <PublishDialog open={showPublish} onOpenChange={setShowPublish} memberId={member.id} />}
      {pickerType && (
        <ResourcePicker
          type={pickerType}
          library={pickerType === "skill" ? librarySkills : pickerType === "mcp" ? libraryMcps : libraryAgents}
          assigned={pickerType === "skill" ? member.config.skills.map(s => s.name) : pickerType === "mcp" ? member.config.mcps.map(m => m.name) : member.config.subAgents.map(a => a.name)}
          onConfirm={(names) => { handleAssign(pickerType, names); setPickerType(null); }}
          onClose={() => setPickerType(null)}
        />
      )}
    </div>
  );
}

// ==================== PromptEditor ====================

function PromptEditor({ value, onSave }: { value: string; onSave: (v: string) => Promise<void> }) {
  const [text, setText] = useState(value);
  const [saving, setSaving] = useState(false);
  const dirty = text !== value;

  useEffect(() => { setText(value); }, [value]);

  const save = async () => {
    setSaving(true);
    try { await onSave(text); } finally { setSaving(false); }
  };

  return (
    <div className="h-full flex flex-col p-4 gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">System Prompt</h3>
        <Button size="sm" disabled={!dirty || saving} onClick={save}>
          <Save className="h-3.5 w-3.5 mr-1" /> {saving ? "保存中..." : "保存"}
        </Button>
      </div>
      <textarea
        className="flex-1 w-full rounded-md border bg-background px-3 py-2 text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="输入 System Prompt..."
      />
    </div>
  );
}

// ==================== ToolsGrid ====================

function ToolsGrid({ items, onToggle }: { items: CrudItem[]; onToggle: (name: string, enabled: boolean) => void }) {
  const [filter, setFilter] = useState("");
  const groups = useMemo(() => {
    const map: Record<string, CrudItem[]> = {};
    for (const t of items) {
      if (filter && !t.name.toLowerCase().includes(filter.toLowerCase())) continue;
      const g = t.group || "other";
      (map[g] ??= []).push(t);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [items, filter]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium">Tools</h3>
        <span className="text-xs text-muted-foreground">{items.length} 个工具</span>
        <div className="flex-1" />
        <div className="relative w-48">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input className="pl-8 h-8 text-xs" placeholder="搜索工具..." value={filter} onChange={e => setFilter(e.target.value)} />
        </div>
      </div>
      {groups.map(([group, tools]) => (
        <div key={group}>
          <p className="text-xs font-medium text-muted-foreground uppercase mb-2">{group}</p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
            {tools.map(t => (
              <div key={t.name} className="flex items-center gap-2 rounded-md border px-3 py-2 text-xs">
                <Wrench className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">{t.name}</p>
                  {t.desc && <p className="text-muted-foreground truncate">{t.desc}</p>}
                </div>
                <Switch checked={t.enabled} onCheckedChange={v => onToggle(t.name, v)} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ==================== RulesPanel ====================

function RulesPanel({ rules, onSave, onAdd, onDelete }: {
  rules: RuleItem[];
  onSave: (name: string, content: string) => Promise<void>;
  onAdd: (name: string) => Promise<void>;
  onDelete: (name: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(rules[0]?.name ?? null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [addName, setAddName] = useState("");

  const current = rules.find(r => r.name === selected);
  useEffect(() => { setText(current?.content ?? ""); }, [current]);

  const dirty = current ? text !== current.content : false;

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    try { await onSave(selected, text); } finally { setSaving(false); }
  };

  const doAdd = async () => {
    const n = addName.trim();
    if (!n) return;
    await onAdd(n.endsWith(".md") ? n : `${n}.md`);
    setAddName("");
    setAddOpen(false);
    setSelected(n.endsWith(".md") ? n : `${n}.md`);
  };

  return (
    <div className="h-full flex">
      {/* File list */}
      <div className="w-48 shrink-0 border-r flex flex-col">
        <div className="flex items-center justify-between px-3 py-2 border-b">
          <span className="text-xs font-medium text-muted-foreground">规则文件</span>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setAddOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
          </Button>
        </div>
        <div className="flex-1 overflow-auto py-1">
          {rules.map(r => (
            <button
              key={r.name}
              onClick={() => setSelected(r.name)}
              className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs ${
                selected === r.name ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"
              }`}
            >
              <BookOpen className="h-3 w-3 shrink-0" />
              <span className="truncate">{r.name}</span>
            </button>
          ))}
        </div>
      </div>
      {/* Editor */}
      <div className="flex-1 flex flex-col p-4 gap-2 min-w-0">
        {current ? (
          <>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium truncate">{current.name}</span>
              <div className="flex-1" />
              <Button variant="ghost" size="sm" className="text-destructive h-7" onClick={() => { onDelete(current.name); setSelected(rules.find(r => r.name !== current.name)?.name ?? null); }}>
                <Trash2 className="h-3.5 w-3.5 mr-1" /> 删除
              </Button>
              <Button size="sm" className="h-7" disabled={!dirty || saving} onClick={save}>
                <Save className="h-3.5 w-3.5 mr-1" /> {saving ? "..." : "保存"}
              </Button>
            </div>
            <textarea
              className="flex-1 w-full rounded-md border bg-background px-3 py-2 text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              value={text}
              onChange={e => setText(e.target.value)}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            {rules.length ? "选择一个规则文件" : "暂无规则，点击 + 添加"}
          </div>
        )}
      </div>
      {/* Add dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader><DialogTitle>添加规则文件</DialogTitle></DialogHeader>
          <Input placeholder="文件名，如 coding.md" value={addName} onChange={e => setAddName(e.target.value)} onKeyDown={e => e.key === "Enter" && doAdd()} />
          <DialogFooter><Button size="sm" onClick={doAdd} disabled={!addName.trim()}>添加</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ==================== ResourceCards ====================

interface ResourceCardItem {
  name: string;
  desc?: string;
  enabled?: boolean;
}

function ResourceCards({ type, items, onToggle, onRemove, onAdd }: {
  type: "skill" | "mcp" | "agent";
  items: ResourceCardItem[];
  onToggle?: (name: string, enabled: boolean) => void;
  onRemove?: (name: string) => void;
  onAdd?: () => void;
}) {
  const labels = { skill: "Skills", mcp: "MCP Servers", agent: "Agents" };
  const icons = { skill: Zap, mcp: Plug, agent: Users };
  const Icon = icons[type];

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium">{labels[type]}</h3>
        <span className="text-xs text-muted-foreground">{items.length} 项</span>
        {onAdd && (
          <Button variant="ghost" size="icon" className="h-6 w-6 ml-auto" onClick={onAdd}>
            <Plus className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground py-8 text-center">
          {onAdd ? (
            <button onClick={onAdd} className="hover:text-primary transition-colors">
              点击 + 从 Library 添加{labels[type]}
            </button>
          ) : (
            <>暂无{labels[type]}</>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
          {items.map(item => (
            <div key={item.name} className="flex items-start gap-2 rounded-md border px-3 py-2.5">
              <Icon className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate">{item.name}</p>
                {item.desc && <p className="text-xs text-muted-foreground truncate">{item.desc}</p>}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {onToggle && item.enabled !== undefined && (
                  <Switch checked={item.enabled} onCheckedChange={v => onToggle(item.name, v)} />
                )}
                {onRemove && (
                  <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive" onClick={() => onRemove(item.name)}>
                    <X className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== ResourcePicker ====================

function ResourcePicker({ type, library, assigned, onConfirm, onClose }: {
  type: "skill" | "mcp" | "agent";
  library: ResourceItem[];
  assigned: string[];
  onConfirm: (names: string[]) => void;
  onClose: () => void;
}) {
  const labels = { skill: "Skill", mcp: "MCP", agent: "Agent" };
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState("");
  const assignedSet = useMemo(() => new Set(assigned), [assigned]);

  const available = useMemo(() =>
    library.filter(item => !assignedSet.has(item.name) && (!filter || item.name.toLowerCase().includes(filter.toLowerCase()))),
    [library, assignedSet, filter]
  );

  const toggle = (name: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>从 Library 添加 {labels[type]}</DialogTitle>
        </DialogHeader>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input className="pl-8 h-8 text-xs" placeholder="搜索..." value={filter} onChange={e => setFilter(e.target.value)} />
        </div>
        <div className="max-h-64 overflow-auto space-y-1">
          {available.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">
              {library.length === 0 ? "Library 中暂无资源，请先去 Library 创建" : "没有可添加的资源"}
            </p>
          ) : available.map(item => (
            <button
              key={item.id}
              onClick={() => toggle(item.name)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left transition-colors ${
                selected.has(item.name) ? "bg-primary/10 text-primary" : "hover:bg-muted"
              }`}
            >
              <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                selected.has(item.name) ? "bg-primary border-primary" : "border-muted-foreground/30"
              }`}>
                {selected.has(item.name) && <Check className="h-3 w-3 text-primary-foreground" />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-medium truncate">{item.name}</p>
                {item.desc && <p className="text-xs text-muted-foreground truncate">{item.desc}</p>}
              </div>
            </button>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>取消</Button>
          <Button size="sm" disabled={selected.size === 0} onClick={() => onConfirm([...selected])}>
            添加 {selected.size > 0 && `(${selected.size})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
