---
name: sksls
description: 列出 .claude/skill-groups/ 下所有组和 skill，显示每个 skill 的激活状态
---

执行并输出结果：

```bash
python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/sksls/ls.py"
```
