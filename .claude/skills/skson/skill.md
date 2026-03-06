---
name: skson
description: 激活整组 skill（创建 symlink），用法：/skson <组名>
---

从用户输入中提取组名，执行并输出结果：

```bash
python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/skson/on.py" "<GROUP>"
```
