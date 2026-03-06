---
name: sksgnew
description: 创建新的 skill 分组，用法：/sksgnew <组名>
---

从用户输入中提取组名，执行并输出结果：

```bash
python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/sksgnew/gnew.py" "<GROUP>"
```
