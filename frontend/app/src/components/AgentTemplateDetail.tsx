import { X, Bot, Users, Calendar, Tag } from "lucide-react";
import { useAppStore } from "@/store/app-store";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";

interface Props {
  agent: { id: string; name: string; desc: string; category: string; updated_at?: number };
  onClose: () => void;
}

export default function AgentTemplateDetail({ agent, onClose }: Props) {
  const getResourceUsedBy = useAppStore((s) => s.getResourceUsedBy);
  const usedBy = getResourceUsedBy("agent", agent.name);
  const updatedText = agent.updated_at
    ? formatDistanceToNow(new Date(agent.updated_at), { addSuffix: true, locale: zhCN })
    : "3 天前";
  return (
    <div className="w-[340px] shrink-0 border-l border-border bg-card overflow-y-auto">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">{agent.name}</h3>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
      <div className="p-4 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Bot className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">{agent.name}</p>
            <p className="text-xs text-muted-foreground">{agent.desc}</p>
          </div>
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Tag className="w-3.5 h-3.5" /> 分类: <span className="text-foreground">{agent.category}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="w-3.5 h-3.5" /> 引用: <span className="text-foreground">{usedBy} 位成员</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Calendar className="w-3.5 h-3.5" /> 更新于 {updatedText}
          </div>
        </div>
        <div className="pt-2 border-t border-border">
          <p className="text-xs font-medium text-foreground mb-2">模板说明</p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            此 Agent 模板可被成员引用，作为子代理或能力来源。模板定义了基础 Prompt、默认工具集和行为规则。
          </p>
        </div>
      </div>
    </div>
  );
}
