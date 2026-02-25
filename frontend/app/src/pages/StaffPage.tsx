import { useState, useEffect } from "react";
import { Search, Bot, Plus, Zap, Users, Wrench, Plug, SearchX, ArrowUpDown, AlertTriangle, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import CreateStaffDialog from "@/components/CreateStaffDialog";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useIsMobile } from "@/hooks/use-mobile";
import { useAppStore } from "@/store/app-store";

const statusConfig = {
  active: { label: "在岗", dot: "bg-success", shape: "rounded-full" },
  draft: { label: "草稿", dot: "bg-warning", shape: "rounded-sm" },
  inactive: { label: "离线", dot: "bg-muted-foreground", shape: "rounded-full opacity-50" },
};

const avatarColors = [
  "bg-primary/15 text-primary",
  "bg-success/15 text-success",
  "bg-warning/15 text-warning",
  "bg-destructive/15 text-destructive",
  "bg-chart-1/15 text-chart-1",
  "bg-accent text-accent-foreground",
];

type SortKey = "name" | "skills" | "status" | null;

export default function Staff() {
  const isMobile = useIsMobile();
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "draft" | "inactive">("all");
  const [sortBy, setSortBy] = useState<SortKey>(null);
  const navigate = useNavigate();
  const staffList = useAppStore(s => s.staffList);
  const loadAll = useAppStore(s => s.loadAll);
  const error = useAppStore(s => s.error);
  const retry = useAppStore(s => s.retry);

  useEffect(() => { loadAll(); }, [loadAll]);

  let filtered = staffList.filter((s) => {
    if (statusFilter !== "all" && s.status !== statusFilter) return false;
    if (search && !s.name.toLowerCase().includes(search.toLowerCase()) && !s.role.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  if (sortBy === "name") filtered = [...filtered].sort((a, b) => a.name.localeCompare(b.name));
  else if (sortBy === "skills") filtered = [...filtered].sort((a, b) => b.config.skills.length - a.config.skills.length);
  else if (sortBy === "status") {
    const order = { active: 0, draft: 1, inactive: 2 };
    filtered = [...filtered].sort((a, b) => order[a.status] - order[b.status]);
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 md:px-6 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-foreground">员工</h2>
          <span className="text-xs text-muted-foreground font-mono">{staffList.length}</span>
        </div>
        <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity">
          <Plus className="w-4 h-4" />
          <span className="hidden md:inline">创建员工</span>
        </button>
      </div>

      {/* Filters */}
      <div className={`px-4 md:px-6 py-3 border-b border-border flex items-center gap-3 ${isMobile ? "overflow-x-auto" : "gap-4"}`}>
        <div className={`relative ${isMobile ? "min-w-[150px] flex-1" : "max-w-md flex-1"}`}>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="搜索员工..." className="w-full pl-9 pr-3 py-2 rounded-lg bg-card border border-border text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary/40 transition-colors" />
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {(["all", "active", "draft", "inactive"] as const).map((s) => {
            const count = s === "all" ? staffList.length : staffList.filter((st) => st.status === s).length;
            return (
              <button key={s} onClick={() => setStatusFilter(s)} className={`px-2 py-1 rounded-md text-xs transition-colors whitespace-nowrap ${
                statusFilter === s ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}>
                {s === "all" ? "全部" : statusConfig[s].label}
                {!isMobile && <span className="ml-1 font-mono">{count}</span>}
              </button>
            );
          })}
        </div>

        {!isMobile && (
          <button
            onClick={() => setSortBy(sortBy === "name" ? "skills" : sortBy === "skills" ? "status" : sortBy === "status" ? null : "name")}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
          >
            <ArrowUpDown className="w-3 h-3" />
            {sortBy ? `排序: ${sortBy === "name" ? "名称" : sortBy === "skills" ? "技能数" : "状态"}` : "排序"}
          </button>
        )}
      </div>

      {/* Card Grid */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
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
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <SearchX className="w-12 h-12 text-muted-foreground mb-4" />
            <p className="text-sm font-medium text-foreground mb-1">未找到员工</p>
            <p className="text-xs text-muted-foreground mb-3">
              {search || statusFilter !== "all" ? "尝试调整搜索词或筛选条件" : "创建你的第一个 AI 员工"}
            </p>
            {!search && statusFilter === "all" && (
              <button onClick={() => setCreateOpen(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-opacity">
                <Plus className="w-3.5 h-3.5" />创建员工
              </button>
            )}
          </div>
        ) : (
          <div className={`grid gap-4 ${isMobile ? "grid-cols-1" : "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"}`}>
            {filtered.map((staff, index) => {
              const status = statusConfig[staff.status];
              const colorClass = avatarColors[index % avatarColors.length];
              const initials = staff.name.split(" ").map((w) => w[0]).join("").slice(0, 2);
              return (
                <div key={staff.id} onClick={() => navigate(`/staff/${staff.id}`)} className="surface-interactive p-4 cursor-pointer group" role="button" aria-label={`查看员工 ${staff.name}`} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && navigate(`/staff/${staff.id}`)}>
                  <div className="flex items-start justify-between mb-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold font-mono ${colorClass}`}>{initials}</div>
                    <div className="flex items-center gap-1.5">
                      <div className={`w-1.5 h-1.5 ${status.shape} ${status.dot}`} />
                      <span className="text-[11px] text-muted-foreground">{status.label}</span>
                    </div>
                  </div>
                  <h3 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors mb-0.5">{staff.name}</h3>
                  <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{staff.description}</p>
                  <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                    <Tooltip><TooltipTrigger asChild><span className="flex items-center gap-1 cursor-default"><Zap className="w-3 h-3" /> {staff.config.skills.length}</span></TooltipTrigger><TooltipContent side="bottom"><p>技能数</p></TooltipContent></Tooltip>
                    <Tooltip><TooltipTrigger asChild><span className="flex items-center gap-1 cursor-default"><Wrench className="w-3 h-3" /> {staff.config.tools.length}</span></TooltipTrigger><TooltipContent side="bottom"><p>工具数</p></TooltipContent></Tooltip>
                    <Tooltip><TooltipTrigger asChild><span className="flex items-center gap-1 cursor-default"><Plug className="w-3 h-3" /> {staff.config.mcps.length}</span></TooltipTrigger><TooltipContent side="bottom"><p>MCP 服务</p></TooltipContent></Tooltip>
                    <Tooltip><TooltipTrigger asChild><span className="flex items-center gap-1 cursor-default"><Users className="w-3 h-3" /> {staff.config.subAgents.length}</span></TooltipTrigger><TooltipContent side="bottom"><p>Sub-agents</p></TooltipContent></Tooltip>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <CreateStaffDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
