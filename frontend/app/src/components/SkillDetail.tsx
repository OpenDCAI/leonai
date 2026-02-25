import { X, Folder, FileText, Users, Calendar, Tag } from "lucide-react";
import { useAppStore } from "@/store/app-store";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";

interface Props {
  skill: { id: string; name: string; desc: string; category: string; updated_at?: number };
  onClose: () => void;
}

const mockFiles = [
  { name: "skill.md", type: "file" },
  { name: "examples/", type: "folder" },
  { name: "examples/basic.md", type: "file" },
  { name: "config.json", type: "file" },
];

const mockContent = `# 代码审查 Skill

## 概述
深度代码审查，覆盖质量、性能、安全三个维度。

## 审查维度
1. **代码质量** - 命名规范、函数复杂度、重复代码
2. **性能** - N+1 查询、内存泄漏、不必要的重渲染
3. **安全** - SQL 注入、XSS、敏感信息泄露

## 输出格式
\`\`\`markdown
### 问题 #1
- **级别**: warning
- **位置**: src/utils.ts:42
- **描述**: 未处理的 Promise rejection
- **建议**: 添加 try-catch 或 .catch() 处理
\`\`\``;

export default function SkillDetail({ skill, onClose }: Props) {
  const getResourceUsedBy = useAppStore((s) => s.getResourceUsedBy);
  const usedBy = getResourceUsedBy("skill", skill.name);
  const updatedText = skill.updated_at
    ? formatDistanceToNow(new Date(skill.updated_at), { addSuffix: true, locale: zhCN })
    : "3 天前";
  return (
    <div className="w-[400px] shrink-0 border-l border-border bg-card flex flex-col overflow-hidden">
      <div className="h-12 flex items-center justify-between px-4 border-b border-border shrink-0">
        <h3 className="text-sm font-semibold text-foreground">{skill.name}</h3>
        <button onClick={onClose} className="p-1 rounded-md hover:bg-muted transition-colors">
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        <div>
          <p className="text-sm text-muted-foreground">{skill.desc}</p>
          <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><Tag className="w-3 h-3" /> {skill.category}</span>
            <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {usedBy} 位员工使用</span>
            <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {updatedText}</span>
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-foreground mb-2">来源</p>
          <div className="px-3 py-2 rounded-lg bg-muted text-xs font-mono text-muted-foreground">
            internal/skills/code-review
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-foreground mb-2">文件结构</p>
          <div className="rounded-lg border border-border bg-background overflow-hidden">
            {mockFiles.map((f, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-1.5 text-xs border-b border-border last:border-0 hover:bg-muted/50 transition-colors">
                {f.type === "folder" ? (
                  <Folder className="w-3.5 h-3.5 text-primary" />
                ) : (
                  <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                )}
                <span className={`font-mono ${f.type === "folder" ? "text-primary font-medium" : "text-foreground"}`}>
                  {f.name}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-foreground mb-2">skill.md 预览</p>
          <pre className="rounded-lg border border-border bg-background p-3 text-xs font-mono text-foreground overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[300px] overflow-y-auto">
            {mockContent}
          </pre>
        </div>
      </div>
    </div>
  );
}
