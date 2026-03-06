---
name: sksoff
description: 关闭整组 skill（移除 symlink），用法：/sksoff <组名>
---

从用户输入中提取组名，执行并输出结果：

```bash
python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/sksoff/off.py" "<GROUP>"
```
