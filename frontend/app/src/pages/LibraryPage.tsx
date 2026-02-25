import { useState, useEffect } from "react";
import { Search, Plus, Zap, Plug, Bot, Edit, Trash2, AlertTriangle, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import SkillDetail from "@/components/SkillDetail";
import MCPDetail from "@/components/MCPDetail";
import AgentTemplateDetail from "@/components/AgentTemplateDetail";
import { toast } from "sonner";
import { useIsMobile } from "@/hooks/use-mobile";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAppStore } from "@/store/app-store";
import type { ResourceItem } from "@/store/types";

type ResourceType = "skills" | "mcp" | "agents";

const typeMap: Record<ResourceType, string> = { skills: "skill", mcp: "mcp", agents: "agent" };

const tabs: { id: ResourceType; label: string; icon: typeof Zap }[] = [
  { id: "skills", label: "技能", icon: Zap },
  { id: "mcp", label: "MCP 服务", icon: Plug },
  { id: "agents", label: "Agent 模板", icon: Bot },
];

export default function LibraryPage() {
  const isMobile = useIsMobile();
  const librarySkills = useAppStore((s) => s.librarySkills);
  const libraryMcps = useAppStore((s) => s.libraryMcps);
  const libraryAgents = useAppStore((s) => s.libraryAgents);
  const loadAll = useAppStore((s) => s.loadAll);
  const error = useAppStore((s) => s.error);
  const retry = useAppStore((s) => s.retry);
  const storeAddResource = useAppStore((s) => s.addResource);
  const storeUpdateResource = useAppStore((s) => s.updateResource);
  const storeDeleteResource = useAppStore((s) => s.deleteResource);
  const getResourceUsedBy = useAppStore((s) => s.getResourceUsedBy);

  useEffect(() => { loadAll(); }, [loadAll]);

  const [tab, setTab] = useState<ResourceType>("skills");
  const [search, setSearch] = useState("");
  const [selectedSkill, setSelectedSkill] = useState<ResourceItem | null>(null);
  const [selectedMCP, setSelectedMCP] = useState<ResourceItem | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<ResourceItem | null>(null);

  // Dialog state
  const [formOpen, setFormOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<ResourceItem | null>(null);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formCategory, setFormCategory] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingItem, setDeletingItem] = useState<ResourceItem | null>(null);

  const getList = () => tab === "skills" ? librarySkills : tab === "mcp" ? libraryMcps : libraryAgents;

  const items = getList();
  const filtered = items.filter((i) => i.name.toLowerCase().includes(search.toLowerCase()));
  const Icon = tab === "skills" ? Zap : tab === "mcp" ? Plug : Bot;

  const handleCardClick = (item: ResourceItem) => {
    if (tab === "skills") { setSelectedSkill(item); setSelectedMCP(null); setSelectedAgent(null); }
    else if (tab === "mcp") { setSelectedMCP(item); setSelectedSkill(null); setSelectedAgent(null); }
    else { setSelectedAgent(item); setSelectedSkill(null); setSelectedMCP(null); }
  };

  const openCreate = () => {
    setEditingItem(null);
    setFormName("");
    setFormDesc("");
    setFormCategory("");
    setFormOpen(true);
  };

  const openEdit = (item: ResourceItem) => {
    setEditingItem(item);
    setFormName(item.name);
    setFormDesc(item.desc);
    setFormCategory(item.category);
    setFormOpen(true);
  };

  const handleSaveForm = async () => {
    if (!formName.trim()) return;
    try {
      if (editingItem) {
        await storeUpdateResource(typeMap[tab], editingItem.id, { name: formName.trim(), desc: formDesc.trim(), category: formCategory.trim() });
        toast.success(`${formName.trim()} 已更新`);
      } else {
        await storeAddResource(typeMap[tab], formName.trim(), formDesc.trim(), formCategory.trim() || "未分类");
        toast.success(`${formName.trim()} 已创建`);
      }
      setFormOpen(false);
    } catch (e: unknown) {
      toast.error("操作失败: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const openDelete = (item: ResourceItem) => {
    setDeletingItem(item);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingItem) return;
    try {
      await storeDeleteResource(typeMap[tab], deletingItem.id);
      if (selectedSkill?.id === deletingItem.id) setSelectedSkill(null);
      if (selectedMCP?.id === deletingItem.id) setSelectedMCP(null);
      if (selectedAgent?.id === deletingItem.id) setSelectedAgent(null);
      toast.success(`${deletingItem.name} 已删除`);
      setDeleteDialogOpen(false);
    } catch (e: unknown) {
      toast.error("删除失败: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const showDetail = selectedSkill || selectedMCP || selectedAgent;

  return (
    <div className="flex h-full">
      {/* Sidebar tabs - desktop */}
      {!isMobile && (
        <div className="w-[200px] shrink-0 border-r border-border bg-card flex flex-col">
          <div className="h-14 flex items-center justify-between px-4 border-b border-border">
            <h2 className="text-sm font-semibold text-foreground">能力库</h2>
          </div>
          <div className="flex-1 p-2 space-y-0.5">
            {tabs.map((t) => {
              const count = (t.id === "skills" ? librarySkills : t.id === "mcp" ? libraryMcps : libraryAgents).length;
              const isActive = tab === t.id;
              return (
                <button key={t.id} onClick={() => { setTab(t.id); setSearch(""); setSelectedSkill(null); setSelectedMCP(null); }} className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-all ${
                  isActive ? "bg-primary/5 text-foreground border border-primary/15" : "text-muted-foreground hover:bg-muted hover:text-foreground border border-transparent"
                }`}>
                  <div className="flex items-center gap-2.5"><t.icon className={`w-4 h-4 ${isActive ? "text-primary" : ""}`} /><span>{t.label}</span></div>
                  <span className={`text-xs font-mono ${isActive ? "text-primary" : ""}`}>{count}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-hidden bg-background">
        {/* Content header bar */}
        <div className="h-14 flex items-center justify-between px-4 md:px-6 border-b border-border shrink-0">
          <div className="flex items-center gap-3">
            {/* Mobile tabs */}
            {isMobile && (
              <div className="flex gap-1 overflow-x-auto">
                {tabs.map((t) => {
                  const isActive = tab === t.id;
                  return (
                    <button key={t.id} onClick={() => { setTab(t.id); setSearch(""); setSelectedSkill(null); setSelectedMCP(null); setSelectedAgent(null); }} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
                      isActive ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    }`}>
                      <t.icon className="w-3.5 h-3.5" />{t.label}
                    </button>
                  );
                })}
              </div>
            )}
            {!isMobile && (
              <>
                <h3 className="text-sm font-semibold text-foreground">
                  {tab === "skills" ? "技能" : tab === "mcp" ? "MCP 服务" : "Agent 模板"}
                </h3>
                <span className="text-xs text-muted-foreground font-mono">{items.length}</span>
              </>
            )}
          </div>
          <button onClick={openCreate} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity">
            <Plus className="w-4 h-4" />
            <span className="hidden md:inline">新建</span>
          </button>
        </div>

        <div className={`flex-1 overflow-y-auto`}>
          <div className={`${showDetail && !isMobile ? "max-w-xl" : "max-w-2xl"} mx-auto py-6 px-4 md:px-6`}>

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="搜索..." className="w-full pl-9 pr-3 py-2 rounded-lg bg-card border border-border text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary/40 transition-colors" />
          </div>

          {/* Grid */}
          {error ? (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-destructive" />
              </div>
              <p className="text-sm font-medium text-foreground mb-1">加载失败</p>
              <p className="text-xs text-muted-foreground mb-4 max-w-xs text-center">{error}</p>
              <button onClick={retry} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-opacity">
                <RefreshCw className="w-3.5 h-3.5" />重试
              </button>
            </div>
          ) : (<>
          <div className={`grid ${isMobile ? "grid-cols-1" : "grid-cols-2"} gap-3`}>
            {filtered.map((item) => (
              <div key={item.id} onClick={() => handleCardClick(item)} className={`surface-interactive p-4 cursor-pointer group relative ${
                (selectedSkill?.id === item.id || selectedMCP?.id === item.id || selectedAgent?.id === item.id) ? "border-primary/40 glow-sm" : ""
              }`}>
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-primary/8 flex items-center justify-center shrink-0">
                    <Icon className="w-4 h-4 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{item.name}</h4>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{item.category}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{item.desc}</p>
                    <p className="text-[11px] text-muted-foreground mt-2">被 <span className="text-foreground font-medium">{getResourceUsedBy(typeMap[tab], item.name)}</span> 位员工使用</p>
                  </div>
                </div>
                {/* Edit/Delete hover actions */}
                <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={(e) => { e.stopPropagation(); openEdit(item); }} className="p-1 rounded hover:bg-muted transition-colors" title="编辑">
                    <Edit className="w-3 h-3 text-muted-foreground" />
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); openDelete(item); }} className="p-1 rounded hover:bg-destructive/10 transition-colors" title="删除">
                    <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          {filtered.length === 0 && (
            <div className="text-center py-12 text-sm text-muted-foreground">未找到相关内容</div>
          )}
          </>)}
        </div>
        </div>
      </div>

      {/* Detail panels */}
      {!isMobile && selectedSkill && <SkillDetail skill={selectedSkill} onClose={() => setSelectedSkill(null)} />}
      {!isMobile && selectedMCP && <MCPDetail mcp={selectedMCP} onClose={() => setSelectedMCP(null)} />}
      {!isMobile && selectedAgent && <AgentTemplateDetail agent={selectedAgent} onClose={() => setSelectedAgent(null)} />}

      {isMobile && selectedSkill && (
        <div className="fixed inset-0 z-50 bg-background overflow-y-auto">
          <SkillDetail skill={selectedSkill} onClose={() => setSelectedSkill(null)} />
        </div>
      )}
      {isMobile && selectedMCP && (
        <div className="fixed inset-0 z-50 bg-background overflow-y-auto">
          <MCPDetail mcp={selectedMCP} onClose={() => setSelectedMCP(null)} />
        </div>
      )}
      {isMobile && selectedAgent && (
        <div className="fixed inset-0 z-50 bg-background overflow-y-auto">
          <AgentTemplateDetail agent={selectedAgent} onClose={() => setSelectedAgent(null)} />
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editingItem ? "编辑" : "新建"}{tab === "skills" ? "技能" : tab === "mcp" ? " MCP 服务" : " Agent 模板"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="名称" />
            <Input value={formDesc} onChange={(e) => setFormDesc(e.target.value)} placeholder="描述" />
            <Input value={formCategory} onChange={(e) => setFormCategory(e.target.value)} placeholder="分类" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)}>取消</Button>
            <Button onClick={handleSaveForm} disabled={!formName.trim()}>{editingItem ? "更新" : "创建"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>确定要删除 "{deletingItem?.name}" 吗？此操作不可撤销。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}


