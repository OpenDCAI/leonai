---
name: sksrm
description: 删除单个 skill，用法：/sksrm <组名/skill名>
---

从用户输入中提取 <组名/skill名>，执行并输出结果：

```bash
python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/sksrm/rm.py" "<GROUP/SKILL>"
```
